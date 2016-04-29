#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import datetime
import os
import sys

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(TESTS_DIR))

from tokkuri import SessionCookie


class TestSessionCookie(unittest.TestCase):
    """Test cases for SessionCookie class"""

    def setUp(self):
        # Create instance
        self.c = SessionCookie(cookie_header=None)

    def tearDown(self):
        pass

    def test___init___with_cookie(self):
        """It should initialize with the given cookie header"""
        c = SessionCookie(
            ("tokkuri.session.id=0123; "
             "Domain=example.com; "
             "Path=/; "
             "Expires=Fri, 29-Apr-2016 23:35:15 GMT")
        )
        d = datetime.datetime.strptime("Fri, 29-Apr-2016 23:35:15 GMT",
                                       "%a, %d-%b-%Y %H:%M:%S GMT")
        self.assertEqual(c.value, '0123')
        self.assertEqual(c.domain, 'example.com')
        self.assertEqual(c.path, '/')
        self.assertEqual(c.secure, False)
        self.assertEqual(c.httponly, False)
        self.assertEqual(c.expires, d)

    def test___init__without_cookie(self):
        """It should initialize as empty cookie"""
        c = SessionCookie(None)
        self.assertIsNone(c.value)
        self.assertEqual(c.domain, '')
        self.assertEqual(c.path, '')
        self.assertEqual(c.secure, False)
        self.assertEqual(c.httponly, False)
        self.assertEqual(c.expires, '')


if __name__ == '__main__':
    unittest.main()
