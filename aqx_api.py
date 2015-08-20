"""
Aquaponics REST API Blueprint
"""
from flask import Blueprint, request, url_for, jsonify, current_app
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
    return resp.json()


def authorize(func):
    """authorization wrapper"""
    @wraps(func)
    def wrapper(*args, **kwargs):
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


API_TIME_FORMAT = '%m/%d/%Y %H:%M:%S'

"""
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer ya29.1QFng_HOUxcDoYncPlVamEsaQOrLGOSTgfE4sweBiYHK_fvKxa5g8qbYpluqowddEaVsWA" -d '[{"time": "08/19/2015 08:15:30", "o2": 10.2}]' http://localhost:5000/api/v1/add-measurements/7921a6763e0011e5beb064273763ec8b

"""
@aqx_api.route('/api/v1/add-measurements/<system_id>', methods=['POST'])
@authorize
def api_add_measurements(system_id, *args, **kwargs):
    conn = dbconn()
    cursor = conn.cursor()
    try:
        if aqxdb.is_system_owner(cursor, system_id, google_id=kwargs['google_id']):
            current_app.logger.debug('adding measurements for system id: %s and google id: %s',
                                     system_id, kwargs['google_id']) 
            measurements = json.loads(request.data)
            current_app.logger.debug(measurements)
            try:
                warned = False
                for measurement in measurements:
                    if not 'time' in measurement:
                        return jsonify(error="no time provided")
                    timestamp = datetime.fromtimestamp(time.mktime(time.strptime(measurement['time'],
                                                                                 API_TIME_FORMAT)))
                    for attr in aqxdb.ATTR_NAMES:
                        if attr in measurement:
                            try:
                                aqxdb.add_measurement(cursor, system_id, attr, timestamp, measurement[attr])
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
    finally:
        cursor.close()
        conn.close()


# This is an example for an API call that is authenticated with Google OAuth2
# The call expects an authorization header with a Bearer token received
# from Google OAuth2.
"""
curl -X POST -H "Authorization: Bearer ya29.1QFng_HOUxcDoYncPlVamEsaQOrLGOSTgfE4sweBiYHK_fvKxa5g8qbYpluqowddEaVsWA" http://localhost:5000/api/v1/api-test
"""
@aqx_api.route('/api/v1/api-test', methods=['POST', 'GET'])
@authorize
def api_test(*args, **kwargs):
    current_app.logger.debug('api_test(), user_id: %s', kwargs['google_id'])

    # this is the authorization code
    return jsonify(message='Greetings from Project Feed 1010 !')
