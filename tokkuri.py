# -*- coding: utf-8 -*-

"""
Tokkuri is a micro session management library for a small web application with
Python. It requires only the python standard libraries and all components are
in a single file.

https://github.com/tsujio/tokkuri

Copyright (c) 2016, Naoki Tsujio.
License: MIT (see LICENSE for details)
"""

# Should import standard libraries only
import uuid
import re
import json
from time import time
from datetime import datetime, timedelta
from random import random
import sqlite3
from Cookie import SimpleCookie


###############################################################################
# Session #####################################################################
###############################################################################


class Session(object):
    """Session object"""

    # Session id pattern
    _ID_PATTERN = re.compile('\A[0-9a-f]{32}\Z')

    def __init__(self, cookie_header='', config=None):
        # Merge config to default config
        self._config = config = _update_deeply({
            'timeout': 24 * 60 * 60,
            'store.type': 'sqlite',
        }, config or {})

        self._is_new = True  # This session is new one or not
        self._vars = {}  # Session vars
        self._cookie_to_send = ''  # Cookie string to send

        # Setup session storage
        store = STORES.get(config['store.type'].lower())
        if store is None:
            raise ValueError("Unknown store type: %s" % config['store.type'])
        self._store = store(timeout=config['timeout'],
                            config=config.get('store.config'))

        # Decode cookie header
        self._cookie = SessionCookie(cookie_header,
                                     config.get('cookie.config'))

        # Start new session if not received session id
        if not self.cookie.value:
            self._renew()
            return

        # Validate given id (if invalid id, clear session)
        try:
            Session.validate_id(self.id)
        except ValueError:
            self.clear()
            return

        # Load session from storage if received session id from client
        self._is_new = False
        try:
            self._vars = self._store.load(self.id)
        except TimedOutException:
            # The session has timed out and start new session
            self.clear()

    @property
    def id(self):
        return self.cookie.value

    @property
    def cookie(self):
        return self._cookie

    @classmethod
    def genid(cls):
        """Generate random session id"""
        return uuid.uuid4().hex.lower()

    @classmethod
    def validate_id(cls, id):
        if not isinstance(id, str):
            raise TypeError("Invalid type for id: %s" % type(id))
        if not Session._ID_PATTERN.match(id):
            raise ValueError("Invalid format for id: %s" % id)

    def _renew(self):
        """Initialize as new session"""
        self._is_new = True
        self._vars = {}
        self._cookie = SessionCookie('', self._config.get('cookie.config'))
        self.cookie.value = Session.genid()

    def save(self):
        """Save session to storage"""
        if self._is_new or self.cookie.attr_changed:
            self._update_cookie_to_send()
        self._store.save(self.id, self._vars)

    def clear(self):
        """Clear all session vars and generate new session id"""
        self.cookie.expires = datetime.utcnow() - timedelta(365)
        self._vars = {}
        self.save()
        self._renew()

    def _update_cookie_to_send(self):
        self._cookie_to_send = str(self.cookie)

    def get_cookie_to_send(self):
        """Return cookie only when any of the following cases occurred
        1. a new session starts and is saved
        2. any attribute of a cookie changes and the session is saved
        3. The session has timed out
        4. The session is cleared
        """
        return self._cookie_to_send or None

    def __len__(self):
        return len(self._vars)

    def __getitem__(self, key):
        return self._vars[key]

    def __setitem__(self, key, value):
        self._vars[key] = value

    def __delitem__(self, key):
        del self._vars[key]

    def __iter__(self):
        return iter(self._vars)

    def __contains__(self, key):
        return key in self._vars

    def __repr__(self):
        return ("Session(cookie_header=%s, config=%s)" %
                (self.cookie, self._config))


class SessionInterface(object):
    """Defer creating session instance until accessed"""

    def __init__(self, *args, **kwargs):
        self.__dict__['_args'] = args
        self.__dict__['_kwargs'] = kwargs
        self.__dict__['_session'] = None

    def session(self):
        if self.__dict__['_session'] is None:
            self.__dict__['_session'] = Session(
                *self.__dict__['_args'], **self.__dict__['_kwargs']
            )
        return self.__dict__['_session']

    def accessed(self):
        return self.__dict__['_session'] is not None

    def __getattr__(self, name):
        return getattr(self.session(), name)

    def __setattr__(self, name, value):
        setattr(self.session(), name, value)

    def __delattr__(self, name):
        delattr(self.session(), name)

    def __len__(self):
        return len(self.session())

    def __getitem__(self, key):
        return self.session()[key]

    def __setitem__(self, key, value):
        self.session()[key] = value

    def __delitem__(self, key):
        del self.session()[key]

    def __repr__(self):
        return repr(self.session())

    def __iter__(self):
        return iter(self.session())

    def __contains__(self, key):
        return key in self.session()


###############################################################################
# Cookies #####################################################################
###############################################################################


class SessionCookie(object):
    """Cookie for sharing session id with a client"""

    def __init__(self, cookie_header='', config=None):
        self._config = config = _update_deeply({
            'key': 'tokkuri.session.id',
            'domain': None,
            'path': None,
            'secure': None,
            'httponly': None,
            'expires': None,
        }, config or {})
        self._cookie = SimpleCookie(input=cookie_header)
        self._attr_changed = False

    @property
    def attr_changed(self):
        return self._attr_changed

    @property
    def key(self):
        return self._config['key']

    # Prpoerty: value
    def _get_value(self):
        if self.key not in self._cookie:
            return None
        return self._cookie[self.key].value

    def _set_value(self, value):
        self._cookie[self.key] = value

        # Set default cookie attrs
        if self._config['domain'] is not None:
            self.domain = self._config['domain']
        if self._config['path'] is not None:
            self.path = self._config['path']
        if self._config['secure'] is not None:
            self.secure = self._config['secure']
        if self._config['httponly'] is not None:
            self.httponly = self._config['httponly']
        if self._config['expires'] is not None:
            self.expires = self._config['expires']
        self._attr_changed = False

    value = property(_get_value, _set_value)

    # Property: domain
    def _get_domain(self):
        if self.key not in self._cookie:
            return ''
        return str(self._cookie[self.key]['domain'])

    def _set_domain(self, domain):
        self._attr_changed = True
        self._cookie[self.key]['domain'] = str(domain)

    domain = property(_get_domain, _set_domain)

    # Property: path
    def _get_path(self):
        if self.key not in self._cookie:
            return ''
        return str(self._cookie[self.key]['path'])

    def _set_path(self, path):
        self._attr_changed = True
        self._cookie[self.key]['path'] = str(path)

    path = property(_get_path, _set_path)

    # Property: secure
    def _get_secure(self):
        if self.key not in self._cookie:
            return False
        return bool(self._cookie[self.key]['secure'])

    def _set_secure(self, secure):
        self._attr_changed = True
        self._cookie[self.key]['secure'] = bool(secure)

    secure = property(_get_secure, _set_secure)

    # Property: httponly
    def _get_httponly(self):
        if self.key not in self._cookie:
            return False
        return bool(self._cookie[self.key]['httponly'])

    def _set_httponly(self, httponly):
        self._attr_changed = True
        self._cookie[self.key]['httponly'] = bool(httponly)

    httponly = property(_get_httponly, _set_httponly)

    # Property: expires
    def _get_expires(self):
        if self.key not in self._cookie:
            return ''
        try:
            return datetime.strptime(
                self._cookie[self.key]['expires'],
                "%a, %d-%b-%Y %H:%M:%S GMT"
            )
        except ValueError:
            return ''

    def _set_expires(self, expires):
        self._attr_changed = True
        if not expires:
            expires = datetime.fromtimestamp(0x7FFFFFFF)
        elif isinstance(expires, timedelta):
            expires = datetime.utcnow() + expires
        elif isinstance(expires, datetime):
            pass
        else:
            raise TypeError("Invalid type for cookie expires: %s" % expires)
        self._cookie[self.key]['expires'] = \
            expires.strftime("%a, %d-%b-%Y %H:%M:%S GMT")

    expires = property(_get_expires, _set_expires)

    def __str__(self):
        return self._cookie[self.key].output(header='')


###############################################################################
# Exceptions ##################################################################
###############################################################################


class SessionException(Exception):
    pass


class TimedOutException(SessionException):
    pass


###############################################################################
# Stores ######################################################################
###############################################################################


class SQLiteStore(object):
    """Session store with SQLite backend"""

    def __init__(self, timeout, config=None):
        self._config = config = _update_deeply({
            'path': './sessions.sqlite',
            'gc.auto': True,
            'gc.auto.prob': 0.001,
        }, config or {})

        self.timeout = timeout

        # Setup connection
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row  # Access column by name

        # Create db unless exists
        self.create_db_unless_exists()

        # Sweep expired sessions
        if config['gc.auto'] and config['gc.auto.prob'] > random():
            self.gc()

    @property
    def path(self):
        return self._config['path']

    def create_db_unless_exists(self):
        """Create db and tables unless exist"""
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "  id TEXT PRIMARY KEY,"  # Session id
            "  ctime INTEGER NOT NULL,"  # Created time
            "  atime INTEGER NOT NULL,"  # Accessed time
            "  vars TEXT NOT NULL"  # Session variables (json format)
            ")"
        )

    def gc(self):
        """Delete all timed out sessions"""
        with self._conn:
            self._conn.execute(
                "DELETE FROM sessions WHERE atime < ?",
                (int(time()) - self.timeout,)
            )

    def save(self, id, vars):
        """Save session to db"""
        now = int(time())
        with self._conn:
            # Delete session and return if no vars to be saved
            if not vars:
                self._conn.execute(
                    "DELETE FROM sessions WHERE id = ?", (id,)
                )
                return

            # Create session if not exist (vars are saved later)
            self._conn.execute(
                ("INSERT OR IGNORE INTO sessions(id, ctime, atime, vars) "
                 "VALUES (?, ?, ?, ?)"),
                (id, now, now, '')
            )

            # Update atime (for existing session) and save session vars
            self._conn.execute(
                "UPDATE sessions SET atime = ?, vars = ? WHERE id = ?",
                (now, json.dumps(vars), id)
            )

    def load(self, id):
        """Load session from db"""
        row = self._conn.execute(
            ("SELECT vars FROM sessions WHERE id = ? AND atime > ?"),
            (id, int(time()) - self.timeout)
        ).fetchone()

        if row is None:
            raise TimedOutException("Session (%s) has timed out." % id)
        return json.loads(row['vars'])


# Available session stores
STORES = {
    'sqlite': SQLiteStore,
}


###############################################################################
# SessionMiddleware ###########################################################
###############################################################################


class SessionMiddleware(object):
    """WSGI middleware for session management"""

    def __init__(self, app, config=None):
        self._app = app
        self._config = _update_deeply({
            'env_key': 'tokkuri.session'
        }, config or {})

    def __call__(self, environ, start_response):
        # Load stored session or create new session
        session = SessionInterface(cookie_header=environ.get('HTTP_COOKIE', ''),
                                   config=self._config.get('session.config'))

        # Set session object to environ
        environ[self._config['env_key']] = session

        def _start_response(status, headers, exec_info=None):
            """Called after app's process"""
            if session.accessed():
                # Set cookie to response header if necessary
                cookie = session.get_cookie_to_send()
                if cookie:
                    headers.append(('Set-cookie', cookie))

            return start_response(status, headers, exec_info)

        return self._app(environ, _start_response)


###############################################################################
# Utils #######################################################################
###############################################################################


def _update_deeply(dest, src):
    """Update dict deeply

    http://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    """
    for k, v in src.iteritems():
        if isinstance(v, dict):
            dest[k] = _update_deeply(dest.get(k, {}), v)
        else:
            dest[k] = src[k]
    return dest
