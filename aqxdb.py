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
    result = [[str(time), float(value)] for time, value in cursor.fetchall()]
    result = result[::-1]  # we need to reverse the list for displaying the right time order
    return result


def create_aquaponics_system(cursor, user_pk, name):
    """Create the entry and tables for a user's Aquaponics system"""
    system_uid = new_system_id()
    cursor.execute('insert into systems (user_id,name,system_id,creation_time) values (%s,%s,%s,now())',
                   [user_pk, name, system_uid])
    for table_name in meas_table_names(system_uid):
        query = "create table if not exists %s (time timestamp primary key not null, value decimal(13,10) not null)" % table_name
        cursor.execute(query)


def update_system_details(cursor, system_uid, data):
    """update the Aquaponics system details
    This rather lengthy procedure ensures we have some checking in place
    so we can only update certain fields
    Note: caller should check if system uid can be updated by the current user"""
    if len(data) > 0:
        # Explicitly check all parameters to sanitize what
        # goes into the database
        params = []
        setters = []
        num_orgs = 0
        num_crops = 0
        query = "update systems set "        
        if 'start_date' in data:
            setters.append('start_date=%s')
            params.append(data['start_date'])
        if 'aqx_technique_id' in data:
            setters.append('aqx_technique_id=%s')
            params.append(data['aqx_technique_id'])

        query += ",".join(setters)
        query += " where system_id=%s"
        params.append(system_uid)
        cursor.execute(query, params)
        cursor.execute('select id from systems where system_id=%s', system_uid)
        system_pk = cursor.fetchone()[0]

        if 'aquatic_org_id' in data:
            org_pk = int(data['aquatic_org_id'])

            if 'num_aquatic_org' in data:
                num_orgs = int(data['num_aquatic_org'])

            # 1. update existing entry
            cursor.execute('select count(*) from system_aquatic_organisms where system_id=%s',
                           system_pk)
            if cursor.fetchone()[0] > 0:
                cursor.execute('update system_aquatic_organisms set organism_id=%s, num=%s where system_id=%s',
                               [org_pk, num_orgs, system_pk])
            else:
                # 2. or create if not
                cursor.execute('insert into system_aquatic_organisms (system_id,organism_id,num) values (%s,%s,%s)',
                               [system_pk, org_pk, num_orgs])

        if 'crop_id' in data:
            crop_pk = int(data['crop_id'])
            if 'num_crops' in data:
                num_crops = int(data['num_crops'])
                                
            # 1. update existing entry
            cursor.execute('select count(*) from system_crops where system_id=%s', system_pk)
            if cursor.fetchone()[0] > 0:
                cursor.execute('update system_crops set crop_id=%s, num=%s where system_id=%s',
                               [crop_pk, num_crops, system_pk])
            else:
                # 2. or create if not
                cursor.execute('insert into system_crops (system_id,crop_id,num) values (%s,%s,%s)',
                               [system_pk, crop_pk, num_crops])


def get_system_aqx_organism(cursor, sys_uid):
    cursor.execute('select organism_id, num from system_aquatic_organisms sao join systems s on sao.system_id=s.id where s.system_id=%s', [sys_uid])
    row = cursor.fetchone()
    if row is not None:
        return row[0], row[1]
    else:
        return None, ''


def get_system_crop(cursor, sys_uid):
    cursor.execute('select crop_id, num from system_crops sc join systems s on sc.system_id=s.id where s.system_id=%s', [sys_uid])
    row = cursor.fetchone()
    if row is not None:
        return row[0], row[1]
    else:
        return None, ''


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

"""
Some values come from catalog tables, we will only extract from
tables that are known as catalogs
"""
CATALOGS = {'crops', 'aqx_techniques', 'aquatic_organisms'}


def all_catalog_values(cursor, name):
    if name in CATALOGS:
        query = 'select id,name from %s order by name' % name
        cursor.execute(query)
        return [(pk, name) for pk, name in cursor.fetchall()]
    else:
        return []


def get_catalog_value(cursor, name, pk):
    if name in CATALOGS and pk is not None:
        query = "select name from %s" % name
        query += " where id=%s"
        cursor.execute(query, pk)
        row = cursor.fetchone()
        if row is not None:
            return cursor.fetchone()[0]
    return None
