#!/usr/bin/env python
import sys
import traceback as tb
import logging
import json
import os
from functools import wraps
import time
from datetime import datetime

import MySQLdb
from flask import Flask, Response, url_for, redirect, render_template, request, session, flash, jsonify
from werkzeug import secure_filename
import flask
import requests

import aqxdb
import csvimport
from aqx_api import aqx_api


app = Flask(__name__)
app.config.from_envvar('AQUAPONICS_SETTINGS')
app.register_blueprint(aqx_api)


######################################################################
#### General helpers
######################################################################


def dbconn():
    return MySQLdb.connect(host=app.config['HOST'], user=app.config['USER'],
                           passwd=app.config['PASS'], db=app.config['DB'])


def get_user(google_id, email):
    conn = dbconn()
    cursor = conn.cursor()
    try:
        return aqxdb.get_or_create_user(conn, cursor, google_id, email)
    finally:
        conn.close()


def requires_login(func):
    """authorization wrapper"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            flash("You are not logged in.", 'error')
            return redirect(url_for('index'))
        else:
            return func(*args, **kwargs)
    return wrapper


######################################################################
#### Template filters
######################################################################

@app.template_filter()
def format_mgl(d):
    return '-' if d is None else '%.02f mg/l' % d

@app.template_filter()
def format_nounit(d):
    return '-' if d is None else '%.02f' % d

@app.template_filter()
def format_degc(d):
    return '-' if d is None else '%.02f &deg;C' % d


def swatch_class(d, green_ranges, yellow_ranges):
    def d_in_ranges(ranges):
        for r in ranges:
            if d >= r[0] and d <= r[1]:
                return True
        return False

    if d is None:
        return 'swatch-bad'
    elif d_in_ranges(green_ranges):
        return 'swatch-ok'
    elif d_in_ranges(yellow_ranges):
        return 'swatch-meh'
    else:
        return 'swatch-bad'

"""
In principle our swatch class filters are dependent on what is configured for
the aquaponics system, for now, we go with the global configuration
"""

@app.template_filter()
def swatch_temp_class(d, system_uid):
    return swatch_class(d, app.config['TEMP_GREEN_RANGES'], app.config['TEMP_YELLOW_RANGES'])


@app.template_filter()
def swatch_ph_class(d, system_uid):
    return swatch_class(d, app.config['PH_GREEN_RANGES'], app.config['PH_YELLOW_RANGES'])

@app.template_filter()
def swatch_o2_class(d, system_uid):
    return swatch_class(d, app.config['O2_GREEN_RANGES'], app.config['O2_YELLOW_RANGES'])

@app.template_filter()
def swatch_ammonium_class(d, system_uid):
    return swatch_class(d, app.config['AMMONIUM_GREEN_RANGES'],
                        app.config['AMMONIUM_YELLOW_RANGES'])

@app.template_filter()
def swatch_nitrate_class(d, system_uid):
    return swatch_class(d, app.config['NITRATE_GREEN_RANGES'], app.config['NITRATE_YELLOW_RANGES'])

@app.template_filter()
def make_marker_obj(location):
    app.logger.debug("location: '%s'", str(location))
    obj = {'title': '# systems: %d' % len(location['systems']),
           'icon': '/static/images/leaf24.png',
           'url': url_for("sys_details", system_uid=location['systems'][0]),
           'position': location['location']}
    return json.dumps(obj)


######################################################################
#### Available application paths
######################################################################

@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.exception(e)
    return render_template('unknown_error.html')


######################################################################
#### Browser Interface
######################################################################

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signin', methods=['POST'])
def signin():
    # validate id token
    try:
        idtoken = request.form['idtoken']
        r = requests.get('https://www.googleapis.com/oauth2/v3/tokeninfo?id_token=' + idtoken)
        context = r.json()
        email = context['email']
        #if not email.endswith('systemsbiology.org'):
        #    return Response("unauthorized user")
        app.logger.debug("signed in: %s", str(context))
        if context['aud'] != app.config['APP_ID']:
            app.logger.error('wrong app id: %s', context['aud'])
            raise Exception('wrong app id')

        # at this point, we are authenticated, now we can see whether we need to sign
        # into the system
        user_id = context['sub']
        if 'picture' in context:
            imgurl = context['picture']
        else:
            imgurl = "/static/images/default_profile.png"
        session['google_id'] = user_id
        session['email'] = email
        session['imgurl'] = imgurl
        session['logged_in'] = True
        session['user_id'] = get_user(user_id, email)
        app.logger.debug("user: %s img: %s", user_id, imgurl)
        return Response("ok", mimetype='text/plain')
    except:
        app.logger.exception("Got an exception")
        raise
        

@app.route('/signout')
def signout():
    # TODO: note that we might want to look into more sophisticated invalidation
    # in the future to prevent session replay attacks
    # see:
    # - http://stackoverflow.com/questions/13735024/invalidate-an-old-session-in-flask
    # - https://en.wikipedia.org/wiki/Replay_attack
    session.clear()
    return Response('ok', mimetype='text/plain')


@app.route('/about')
def about():
    return render_template('about.html', **locals())


@app.route('/home')
@requires_login
def dashboard():
    google_id = session['google_id']
    conn = dbconn()
    cursor = conn.cursor()
    try:
        systems = aqxdb.systems_and_latest_measurements(cursor, google_id)
    finally:
        cursor.close()
        conn.close()
    return render_template('dashboard.html', **locals())

@app.route('/user-settings')
@requires_login
def user_settings():
    conn = dbconn()
    cursor = conn.cursor()
    try:
        site_location = aqxdb.get_default_site_location(cursor, session['user_id'])
        app.logger.debug(site_location)
    finally:
        cursor.close()
        conn.close()
    return render_template('user_settings.html', **locals())

@app.route('/update-default-site-location', methods=['POST'])
@requires_login
def update_default_site_location():
    conn = dbconn()
    cursor = conn.cursor()
    try:
        lat = float(request.form['lat'])
        lng = float(request.form['lng'])
        aqxdb.set_default_site_location(cursor, session['user_id'], lat, lng)
        conn.commit()
        return jsonify(status="Ok")
    except Exception, e:
        app.logger.exception(e)
        return jsonify(error="invalid geo coordinate format")
    finally:
        cursor.close()
        conn.close()


@app.route('/system-details/<system_uid>')
def sys_details(system_uid=None):
    user_google_id = session['google_id'] if 'google_id' in session else None
    img_url = None
    jpg_path = os.path.join(app.config['UPLOAD_FOLDER'], "%s.jpg" % system_uid)
    if os.path.exists(jpg_path):
        img_url = '/static/uploads/%s.jpg' % system_uid
    if img_url is None:
        png_path = os.path.join(app.config['UPLOAD_FOLDER'], "%s.png" % system_uid)
        if os.path.exists(png_path):
            img_url = '/static/uploads/%s.png' % system_uid

    conn = dbconn()
    cursor = conn.cursor()
    try:
        cursor.execute('select s.id,s.name,s.creation_time,google_id from systems s join users u on s.user_id=u.id where system_id=%s', [system_uid])
        system_pk, system_name, creation_time, sys_google_id = cursor.fetchone()
        
        # only owners can modify systems's data
        readonly = user_google_id != sys_google_id
        temp_rows = aqxdb.get_measurement_series(cursor, system_uid, 'temp')
        ph_rows = aqxdb.get_measurement_series(cursor, system_uid, 'ph')
        o2_rows = aqxdb.get_measurement_series(cursor, system_uid, 'o2')
        ammonium_rows = aqxdb.get_measurement_series(cursor, system_uid, 'ammonium')
        nitrate_rows = aqxdb.get_measurement_series(cursor, system_uid, 'nitrate')
    finally:
        cursor.close()
        conn.close()
    # Provide special readonly views, it's easier to keep world-viewable pages
    # secure when all you can do is read and keep the logic outside the template
    if readonly:
        return render_template('system_details_readonly.html', **locals())
    else:
        return render_template('system_details.html', **locals())


@app.route("/create-system", methods=['POST'])
@requires_login
def create_system():
    sysname = request.form['system-name']
    if sysname is None or sysname.strip() == "":
        flash("Could not create system. Please provide a name.", 'error')
    else:
        app.logger.debug('system name submitted: %s', sysname)
        conn = dbconn()
        cursor = conn.cursor()
        try:
            cursor.execute('select count(*) from systems where user_id=%s', [session['user_id']])
            if cursor.fetchone()[0] >= app.config['SYSTEMS_PER_USER']:
                flash('Maximum number of systems/user reached.','error')
            else:
                cursor.execute('select u.id, n from users u left outer join (select user_id, count(*) as n from systems where name=%s) s on u.id=s.user_id where u.google_id=%s',
                               [sysname, session['google_id']])            
                user_pk, num_sys = cursor.fetchone()
                if num_sys > 0:
                    flash("You already have a system named '%s'. Please use a different name." % sysname, 'error')
                else:
                    app.logger.debug("creating system %s for user id: %d", sysname, user_pk)
                    aqxdb.create_aquaponics_system(cursor, user_pk, sysname)
                    conn.commit()
                    flash("Created Aquaponics system '%s'." % sysname, 'info')
        except Exception, e:
            app.logger.exception(e)
            flash("System error while trying to create '%s'" % sysname, "error")
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('dashboard'))


def get_form_time(datestr, timestr):
    if timestr:
        s = "%sT%s" % (datestr, timestr)
    else:
        s = "%sT00:00:00" % datestr
    return datetime.fromtimestamp(time.mktime(time.strptime(s, '%Y-%m-%dT%H:%M:%S')))


@app.route("/add-measurement", methods=['POST'])
@requires_login
def add_measurement():
    sys_uid = request.form['system-uid']
    measure_date = request.form['measure-date']
    measure_time = request.form['measure-time']
    mtime = get_form_time(measure_date, measure_time)
    app.logger.debug("Date: %s, Time: '%s', mtime: '%s'", measure_date, measure_time, str(mtime))
    values = {}
    errors = []
    for attr in aqxdb.ATTR_NAMES:
        if attr != 'light':  # currently the form does not support light
            try:
                value = request.form['%s-value' % attr]
                if value:
                    try:
                        values[attr] = float(value)
                    except:
                        errors.append("invalid input for '%s': '%s'" % (attr, value))
            except Exception, e:
                app.logger.debug("key error: %s", attr)
                app.logger.exception(e)

    for error_msg in errors:
        flash(error_msg, "error")

    if len(values) == 0:
        flash("Please specify at least one measurement value.", "error")

    form_ok = len(values) > 0 or len(errors) == 0
    if form_ok:
        conn = dbconn()
        cursor = conn.cursor()
        try:
            if aqxdb.is_system_owner(cursor, sys_uid, user_id=session['user_id']):
                for measure_type, mvalue in values.items():
                    aqxdb.add_measurement(cursor, sys_uid, measure_type, mtime, mvalue)
                conn.commit()
                flash('Measurements added', 'info')
            else:
                flash('Error: only system owners can add measurements')
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('sys_details', system_uid=sys_uid))


@app.route("/import-csv", methods=['POST'])
@requires_login
def import_csv():
    sys_uid = request.form['system-uid']
    file = request.files['import-file']
    if file:
        filename = secure_filename(file.filename)
        target_path = os.path.join(app.config['TMP_FOLDER'], filename)
        file.save(target_path)
        app.logger.debug('import csv, system uid: %s, filename: %s', sys_uid, filename)
        
        with open(target_path) as csvfile:
            conn = dbconn()
            cursor = conn.cursor()
            try:
                if aqxdb.is_system_owner(cursor, sys_uid, user_id=session['user_id']):
                    error_messages = csvimport.import_measurement_file(app, conn, sys_uid,
                                                                       csvfile, filename)
                    if len(error_messages) > 0:
                        conn.rollback()
                        for msg in error_messages:
                            flash(msg, "error")
                    else:
                        conn.commit()
                        flash("Imported measurements file '%s'." % filename, "info")
                else:
                    flash('Error: only system owners can import measurement data')
            finally:
                cursor.close()
                conn.close()
    else:
        flash('No import file specified', 'error')

    return redirect(url_for('sys_details', system_uid=sys_uid))


@app.route("/details_image_div/<system_uid>", methods=["GET"])
def details_images_div(system_uid):
    """a simple snippet to add an image control"""
    img_url = request.args.get('img_url');
    return render_template('details_image_div.html', **locals())


@app.route("/details_image_placeholder/<system_uid>", methods=["GET"])
def details_images_placeholder(system_uid):
    """a simple snippet to add an image control"""
    return render_template('details_image_placeholder.html', **locals())
    

@app.route('/set-system-image', methods=['POST'])
@requires_login
def set_system_image():
    sys_uid = request.form['system-uid']
    conn = dbconn()
    cursor = conn.cursor()
    try:
        if aqxdb.is_system_owner(cursor, sys_uid, user_id=session['user_id']):
            file = request.files['image-file']
            if file:
                filename = secure_filename(file.filename)
                suffix = filename.split('.')[-1].lower()
                app.logger.debug('suffix: %s', suffix)
                if suffix in {'png', 'jpg'}:
                    filename = "%s.%s" % (sys_uid, suffix)
                    target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(target_path)
                    return jsonify(status="Ok", img_url="/static/uploads/%s" % filename)
                else:
                    return jsonify(error="invalid image file name")
            else:
                return jsonify(error="please specify an image file")
        else:
            return jsonify(error="unauthorized attempt to set image file")
    finally:
        cursor.close()
        conn.close()


@app.route('/clear-system-image/<system_uid>', methods=['DELETE'])
@requires_login
def clear_system_image(system_uid):
    conn = dbconn()
    cursor = conn.cursor()
    try:
        if aqxdb.is_system_owner(cursor, system_uid, user_id=session['user_id']):
            filename = "%s.jpg" % system_uid
            target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(target_path):
                os.remove(target_path)
            else:
                filename = "%s.png" % system_uid
                target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(target_path):
                    os.remove(target_path)
            return jsonify(status="ok")
        else:
            return jsonify(error="attempt to modify non-owned system")
    finally:
        cursor.close()
        conn.close()

@app.route('/aqx-map')
def aqx_map():
    conn = dbconn()
    cursor = conn.cursor()
    try:
        #cursor.execute('select distinct default_site_location from users where default_site_location is not NULL')
        cursor.execute("select default_site_location as loc, u.id as site_id, group_concat(system_id separator ',') as sys_uids from users u join systems s on s.user_id=u.id group by loc")
        locations = []
        for loc, site_id, sys_uids in cursor.fetchall():
            try:
                lat, lng = map(float, loc.split(':'))
                locations.append({'location': {'lat': lat, 'lng': lng}, 'systems': sys_uids.split(',')})
            except:  # don't add invalid locations
                pass
    finally:
        cursor.close()
        conn.close()
    return render_template('aqx_map.html', **locals())


if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    app.debug = True
    app.secret_key = 'supercalifragilistic'
    app.logger.addHandler(handler)
    app.run(host='0.0.0.0', debug=True)
