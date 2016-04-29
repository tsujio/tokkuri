#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Sample cgi program using Bottle web framework (http://bottlepy.org)"""

import bottle    # Locate bottle.py in search path in advance
from tokkuri import SessionMiddleware


session_config = {
    'env_key': 'session',
    'session.config': {
        'store.type': 'sqlite',
        'store.config': {
            'path': './sessions.sqlite'
        },
        'cookie.config': {
            'path': '/'
        }
    }
}
app = SessionMiddleware(bottle.app(), session_config)


@bottle.get('/')
def index():
    return bottle.template("""
      <form action='{{url}}' method='POST'>
        Your name: <input type='text' name='name' /><br />
        <input type='submit' value='Login' />
      </form>
    """, url=bottle.url('/login'))


@bottle.post('/login')
def login():
    s = bottle.request.environ['session']
    s.clear()
    s['name'] = bottle.request.forms['name']
    s.save()
    bottle.redirect(bottle.url('/hello'))


@bottle.get('/hello')
def hello():
    s = bottle.request.environ['session']
    if 'name' not in s:
        bottle.redirect(bottle.url('/'))
    name = s['name']
    return bottle.template("<p>Hello {{name}}!</p>", name=name)


bottle.run(app=app, server='cgi')
