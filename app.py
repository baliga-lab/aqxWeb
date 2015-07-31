#!/usr/bin/env python
from flask import Flask, Response, url_for, redirect, render_template, request, session
import flask
import requests
import logging

"""This is the prototype web application for our Aquaponics site.
We might consider later splitting stuff up into Flask Blueprints
"""
APP_ID = '75692667349-39hlipha81a3v40du06184k75ajl8u4u.apps.googleusercontent.com'


app = Flask(__name__)


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
        if context['aud'] != APP_ID:
            app.logger.error('wrong app id: %s', context['aud'])
            raise Exception('wrong app id')

        # at this point, we are authenticated, now we can see whether we need to sign
        # into the system
        user = context['email']
        imgurl = context['picture']
        session['user'] = user
        session['imgurl'] = imgurl
        session['logged_in'] = True
        app.logger.debug("user: %s img: %s", user, imgurl)
        return Response("ok", mimetype='text/plain')
    except:
        return Response("error", mimetype='text/plain')
        
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
    if 'logged_in' not in session or  not session['logged_in']:
        return redirect(url_for('.index'))
    else:
        user = session['user']
        app.logger.debug("logged in: %s", session['logged_in'])
        app.logger.debug("we are currently logged in as: %s", user)
        return render_template('dashboard.html')

if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    app.debug = True
    app.secret_key = 'supercalifragilistic'
    app.logger.addHandler(handler)
    app.run(host='0.0.0.0')
