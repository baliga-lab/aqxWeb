import os
import app
import unittest
import json

"""
Run from top-level with:

AQUAPONICS_SETTINGS=settings_test.cfg PYTHONPATH=. python tests/simple_test.py
"""
TEST_GOOGLE_ID = '108935443071440000056'
TEST_SYSTEM_UID = '1e3dc0c08fbb11e5bbf5dc0ea155dce8'

class ApiTest(unittest.TestCase):
    def setUp(self): 
        self.app = app.app.test_client()

    def tearDown(self):
        pass

    def test_api_techniques(self):
        response = self.app.get('/api/v1.0/techniques')
        result = json.loads(response.data)
        self.assertNotEqual(len(result), 0, 'techniques exist')

    def test_api_botanic_crops(self):
        response = self.app.get('/api/v1.0/botanic_crops')
        result = json.loads(response.data)
        self.assertNotEqual(len(result), 0, 'botanic crops exist')

    def test_api_aquatic_crops(self):
        response = self.app.get('/api/v1.0/aquatic_crops')
        result = json.loads(response.data)
        self.assertNotEqual(len(result), 0, 'aquatiic crops exist')

    def test_api_user_systems(self):
        """Authenticated user systems"""
        response = self.app.get('/api/v1.0/systems', headers={'GOOGLE_ID': TEST_GOOGLE_ID})
        result = json.loads(response.data)
        self.assertTrue("error" not in result)

    def test_api_get_system_details(self):
        """Authenticated user system details"""
        response = self.app.get('/api/v1.0/system/%s' % TEST_SYSTEM_UID,
                                headers={'GOOGLE_ID': TEST_GOOGLE_ID})
        result = json.loads(response.data)
        #print result
        self.assertTrue("error" not in result)

if __name__ == '__main__':
    unittest.main()
