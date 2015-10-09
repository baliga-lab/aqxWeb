#!/usr/bin/env python
"""This is a script to add a measurement type for each
aquaponics system in the database
"""
import MySQLdb
import argparse

DESCRIPTION = """add_meastyp.py - add measurement type
"""
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--dbhost', default="localhost")
    parser.add_argument('--dbuser', default="aquaponics")
    parser.add_argument('--dbpass', default="aquaponics")
    parser.add_argument('--dbname', default="aquaponics")
    parser.add_argument('meastype', help="name of measurment type")
    args = parser.parse_args()

    conn = MySQLdb.connect(host=args.dbhost, user=args.dbuser,
                           passwd=args.dbpass, db=args.dbname)
    cursor = conn.cursor()
    cursor2 = conn.cursor()
    try:
        cursor.execute('select system_uid from systems')
        for row in cursor.fetchall():
            system_uid = row[0]
            query = "create table if not exists aqxs_%s_%s (time timestamp primary key not null, value decimal(13,10) not null)" % (args.meastype, system_uid)
            print query
            cursor2.execute(query)
    finally:
        if cursor:
            cursor.close()
        if cursor2:
            cursor2.close()
        if conn:
            conn.close()
