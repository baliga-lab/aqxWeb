#!/usr/bin/env python
import sys
import traceback as tb
import logging

import MySQLdb
from flask import Flask, Response, url_for, redirect, render_template, request, session
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
def dashboard():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('.index'))
    else:
        user_id = session['google_id']
        conn = dbconn()
        cursor = conn.cursor()
        try:
            cursor.execute('select s.id,s.name from systems s join users u on s.user_id=u.id where google_id=%s',
                           [user_id])
            system_id, system_name = cursor.fetchone()
            cursor.execute("select time,temperature,ph,ammonium,nitrate,oxygen from measurements where system_id=%s order by time desc limit 1",
                           [system_id])
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
        # TODO: filter using the system id
        return render_template('dashboard.html', **locals())

@app.route('/upload_run', methods=['POST'])
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
@app.route('/api_test', methods=['POST', 'GET'])
def api_test():
    app.logger.debug("api_test() method: %s", request.method)
    app.logger.debug("api_test() args: %s", str(request.args))

    # this is the authorization code
    auth = request.headers.get('Authorization')
    if auth is not None:
        auth = auth.split()
        app.logger.debug("api_test() auth: %s", str(auth))
        if auth[0] == 'Bearer':
            user_info = google_user_info(auth[1])            
            app.logger.debug(user_info)
            if 'error' in user_info:
                app.logger.error('error in authorization: %s', user_info['error']['message'])
            else:
                # retrieve user information
                pass
        else:
            # error wrong authentification
            pass
    return Response('{"hallo": "spencer"}', mimetype='application/json')
    

@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.exception(e)
    return render_template('unknown_error.html')

if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    app.debug = True
    app.secret_key = 'supercalifragilistic'
    app.logger.addHandler(handler)
    app.run(host='0.0.0.0')
