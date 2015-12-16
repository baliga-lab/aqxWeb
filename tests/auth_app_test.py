import os
import app
import unittest
import flask

"""
Authenticated web app tests
"""
TEST_GOOGLE_ID = '108935443071440000056'
TEST_SYSTEM_UID = '1e3dc0c08fbb11e5bbf5dc0ea155dce8'

class AuthAppTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()
        with self.app.session_transaction() as sess:
            sess['google_id'] = TEST_GOOGLE_ID
            sess['logged_in'] = True

    def tearDown(self):
        pass

    def test_index_exists(self):
        response = self.app.get('/')
        self.assertFalse(response.status == '404 NOT FOUND')

    def test_dashboard(self):
        response = self.app.get('/home')
        #print response.data
        self.assertFalse(response.status == '404 NOT FOUND')
        self.assertTrue('Unknown Error' not in response.data)
        self.assertTrue('Your Aquaponics Systems' in response.data)


if __name__ == '__main__':
    unittest.main()
