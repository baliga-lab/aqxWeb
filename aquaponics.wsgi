import sys, os
sys.path.insert(0, '/local/apache-stuff/aquaponics_site')
os.environ['PYTHON_EGG_CACHE'] = '/local/apache-stuff/python_egg_cache'
os.environ['AQUAPONICS_REPO_SETTINGS'] = '/local/apache-stuff/aquaponics_site/settings.cfg'
from app import app as application
