#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import time
import json
import sqlite3
import os
import sys

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(TESTS_DIR))

from tokkuri import SQLiteStore, TimedOutException

DB_PATH = os.path.join(TESTS_DIR, 'test_sqlitestore.sqlite')


def get_session(id):
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c.execute("SELECT * FROM sessions WHERE id = ?", (id,)).fetchone()


class TestSQLiteStore(unittest.TestCase):
    """Test cases for SQLiteStore class"""

    def setUp(self):
        # Create instance
        self.s = SQLiteStore(
            timeout=60,
            config={
                'path': DB_PATH,
            }
        )

    def tearDown(self):
        # Remove test db if exists
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)

    def test_save(self):
        """It should save a given session in db"""
        # Save sessions
        self.s.save('0123', {'key1': 'value', 'key2': 123})
        self.s.save('9876', {'key1': [1,2,3], 'key2': {'foo': 'bar'}})

        # Fetch saved sessions
        s1 = get_session('0123')
        s2 = get_session('9876')

        now = time.time()

        # Check s1
        self.assertEqual(s1['id'], '0123')
        self.assertTrue(0 < s1['ctime'] and s1['ctime'] < now + 1)
        self.assertTrue(0 < s1['atime'] and s1['atime'] < now + 1)
        self.assertEqual(json.loads(s1['vars']),
                         {'key1': 'value', 'key2': 123})

        # Check s2
        self.assertEqual(s2['id'], '9876')
        self.assertTrue(0 < s2['ctime'] and s2['ctime'] < now + 1)
        self.assertTrue(0 < s2['atime'] and s2['atime'] < now + 1)
        self.assertEqual(json.loads(s2['vars']),
                         {'key1': [1,2,3], 'key2': {'foo': 'bar'}})

        # Update s1
        time.sleep(1)
        self.s.save('0123', {'key3': 0.1})
        _s1 = get_session('0123')

        # Check _s1
        self.assertEqual(_s1['id'], '0123')
        self.assertEqual(s1['ctime'], _s1['ctime'])
        self.assertTrue(s1['atime'] < _s1['atime'])
        self.assertEqual(json.loads(_s1['vars']), {'key3': 0.1})

        # Delete session if no vars to be saved
        self.s.save('0123', {})
        self.assertIsNone(get_session('0123'))

    def test_load(self):
        """It should load a saved session"""
        # Should raise exception if session not found
        self.assertRaises(TimedOutException, self.s.load, '0123')

        # Save sessions
        self.s.save('0123', {'key1': 'value', 'key2': 123})
        self.s.save('9876', {'key1': [1,2,3], 'key2': {'foo': 'bar'}})

        # Load sessions
        vars1 = self.s.load('0123')
        vars2 = self.s.load('9876')

        # Check
        self.assertEqual(vars1, {'key1': 'value', 'key2': 123})
        self.assertEqual(vars2, {'key1': [1,2,3], 'key2': {'foo': 'bar'}})

        # Should raise exception if session timed out
        self.s.timeout = -1
        self.assertRaises(TimedOutException, self.s.load, '0123')

    def test_gc(self):
        """It should delete expired sessions"""
        # Save sessions
        self.s.save('0123', {'key1': 'value', 'key2': 123})
        time.sleep(1)
        self.s.save('9876', {'key1': [1,2,3], 'key2': {'foo': 'bar'}})

        # Execute gc
        self.s.timeout = 0
        self.s.gc()

        # Should delete expired sessions only
        self.assertIsNone(get_session('0123'))
        self.assertIsNotNone(get_session('9876'))


if __name__ == '__main__':
    unittest.main()
