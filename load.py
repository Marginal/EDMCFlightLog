"""
An plugin for EDMC that outputs a flight log to "Flight Log.csv" in EDMC's output folder.
Duplicates functionality present in EDMC prior to version 2.15.

Version 1.00
"""

import atexit
from collections import defaultdict
import errno
import os
from os.path import join
from sys import platform
import time

if platform != 'win32':
    from fcntl import lockf, LOCK_SH, LOCK_NB

from config import config
from companion import ship_map


# Globals

logfile = None
last_timestamp = last_system = last_ship = None
last_commodities = {}


def writelog(timestamp, system, station=None, ship=None, commodities={}):

    global last_timestamp, last_system, last_ship, last_commodities
    if last_system and last_system != system:
        _writelog(last_timestamp, last_system, None, last_ship, last_commodities)

    if not station:
        # If not docked, hold off writing log entry until docked or until system changes
        last_timestamp, last_system, last_ship, last_commodities = timestamp, system, ship, commodities
    else:
        last_system = None
        _writelog(timestamp, system, station, ship, commodities)

def _writelog(timestamp, system, station=None, ship=None, commodities={}):

    logfile.write('%s,%s,%s,%s,%s,%s\r\n' % (
        time.strftime('%Y-%m-%d', time.localtime(timestamp)),
        time.strftime('%H:%M:%S', time.localtime(timestamp)),
        system,
        station or '',
        ship or '',
        ','.join([('%d %s' % (commodities[k], k)) for k in sorted(commodities)])))
    logfile.flush()

def close():
    if last_system:
        _writelog(last_timestamp, last_system, None, last_ship, last_commodities)
    logfile.close()


def plugin_start():
    # Open log file
    global logfile
    try:
        logfile = open(join(config.get('outdir'), 'Flight Log.csv'), 'a+b')
        if platform != 'win32':	# open for writing is automatically exclusive on Windows
            lockf(logfile, LOCK_SH|LOCK_NB)
        logfile.seek(0, os.SEEK_END)
        if not logfile.tell():
            logfile.write('Date,Time,System,Station,Ship,Cargo\r\n')
    except EnvironmentError as e:
        if logfile:
            logfile.close()
            logfile = None
        if e.errno in [errno.EACCES, errno.EAGAIN]:
            raise Exception('Can\'t write "Flight Log.csv". Are you editing it in another app?')
        else:
            raise
    except:
        if logfile:
            logfile.close()
            logfile = None
        raise
    atexit.register(close)

def system_changed(timestamp, system, coordinates):
    writelog(timestamp, system)

def cmdr_data(data):
    timestamp = config.getint('querytime') or int(time.time())

    commodities = defaultdict(int)
    for item in data['ship'].get('cargo',{}).get('items',[]):
        if item['commodity'] != 'drones':
            commodities[item['commodity']] += item['qty']

    writelog(timestamp,
             data['lastSystem']['name'],
             data['commander']['docked'] and data['lastStarport']['name'],
             ship_map.get(data['ship']['name'].lower(), data['ship']['name']),
             commodities)
