* Aquaponic Site

* Dependencies

  - >= Python 2.7.6
  - MySQL Server
  - Flask, Werkzeug, Jinja2
  - python-MySQLdb
  - python-flask-cors
  - ImageMagick
  - python-wand

* Deployment

Uses mod_wsgi to deploy, see file `aquaponics.wsgi`

* Testing

Unit tests are in tests, there is a separate settings.cfg file for
testing, called `settings_test.cfg`.

Requires a database `aquaponics_test` to be created in mysql.

Run with:
```
AQUAPONICS_SETTINGS=settings_test.cfg PYTHONPATH=. python tests/all_tests.py [xml]
```
