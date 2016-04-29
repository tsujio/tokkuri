#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os
import sys

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(TESTS_DIR))
sys.path.insert(0, TESTS_DIR)

import tokkuri
from tokkuri import SessionInterface
import mockstore
from mockstore import MockStore

# Use mock store for saving sessions
tokkuri.STORES = {'mock': MockStore}


class TestSessionInterface(unittest.TestCase):
    """Test cases for SessionInterface class"""

    def setUp(self):
        # Create instance
        mockstore.LOAD = lambda id: {'key1': 'string', 'key2': 123}
        self.s = SessionInterface(
            cookie_header="tokkuri.session.id=%s;" % ('a' * 32),
            config={'store.type': 'mock'}
        )

    def tearDown(self):
        mockstore.SAVE = mockstore.DEFAULT_SAVE
        mockstore.LOAD = mockstore.DEFAULT_LOAD

    def test_session(self):
        """It should create session instance only once"""
        s = SessionInterface(config={'store.type': 'mock'})
        s1 = s.session()
        s2 = s.session()
        self.assertIs(s1, s2)

    def test_accessed(self):
        """It should test a session accessed or not"""
        self.assertFalse(self.s.accessed())
        self.s['key1'] = "string"
        self.assertTrue(self.s.accessed())
        self.assertEqual(self.s.id, 'a' * 32)


if __name__ == '__main__':
    unittest.main()
