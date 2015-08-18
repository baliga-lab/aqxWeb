"""aqxdb.py - Aquaponics Database interface module

The access to the main storage database is controlled here
"""
from datetime import datetime
import uuid


ATTR_NAMES = {'ammonium', 'o2', 'ph', 'nitrate', 'light', 'temp'}


def get_or_create_user(conn, cursor, google_id, email):
    cursor.execute('select id from users where google_id=%s', [google_id])
    row = cursor.fetchone()
    if row is None:
        # create user
        cursor.execute('insert into users (google_id, email) values (%s,%s)', [google_id, email])
        result = cursor.lastrowid
        conn.commit()
    else:
        result = row[0]
    return result

def new_system_id():
    """Generates a new system id"""
    return uuid.uuid1().hex


def is_system_owner(cursor, sys_uid, user_id=None, google_id=None):
    if user_id is not None:
        cursor.execute('select count(*) from systems where system_id=%s and user_id=%s',
                    [sys_uid, user_id])
        return cursor.fetchone()[0] > 0
    elif google_id is not None:
        print "GOOGLE ID"
        cursor.execute('select count(*) from systems s join users u on s.user_id=u.id where system_id=%s and u.google_id=%s',
                       [sys_uid, google_id])
        return cursor.fetchone()[0] > 0
    return False


def meas_table_name(system_uid, attr):
    return "aqxs_%s_%s" % (attr, system_uid)


def meas_table_names(system_uid):
    return [meas_table_name(system_uid, attr) for attr in ATTR_NAMES]


def get_latest_measurement(cursor, sys_uid, attr):
    cursor.execute("select value from " + meas_table_name(sys_uid, attr) + " order by time desc limit 1")
    row = cursor.fetchone()
    return None if row is None else row[0]


def systems_and_latest_measurements(cursor, user_id):
    cursor.execute('select s.id,s.name,system_id from systems s join users u on s.user_id=u.id where google_id=%s',
                   [user_id])
    systems = [{'pk': pk, 'name': name, 'sys_uid': sys_id}
               for pk, name, sys_id in cursor.fetchall()]
    now = datetime.now()

    for system in systems:            
        sys_uid = system['sys_uid']
        system['time'] = now
        system['temperature'] = get_latest_measurement(cursor, sys_uid, 'temp')
        system['ph'] = get_latest_measurement(cursor, sys_uid, 'ph')
        system['oxygen'] = get_latest_measurement(cursor, sys_uid, 'o2')
        system['ammonium'] = get_latest_measurement(cursor, sys_uid, 'ammonium')
        system['nitrate'] = get_latest_measurement(cursor, sys_uid, 'nitrate')
        # TODO: light                        
    return systems

def get_measurement_series(cursor, sys_uid, attr):
    cursor.execute("select time, value from " + meas_table_name(sys_uid, attr) + " order by time desc limit 100")
    return [[str(time), float(value)] for time, value in cursor.fetchall()]


def create_aquaponics_system(cursor, user_pk, name):
    """Create the entry and tables for a user's Aquaponics system"""
    system_uid = new_system_id()
    cursor.execute('insert into systems (user_id,name,system_id,creation_time) values (%s,%s,%s,now())',
                   [user_pk, name, system_uid])
    for table_name in meas_table_names(system_uid):
        query = "create table if not exists %s (time timestamp primary key not null, value decimal(13,10) not null)" % table_name
        cursor.execute(query)


def add_measurement(cursor, sys_uid, attr, timestamp, value):
    table = meas_table_name(sys_uid, attr)
    query = 'insert into ' + table + ' (time,value) values (%s,%s)'
    cursor.execute(query, [timestamp, value])

def set_default_site_location(cursor, user_pk, lat, lng):
    locstring = "%f:%f" % (lat, lng)
    cursor.execute('update users set default_site_location=%s where id=%s',
                   [locstring, user_pk])

def get_default_site_location(cursor, user_pk):
    cursor.execute('select default_site_location from users where id=%s', [user_pk])
    row = cursor.fetchone()
    if row is not None and row[0] is not None:
        coords = map(float, row[0].split(':'))
        return {'lat': coords[0], 'lng': coords[1]}
    else:
        return None
