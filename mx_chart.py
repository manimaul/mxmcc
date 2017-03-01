#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2017, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Assembles a "mx_chart" (sqlite) chart file from a directory structure of zxy tiles.
'''

import sqlite3
import os.path

MX_CHART_EXTENSION = ".mxc"
MX_CHART_VERSION = 1

SCHEMA = ("""CREATE TABLE tiles (zxy TEXT UNIQUE, png, BLOB);""",
          """CREATE TABLE meta (m_key TEXT UNIQUE, val);""",
          """CREATE UNIQUE INDEX meta_index on meta(m_key);""",
          """CREATE UNIQUE INDEX tiles_index on tiles(zxy);""")


def _optimize_database(cur):
    cur.execute("""ANALYZE;""")
    cur.execute("""VACUUM;""")


def _optimize_connection(cur):
    cur.execute("""PRAGMA synchronous=0""")
    cur.execute("""PRAGMA locking_mode=EXCLUSIVE""")
    cur.execute("""PRAGMA journal_mode=DELETE""")


def _add_meta_data(cur, key, value):
    cur.execute("""INSERT INTO meta (m_key, val) values (?, ?)""", (str(key), value))


def disk_to_mx_chart(directory_path, file_out_path, name, outline, updated, depth_units, scale):
    con = sqlite3.connect(file_out_path)
    cur = con.cursor()
    _optimize_connection(cur)
    for sql in SCHEMA:
        cur.execute(sql)

    min_x = None
    max_x = None
    min_y = None
    max_y = None
    chart_z = None

    for z_dir in os.listdir(directory_path):
        try:
            z = int(z_dir)
            if chart_z is not None:
                raise Exception("Only 1 zoom level allowed per chart")
            chart_z = z

        except ValueError:
            print "skipping file: {}".format(os.path.join(directory_path, z_dir))
            continue
        for x_dir in os.listdir(os.path.join(directory_path, z_dir)):
            try:
                x = int(x_dir)
                if min_x is None and max_x is None:
                    min_x = x
                    max_x = x
                else:
                    min_x = min(x, min_x)
                    max_x = max(x, max_x)
            except ValueError:
                print "skipping file: {}".format(os.path.join(directory_path, z_dir, x_dir))
                continue
            for y_png in os.listdir(os.path.join(directory_path, z_dir, x_dir)):
                y = int(y_png[:-4])
                if min_y is None and max_y is None:
                    min_y = y
                    max_y = y
                else:
                    min_y = min(y, min_y)
                    max_y = max(y, max_y)
                zxy = '{}/{}/{}'.format(z, x, y)
                fd = open(os.path.join(directory_path, z_dir, x_dir, y_png))
                cur.execute("""INSERT INTO tiles (zxy, png) values (?, ?);""", (zxy, sqlite3.Binary(fd.read())))
                fd.close()

    if min_x is None or max_x is None or min_y is None or max_y is None or chart_z is None:
        os.remove(file_out_path)
    else:
        _add_meta_data(cur, "name", str(name))
        _add_meta_data(cur, "outline", str(outline))
        _add_meta_data(cur, "updated", str(updated))
        _add_meta_data(cur, "depth_units", str(depth_units))
        _add_meta_data(cur, "scale", str(scale))
        _add_meta_data(cur, "zoom", str(chart_z))
        _add_meta_data(cur, "min_x", str(min_x))
        _add_meta_data(cur, "max_x", str(max_x))
        _add_meta_data(cur, "min_y", str(min_y))
        _add_meta_data(cur, "max_y", str(max_y))
        _add_meta_data(cur, "version", str(MX_CHART_VERSION))
        _optimize_database(cur)


"""m_key:val Key values
    name        : string(the name of the chart e.g. "PUGET SOUND")
    outline     : string(linear ring wkt of the chart's outline in WGS84 coordinates)
    updated     : integer(the unix epoch time since 1970 in seconds when the chart was upated)
    depth_units : string(chart depths unit of measure e.g. METRES, FATHOMS)
    scale       : integer(the chart scale as 1:<scale>)
    zoom        : integer(the zoom level of detail)
    min_x       : integer(the chart's min x coordinate)
    max_x       : integer(the chart's max x coordinate)
    min_y       : integer(the chart's min y coordinate)
    max_y       : integer(the chart's max y coordinate)
    version     : integer(the file version)
"""
