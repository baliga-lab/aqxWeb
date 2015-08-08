#!/usr/bin/env python
import sys
import traceback as tb
import logging
import uuid
from functools import wraps

import MySQLdb
from flask import Flask, Response, url_for, redirect, render_template, request, session, flash
import flask
import requests

"""This is the prototype web application for our Aquaponics site.
We might consider later splitting stuff up into Flask Blueprints
"""

app = Flask(__name__)
app.config.from_envvar('AQUAPONICS_SETTINGS')


def dbconn():
    return MySQLdb.connect(host=app.config['HOST'], user=app.config['USER'],
                           passwd=app.config['PASS'], db=app.config['DB'])


def new_system_id():
    """Generates a new system id"""
    return uuid.uuid1().hex

    
def google_user_info(bearer_token):
    resp = requests.get(app.config['USERINFO_URL'], headers={'Authorization': 'Bearer %s' % bearer_token})
    return resp.json()


def get_user(user_id, email):
    conn = dbconn()
    cursor = conn.cursor()
    try:
        cursor.execute('select id from users where google_id=%s', [user_id])
        row = cursor.fetchone()
        if row is None:
            # create user
            cursor.execute('insert into users (google_id, email) values (%s,%s)', [user_id, email])
            result = cursor.lastrowid
            conn.commit()
        else:
            result = row[0]
        return result
    finally:
        conn.close()


def authorize(func):
    """authorization wrapper"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if auth is not None:
            auth = auth.split()
            app.logger.debug("@authorize auth: %s", str(auth))
            if auth[0] == 'Bearer':
                user_info = google_user_info(auth[1])            
                app.logger.debug(user_info)
                if 'error' in user_info:
                    app.logger.error('error in authorization: %s', user_info['error']['message'])
                else:
                    kwargs['user_id'] = user_info['id']
                    app.logger.debug('@authorize(), user_id: %s', kwargs['user_id'])
            else:
                # error wrong authentification
                app.logger.error('@authorize(), not a Bearer token')
                raise Exception('authentication error')

        return func(*args, **kwargs)
    return wrapper


def check_logged_in(func):
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
        app.logger.debug("signed in: %s", str(context))
        if context['aud'] != app.config['APP_ID']:
            app.logger.error('wrong app id: %s', context['aud'])
            raise Exception('wrong app id')

        # at this point, we are authenticated, now we can see whether we need to sign
        # into the system
        user_id = context['sub']
        email = context['email']
        imgurl = context['picture']
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


@app.route('/home')
@check_logged_in
def dashboard():
    user_id = session['google_id']
    conn = dbconn()
    cursor = conn.cursor()
    try:
        cursor.execute('select s.id,s.name,system_id from systems s join users u on s.user_id=u.id where google_id=%s',
                       [user_id])
        system_pk, system_name, system_id = cursor.fetchone()
        cursor.execute("select time,temperature,ph,ammonium,nitrate,oxygen from measurements where system_id=%s order by time desc limit 1",
                       [system_pk])
        row = cursor.fetchone()
        if row is not None:
            time, temperature, ph, ammonium, nitrate, oxygen = row
            if oxygen is None:
                oxygen = 0.0
            logging.debug("temperature: %s", str(temperature))
        else:
            logging.error('query failed')
    finally:
        cursor.close()
        conn.close()

    app.logger.debug("we are currently logged in as: %s", user_id)
    # TODO: get all available system ids
    return render_template('dashboard.html', **locals())


@app.route('/system-details/<system_id>')
@check_logged_in
def sys_details(system_id=None):
    user_id = session['google_id']
    conn = dbconn()
    cursor = conn.cursor()
    try:
        cursor.execute('select s.id,s.name,creation_time from systems s where system_id=%s', [system_id])
        system_pk, system_name, creation_time = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    return render_template('system_details.html', **locals())


######################################################################
#### REST API
######################################################################

@app.route('/api/v1/upload_run', methods=['POST'])
def upload_run():
    conn = dbconn()
    cursor = conn.cursor()
    try:
        xmlimport.process_doc(cursor, request.data)
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return Response("hello world", mimetype='text/plain')

# This is an example for an API call that is authenticated with Google OAuth2
# The call expects an authorization header with a Bearer token received
# from Google OAuth2.
@app.route('/api/v1/api_test', methods=['POST', 'GET'])
@authorize
def api_test(*args, **kwargs):
    app.logger.debug('api_test(), user_id: %s', kwargs['user_id'])

    # this is the authorization code
    return Response('{"hallo": "spencer"}', mimetype='application/json')
    

if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    app.debug = True
    app.secret_key = 'supercalifragilistic'
    app.logger.addHandler(handler)
    app.run(host='0.0.0.0', debug=True)
