#!/usr/bin/env python

import MySQLdb
from datetime import datetime
from xml.dom import minidom


def insert_measurements(system_id, cursor, dataset):
    """
    Keys: Nitrate, pH, Ammonium, Temperature, Time
    There are duplicate measurements, which we filter out by
    catching the duplicate constraint exception
    """
    timepoints = dataset['Time']['values']
    for i, timepoint in enumerate(timepoints):
        try:
            table = "aqxs_temp_%s" % system_id
            cursor.execute('insert into ' + table + ' (time,value) values (%s,%s)',
                           [timepoint, dataset['Temperature']['values'][i]])
        except MySQLdb.IntegrityError:
            pass
        try:
            table = "aqxs_ph_%s" % system_id
            cursor.execute('insert into ' + table + ' (time,value) values (%s,%s)',
                           [timepoint, dataset['pH']['values'][i]])
        except MySQLdb.IntegrityError:
            pass
        try:
            table = "aqxs_ammonium_%s" % system_id
            cursor.execute('insert into ' + table + ' (time,value) values (%s,%s)',
                           [timepoint, dataset['Ammonium']['values'][i]])
        except MySQLdb.IntegrityError:
            pass

        try:        
            table = "aqxs_nitrate_%s" % system_id
            cursor.execute('insert into ' + table + ' (time,value) values (%s,%s)',
                           [timepoint, dataset['Nitrate']['values'][i]])
        except MySQLdb.IntegrityError:
            pass


def process_doc(system_id, cursor, data):
    xmldoc = minidom.parseString(data)
    datasets = xmldoc.getElementsByTagName('DataSet')
    result = []
    for dataset in datasets:
        current_set = {}
        result.append(current_set)

        columns = xmldoc.getElementsByTagName('DataColumn')
        # collect the column data of the current data set

        for item in columns:
            name = item.getElementsByTagName('DataObjectName')[0].childNodes[0].nodeValue
            short_name = item.getElementsByTagName('DataObjectShortName')[0].childNodes[0].nodeValue
            try:
                unit = item.getElementsByTagName('ColumnUnits')[0].childNodes[0].nodeValue
            except:
                unit = ''
            start_time = float(item.getElementsByTagName('StartTime')[0].childNodes[0].nodeValue)
            start_collect_time = float(item.getElementsByTagName('ColumnStartCollectTime')[0].childNodes[0].nodeValue)
            values = item.getElementsByTagName('ColumnCells')[0].childNodes[0].nodeValue.strip().split()
            values = map(float, values)
            if name == 'Time':
                values = [datetime.utcfromtimestamp(inc_time + start_time) for inc_time in values]

            current_set[name] = {'short_name': short_name, 'unit': unit, 'values': values}

    # data extracted into a list of dictionaries
    for dataset in result:
        time_points = dataset['Time']['values']
        num_timepoints = len(time_points)
        # check length
        for key, col in dataset.items():
            num_values = len(col['values'])
            if num_values != num_timepoints:
                raise Exception("# values for %s = %d, != %d" % (key, num_values, num_timepoints))

        insert_measurements(system_id, cursor, dataset)


if __name__ == '__main__':
    conn = MySQLdb.connect(host='localhost', user='aquaponics',
                           passwd='aquaponics', db='aquaponics')
    cursor = conn.cursor()
    try:
        with open('example.cmbl') as infile:
            data = infile.read()
        process_doc("aa56fa203bcb11e58c8864273763ec8b", cursor, data)
        conn.commit()
    finally:
        cursor.close()
        conn.close()
