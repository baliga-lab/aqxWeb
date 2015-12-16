#!/usr/bin/env python
import sys
import unittest
import xmlrunner

import app_test, api_test, auth_app_test

"""
A test suite that can be used from a CI system. Contains an XML runner and
includes all unit test cases

AQUAPONICS_SETTINGS=settings_test.cfg PYTHONPATH=. python tests/all_tests.py [xml]
"""

if __name__ == '__main__':
    SUITE = []
    SUITE.append(unittest.TestLoader().loadTestsFromTestCase(app_test.AnonymousAppTest))
    SUITE.append(unittest.TestLoader().loadTestsFromTestCase(auth_app_test.AuthAppTest))
    SUITE.append(unittest.TestLoader().loadTestsFromTestCase(api_test.ApiTest))

    if len(sys.argv) > 1 and sys.argv[1] == 'xml':
      xmlrunner.XMLTestRunner(output='test-reports').run(unittest.TestSuite(SUITE))
    else:
      unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(SUITE))
