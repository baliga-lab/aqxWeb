"""csvimport.py - CSV import module
"""
import csv
import time
from datetime import datetime
import flask

import aqxdb

IMPORT_ATTR_NAMES = {'time', 'ammonium', 'o2', 'ph', 'nitrate', 'light', 'temperature'}
IMPORT_ATTR_MAP = {
    'ammonium': 'ammonium',
    'o2': 'o2',
    'ph': 'ph',
    'nitrate': 'nitrate',
    'light': 'light',
    'temperature': 'temp'
}

TIME_FORMATS = [
    '%m/%d/%Y %H:%M',
    '%m/%d/%y %H:%M',
    '%m/%d/%Y %H:%M:%S',
    '%m/%d/%y %H:%M:%S'
]

def check_titles(titles, error_messages):
    """Check for the possible errors in document titles"""
    ok = True
    unknown_titles = {unicode(title, 'utf-8') for title in titles
                      if title not in IMPORT_ATTR_NAMES}
    if len(unknown_titles) > 0:
        error_messages.append("There are problems in your import document")
        for unknown_title in unknown_titles:
            error_messages.append("Unknown document title: '%s'." % flask.escape(unknown_title))
        ok = False
    if "time" not in titles:
        error_messages.append("Your import document does not contain the mandatory 'time' attribute")
        ok = False
    if len(set(titles)) != len(titles):
        error_messages.append("Your import document does not contain the mandatory 'time' attribute")
        ok = False
    return ok


def get_time(row, time_index):
    value = row[time_index]
    for time_format in TIME_FORMATS:
        try:
            result = datetime.fromtimestamp(time.mktime(time.strptime(value, time_format)))
            return result
        except:
            pass
    return None


def import_measurement_file(app, conn, sys_uid, csvfile, filename):
    error_messages = []
    cursor = conn.cursor()
    try:
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)
        # only import after a complete consistency check
        check_measurement_file(app, reader, filename, error_messages)

        # now import
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)
        titles = reader.next()
        title_indexes = {title: i for i, title in enumerate(titles)}
        time_index = title_indexes['time']
        for row in reader:
            timestamp = get_time(row, time_index)
            for i, value in enumerate(row):
                if i != time_index:
                    attr_name = titles[i]
                    mvalue = float(value)
                    try:
                        table = aqxdb.meas_table_name(sys_uid, IMPORT_ATTR_MAP[attr_name])
                        cursor.execute('insert into ' + table + ' (time,value) values (%s,%s)',
                                       [timestamp, mvalue])
                    except Exception, e:
                        pass
    except Exception, e:
        # this exception is often thrown by csv.Sniffer when the format
        # is not recognized
        app.logger.exception(e)
        error_messages.append("The provided file '%s' most likely is not a CSV file" % filename)
    return error_messages


def check_measurement_file(app, reader, filename, error_messages):
    """This is the preliminary sanity check for CSV files"""
    titles = reader.next()
    if check_titles(titles, error_messages):
        # headers are valid, now check the input
        title_indexes = {title: i for i, title in enumerate(titles)}
        time_index = title_indexes['time']

        for row in reader:
            timestamp = get_time(row, time_index)
            if timestamp is None:
                error_messages.append("invalid time value '%s' in line %d" % (row[time_index],
                                                                              reader.line_num))
            for i, value in enumerate(row):
                if i != time_index:
                    attr_name = titles[i]
                    try:
                        float(value)
                    except:
                        error_messages.append("invalid value '%s' in line %d for '%s'" % (value, reader.line_num, attr_name))
                        return
