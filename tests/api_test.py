import os
import app
import unittest
import json

"""
Run from top-level with:

AQUAPONICS_SETTINGS=settings_test.cfg PYTHONPATH=. python tests/simple_test.py
"""
class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

    def tearDown(self):
        pass

    def test_api_techniques(self):
        response = self.app.get('/api/v1.0/techniques')
        result = json.loads(response.data)
        self.assertNotEqual(len(result), 0, 'techniques exist')

if __name__ == '__main__':
    unittest.main()
