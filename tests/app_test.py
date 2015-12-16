import os
import app
import unittest
import flask

"""
Test cases for anonymous web app use.
"""

class AnonymousAppTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

    def tearDown(self):
        pass

    def test_index_exists(self):
        response = self.app.get('/')
        self.assertFalse(response.status == '404 NOT FOUND')


    def test_explore_exists(self):
        response = self.app.get('/aqx-map')
        self.assertFalse(response.status == '404 NOT FOUND')

if __name__ == '__main__':
    unittest.main()
