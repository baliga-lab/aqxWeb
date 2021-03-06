"""
Aquaponics REST API Blueprint
"""
import os
from flask import Blueprint, request, url_for, jsonify, current_app, Response
from functools import wraps
import requests
import MySQLdb
import json
import time
from datetime import datetime

import aqxdb

aqx_api = Blueprint('aqx_api', __name__)


def dbconn():
    return MySQLdb.connect(host=current_app.config['HOST'], user=current_app.config['USER'],
                           passwd=current_app.config['PASS'], db=current_app.config['DB'])


def google_user_info(bearer_token):
    resp = requests.get(current_app.config['USERINFO_URL'],
                        headers={'Authorization': 'Bearer %s' % bearer_token})
    try:
        return resp.json()
    except:
        # fallback to older requests module
        return resp.json


def authorize(func):
    """authorization wrapper"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # If testing is set to true, google id will be taken from the GOOGLE_ID
        # request header
        if current_app.config['TESTING']:
            kwargs['google_id'] = request.headers.get('GOOGLE_ID')
            return func(*args, **kwargs)

        auth = request.headers.get('Authorization')
        if auth is not None:
            auth = auth.split()
            current_app.logger.debug("@authorize auth: %s", str(auth))
            if auth[0] == 'Bearer':
                user_info = google_user_info(auth[1])
                current_app.logger.debug(user_info)
                if 'error' in user_info:
                    current_app.logger.error('error in authorization: %s',
                                             user_info['error']['message'])
                    return jsonify(error='authorization error')
                else:
                    kwargs['google_id'] = user_info['id']
                    current_app.logger.debug('@authorize(), google_id: %s', kwargs['google_id'])
            else:
                # error wrong authentification
                current_app.logger.error('@authorize(), not a Bearer token')
                return jsonify(error="authorization error")
        else:
            current_app.logger.debug("no authorization headers: %s", str(request.headers))
            return jsonify(error="authorization error")
        return func(*args, **kwargs)
    return wrapper


API_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
API_TIME_FORMAT_OBSOLETE = '%Y/%m/%d %H:%M:%S'
API_DATE_FORMAT = '%Y-%m-%d'


def parse_timestamp(s):
    try:
        return datetime.fromtimestamp(time.mktime(time.strptime(s, API_TIME_FORMAT)))
    except:
        current_app.logger.debug("problem using API default format, trying obsolete format")
        # support this until new version of Android client is rolled out
        try:
            return datetime.fromtimestamp(time.mktime(time.strptime(s, API_TIME_FORMAT_OBSOLETE)))
        except:
            return None


def format_timestamp(timestamp):
    return datetime.strftime(timestamp, API_TIME_FORMAT) if timestamp is not None else ''

"""
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer ya29.1QFng_HOUxcDoYncPlVamEsaQOrLGOSTgfE4sweBiYHK_fvKxa5g8qbYpluqowddEaVsWA" -d '[{"time": "08/19/2015 08:15:30", "o2": 10.2}]' http://localhost:5000/api/v1.0/add-measurements/7921a6763e0011e5beb064273763ec8b

"""
@aqx_api.route('/api/v1.0/measurements/<system_uid>', methods=['POST'])
@authorize
def api_add_measurements(system_uid, *args, **kwargs):
    """
    {'measurements': [{'time': '2015/10/11 10:30:50', 'o2': 12.0}, ...]}
    """
    conn = dbconn()
    cursor = conn.cursor()
    try:
        if aqxdb.is_system_owner(cursor, system_uid, google_id=kwargs['google_id']):
            current_app.logger.debug('adding measurements for system id: %s and google id: %s',
                                     system_uid, kwargs['google_id'])
            measurements = json.loads(request.data)['measurements']
            current_app.logger.debug(measurements)
            try:
                warned = False
                for measurement in measurements:
                    if not 'time' in measurement:
                        return jsonify(error="no time provided")
                    timestamp = parse_timestamp(measurement['time'])
                    for attr in aqxdb.ATTR_NAMES:
                        if attr in measurement:
                            try:
                                aqxdb.add_measurement(cursor, system_uid, attr, timestamp, measurement[attr])
                            except:
                                # only warn once per submission
                                if not warned:
                                    current_app.logger.warn('attempted to add data for existing time')
                                    warned = True
                conn.commit()
                return jsonify(status="Ok")
            except Exception, e:
                current_app.logger.exception(e)
                return jsonify(error="error in input document")
        else:
            return jsonify(error="attempt to access non-existing (or non-owned) system")
    except Exception, e:
        print "REQUEST DATA: '%s'" % request.data
        current_app.logger.exception(e)
        return jsonify(error="error in input document")
    finally:
        cursor.close()
        conn.close()

"""
http://localhost:5000/api/v1.0/measurements/312319313/2015-12-12T00:00:00Z/2015-12-14T00:00:00Z
"""
@aqx_api.route('/api/v1.0/measurements/<system_uid>', methods=['GET'])
@aqx_api.route('/api/v1.0/measurements/<system_uid>/<from_time>', methods=['GET'])
@aqx_api.route('/api/v1.0/measurements/<system_uid>/<from_time>/<to_time>', methods=['GET'])
def api_get_measurements(system_uid, from_time=None, to_time=None):
    """Retrieve a system's measurements in the specified date/time range"""
    start = parse_timestamp(from_time)
    end = parse_timestamp(to_time)
    conn = dbconn()
    cursor = conn.cursor()
    result = {}
    for attr in aqxdb.ATTR_NAMES:
        values =  aqxdb.get_measurement_series_range(cursor, system_uid, attr, start, end)
        out_values = [ {"time": format_timestamp(time), "value": value} for time, value in values ]
        result[attr] = out_values

    return jsonify(result)

"""
GET: Retrieve systems
POST: Create new system
Example:
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer ya29.SwKh2KrxuyGw67_RIPA__Y8VxGhcWsyHdAGOrDWkYJElflp4_fkfqer67dfkaIB0aRpOWpA" -d '{"name": "Another system"}' http://localhost:5000/api/v1.0/systems
"""
@aqx_api.route('/api/v1.0/systems', methods=['GET', 'POST'])
@authorize
def api_user_systems(*args, **kwargs):
    """Returns all systems available to the user."""
    conn = dbconn()
    cursor = conn.cursor()
    try:
        if request.method == 'GET':
            systems = aqxdb.user_systems(cursor, google_id=kwargs['google_id'])
            for system in systems:
                sys_uid = system['uid']
                png_path = os.path.join(current_app.config['UPLOAD_FOLDER'], '%s_thumb.png' % sys_uid)
                jpg_path = os.path.join(current_app.config['UPLOAD_FOLDER'], '%s_thumb.jpg' % sys_uid)
                if os.path.exists(png_path):
                    system['thumb_url'] = "/static/uploads/%s_thumb.png" % sys_uid
                elif os.path.exists(jpg_path):
                    system['thumb_url'] = "/static/uploads/%s_thumb.jpg" % sys_uid
                else:
                    system['thumb_url'] = '/static/images/leaf_icon_100.png'
            return jsonify(systems=systems)
        elif request.method == 'POST':
            update_data = json.loads(request.data)
            current_app.logger.debug("Creating app with name '%s'", update_data['name'])
            user_pk = aqxdb.user_pk_for_google_id(cursor, kwargs['google_id'])
            aqxdb.create_aquaponics_system(cursor, user_pk, update_data['name'])
            conn.commit()
            return jsonify(status="Ok", message="System created")
    finally:
        cursor.close()
        conn.close()

def thumb_url(system_uid):
    png_path = os.path.join(current_app.config['UPLOAD_FOLDER'], '%s_thumb.png' % system_uid)
    jpg_path = os.path.join(current_app.config['UPLOAD_FOLDER'], '%s_thumb.jpg' % system_uid)
    if os.path.exists(png_path):
        mtime = os.path.getmtime(png_path)
        return "/static/uploads/%s_thumb.png?%s" % (system_uid, mtime)
    elif os.path.exists(jpg_path):
        mtime = os.path.getmtime(jpg_path)
        return "/static/uploads/%s_thumb.jpg?%s" % (system_uid, mtime)
    else:
        return '/static/images/leaf_icon_100.png'


def image_url(system_uid):
    img_url = None
    mtime = None
    jpg_path = os.path.join(current_app.config['UPLOAD_FOLDER'], "%s.jpg" % system_uid)
    if os.path.exists(jpg_path):
        mtime = os.path.getmtime(jpg_path)
        img_url = '/static/uploads/%s.jpg?%s' % (system_uid, str(mtime))
    if img_url is None:
        png_path = os.path.join(current_app.config['UPLOAD_FOLDER'], "%s.png" % system_uid)
        if os.path.exists(png_path):
            mtime = os.path.getmtime(png_path)
            img_url = '/static/uploads/%s.png?%s' % (system_uid, str(mtime))
    return img_url

"""
GET: Detail information for system
POST: Update detail information for system
DELETE: Delete a system
"""
@aqx_api.route('/api/v1.0/system/<system_uid>', methods=['GET'])
@authorize
def api_system_details(system_uid, *args, **kwargs):
    """Returns the specified system's details"""
    conn = dbconn()
    cursor = conn.cursor()
    try:
        cursor.execute('select s.id,s.name,s.creation_time,start_date,t.name from systems s left outer join aqx_techniques t on s.aqx_technique_id=t.id where system_uid=%s',
                       [system_uid])
        row = cursor.fetchone()
        system_pk, system_name, creation_time, start_date, technique = row
        img_url = None  # TODO
        details = {'name': system_name,
                   'creation_time': format_timestamp(creation_time),
                   'start_date': format_timestamp(start_date),
                   'aqx_technique': technique if technique is not None else '',
                   'image_url': img_url if img_url is not None else ''
                   }
        cursor.execute('select ao.name,sao.num from system_aquatic_organisms sao join aquatic_organisms ao on sao.organism_id=ao.id where system_id=%s', [system_pk])
        organisms = [{name: num} for name, num in cursor.fetchall()]
        details['aquatic_organisms'] = organisms

        cursor.execute('select c.name,sc.num from system_crops sc join crops c on sc.crop_id=c.id where system_id=%s', [system_pk])
        crops = [{name: num} for name, num in cursor.fetchall()]
        details['crops'] = crops
        return jsonify(system_details=details)
    finally:
        cursor.close()
        conn.close()


@aqx_api.route('/api/v1.0/aquatic_crops', methods=['GET'])
def api_aquatic_crops():
    """Returns a list of all aquatic crops in the system"""
    conn = dbconn()
    cursor = conn.cursor()
    try:
        result = [{"id": pk, "name": name} for pk, name in
                  aqxdb.all_catalog_values(cursor, "aquatic_organisms")]
        return Response(json.dumps(result), mimetype='application/json')
    finally:
        cursor.close()
        conn.close()


@aqx_api.route('/api/v1.0/botanic_crops', methods=['GET'])
def api_botanic_crops():
    """Returns a list of all plant crops in the system"""
    conn = dbconn()
    cursor = conn.cursor()
    try:
        result = [{"id": pk, "name": name} for pk, name in
                  aqxdb.all_catalog_values(cursor, "crops")]
        return Response(json.dumps(result), mimetype='application/json')
    finally:
        cursor.close()
        conn.close()


@aqx_api.route('/api/v1.0/techniques', methods=['GET'])
def api_techniques():
    """Returns a list of all aquaponics techniques in the system"""
    conn = dbconn()
    cursor = conn.cursor()
    try:
        result = [{"id": pk, "name": name} for pk, name in
                  aqxdb.all_catalog_values(cursor, "aqx_techniques")]
        return Response(json.dumps(result), mimetype='application/json')
    finally:
        cursor.close()
        conn.close()


# This is an example for an API call that is authenticated with Google OAuth2
# The call expects an authorization header with a Bearer token received
# from Google OAuth2.
"""
curl -X POST -H "Authorization: Bearer ya29.1QFng_HOUxcDoYncPlVamEsaQOrLGOSTgfE4sweBiYHK_fvKxa5g8qbYpluqowddEaVsWA" http://localhost:5000/api/v1.0/api-test
"""
@aqx_api.route('/api/v1.0/api-test', methods=['POST', 'GET'])
@authorize
def api_test(*args, **kwargs):
    current_app.logger.debug('api_test(), user_id: %s', kwargs['google_id'])

    # this is the authorization code
    return jsonify(message='Greetings from Project Feed 1010 !')
