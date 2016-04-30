#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import re
import os
import sys

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(TESTS_DIR))
sys.path.insert(0, TESTS_DIR)

import tokkuri
from tokkuri import Session, TimedOutException
import mockstore
from mockstore import MockStore

# Use mock store for saving sessions
tokkuri.STORES = {'mock': MockStore}


class TestSession(unittest.TestCase):
    """Test cases for Session class"""

    def setUp(self):
        # Create instance as new session
        self.ns = Session(cookie_header='', config={'store.type': 'mock'})

        # Create instance as existing session
        mockstore.LOAD = lambda id: {'key1': 'string', 'key2': 123}
        self.es = Session(
            cookie_header="tokkuri.session.id=%s;" % ('a' * 32),
            config={'store.type': 'mock'}
        )
        mockstore.LOAD = mockstore.DEFAULT_LOAD

    def tearDown(self):
        mockstore.SAVE = mockstore.DEFAULT_SAVE
        mockstore.LOAD = mockstore.DEFAULT_LOAD

    def test___init___setup_store(self):
        """It should initialize session store with given config"""
        # Should raise exception if passed unknown store type
        self.assertRaises(ValueError, Session, '', {'store.type': 'unknown'})

        # Should pass appropriate arguments to store
        Session('', {
            'timeout': 60,
            'store.type': 'mock',
            'store.config': {
                'path': 'testdb.sqlite'
            }
        })
        self.assertEqual(MockStore.initargs, (60, {'path': 'testdb.sqlite'}))

    def test___init___without_cookie(self):
        """It should start a new session if cookie not received"""
        s = Session(None, {'store.type': 'mock'})
        self.assertTrue(s._is_new)
        self.assertEqual(s._vars, {})
        self.assertIsNone(Session.validate_id(s.id))
        self.assertIsNone(s.get_cookie_to_send())

    def test___init___with_cookie(self):
        """It should initialize session by given cookie"""
        s = Session(
            "tokkuri.session.id=%s; Domain=example.com; Path=/" % ('a' * 32),
            {'store.type': 'mock'}
        )
        self.assertFalse(s._is_new)
        self.assertEqual(s._vars, mockstore.DEFAULT_LOAD('dummy'))
        self.assertEqual(s.id, 'a' * 32)
        self.assertIsNone(s.get_cookie_to_send())

    def test___init___with_invalid_cookie(self):
        """It should start a new session sening expired cookie
        if received invalid session id
        """
        s = Session(
            "tokkuri.session.id=%s" % ('a' * 31),
            {'store.type': 'mock'}
        )
        self.assertTrue(s._is_new)
        self.assertEqual(s._vars, {})
        self.assertIsNone(Session.validate_id(s.id))
        self.assertIsNotNone(
            re.search("expires=", s.get_cookie_to_send().lower())
        )

    def test___init___timed_out(self):
        """It should start a new session sending expired cookie
        if session timed out
        """
        def _load(id): raise TimedOutException()
        mockstore.LOAD = _load
        s = Session(
            "tokkuri.session.id=%s" % ('a' * 32),
            {'store.type': 'mock'}
        )
        self.assertTrue(s._is_new)
        self.assertEqual(s._vars, {})
        self.assertIsNone(Session.validate_id(s.id))
        self.assertIsNotNone(
            re.search("expires=", s.get_cookie_to_send().lower())
        )

    def test_genid(self):
        """It should generate valid session id"""
        # Should generate valid formed session id
        self.assertIsNotNone(Session._ID_PATTERN.match(Session.genid()))

        # Should generate random id for each call
        ids = set(Session.genid() for i in range(10000))
        self.assertEqual(len(ids), 10000)

    def test_validate_id(self):
        """It should validate given id"""
        # Should pass if received valid id
        self.assertIsNone(Session.validate_id('0' * 32))
        self.assertIsNone(Session.validate_id('f' * 32))

        # Should raise TypeError if received invalid argument type
        self.assertRaises(TypeError, Session.validate_id, 0)
        self.assertRaises(TypeError, Session.validate_id, [])
        self.assertRaises(TypeError, Session.validate_id, {})
        self.assertRaises(TypeError, Session.validate_id, None)

        # Should raise ValueError if received invalid formed id
        self.assertRaises(ValueError, Session.validate_id, "")
        self.assertRaises(ValueError, Session.validate_id, "f" * 31)
        self.assertRaises(ValueError, Session.validate_id, "g" * 32)
        self.assertRaises(ValueError, Session.validate_id, "F" * 32)

    def test_save_new_session(self):
        """It should save session vars and set output cookie"""
        self.ns['key1'] = "string"
        self.ns['key2'] = 123
        self.ns.save()
        self.assertEqual(MockStore.calls[-1],
                         ('save', self.ns.id, {'key1': "string", 'key2': 123}))
        self.assertIsNotNone(
            re.search(self.ns.id, self.ns.get_cookie_to_send())
        )

    def test_save_existing_session(self):
        """It should save session vars"""
        self.es.save()
        self.assertEqual(MockStore.calls[-1],
                         ('save', self.es.id, {'key1': "string", 'key2': 123}))

        # Should not set output cookie if cookie attr not modified
        self.assertIsNone(self.ns.get_cookie_to_send())

        # Should set output cookie if cookie attr modified
        self.es.cookie.path = '/other'
        self.es.save()
        self.assertIsNotNone(
            re.search("path=/other", self.es.get_cookie_to_send().lower())
        )

    def test_save_cleared_session(self):
        """It should save session vars and set output cookie with new id"""
        # Clear session (should set cookie expired)
        self.es.clear()
        self.assertIsNotNone(
            re.search("%s.*expires=" % ('a' * 32),
                      self.es.get_cookie_to_send().lower())
        )

        # Save cleared session (should update output cookie)
        self.es.save()
        self.assertEqual(MockStore.calls[-1], ('save', self.es.id, {}))
        self.assertIsNone(
            re.search('a' * 32, self.es.get_cookie_to_send())
        )
        self.assertIsNotNone(
            re.search(self.es.id, self.es.get_cookie_to_send())
        )
        self.assertIsNone(
            re.search('expires', self.es.get_cookie_to_send().lower())
        )

    def test_clear(self):
        """It should clear current session"""
        old_id = self.es.id
        self.es.clear()
        self.assertTrue(self.es._is_new)
        self.assertEqual(self.es._vars, {})
        self.assertNotEqual(self.es.id, old_id)
        self.assertIsNotNone(
            re.search("%s.*expires=" % old_id,
                      self.es.get_cookie_to_send().lower())
        )

    def test___repr__(self):
        """It should return repr format string"""
        self.assertTrue(repr(self.ns).startswith(
            "Session(cookie_header=" + str(self.ns.cookie)
        ))
        self.assertTrue(repr(self.es).startswith(
            "Session(cookie_header=" + str(self.es.cookie)
        ))

    def test_get(self):
        """It should have dict#get method"""
        self.assertEqual(self.es.get('key1'), "string")
        self.assertEqual(self.es.get('key2'), 123)
        self.assertIsNone(self.es.get('key3'))
        self.assertEqual(self.es.get('key3', [1, 2, 3]), [1, 2, 3])

    def test_keys(self):
        """It should have dict#keys method"""
        self.assertEqual(self.ns.keys(), [])
        self.assertEqual(sorted(self.es.keys()), ['key1', 'key2'])

    def test_values(self):
        """It should have dict#values method"""
        self.assertEqual(self.ns.values(), [])
        self.assertEqual(sorted(self.es.values()), [123, "string"])

    def test_items(self):
        """It should have dict#items method"""
        self.assertEqual(self.ns.items(), [])
        self.assertEqual(sorted(self.es.items()),
                         [('key1', "string"), ('key2', 123)])

    def has_key(self):
        """It should have dict#has_key method"""
        self.assertTrue(self.es.has_key('key1'))
        self.assertTrue(self.es.has_key('key2'))
        self.assertFalse(self.es.has_key('key3'))

    def test___len__(self):
        """It should have dict#__len__ method"""
        self.assertEqual(len(self.ns), 0)
        self.assertEqual(len(self.es), 2)

    def test___getitem__(self):
        """It should have dict#__getitem__ method"""
        self.assertEqual(self.es['key1'], "string")
        self.assertEqual(self.es['key2'], 123)
        self.assertRaises(KeyError, self.es.__getitem__, 'key3')

    def test___setitem__(self):
        """It should have dict#__setitem__ method"""
        self.es['key1'] = "other"
        self.es['key2'] = [1, 2, 3]
        self.assertEqual(self.es['key1'], "other")
        self.assertEqual(self.es['key2'], [1, 2, 3])

    def test___delitem__(self):
        """It should have dict#__delitem__ method"""
        del self.es['key1']
        self.assertRaises(KeyError, self.es.__getitem__, 'key1')
        self.assertEqual(self.es['key2'], 123)

    def test___iter__(self):
        """It should have dict#__iter__ method"""
        keys = sorted([k for k in self.es])
        self.assertEqual(keys, ['key1', 'key2'])

    def test___contains__(self):
        """It should have dict#__contains__ method"""
        self.assertTrue('key1' in self.es)
        self.assertTrue('key2' in self.es)
        self.assertFalse('key3' in self.es)


if __name__ == '__main__':
    unittest.main()
