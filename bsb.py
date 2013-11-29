#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Scans the header portion of a BSB nautical chart, extracts data and offers
   convenient methods for accessing chart meta data
'''

import os.path
from re import sub

import findzoom


class BsbHeader():
    def __init__(self, map_path):
        self.map_path = map_path
        self.updated = None
        self.name = None
        self.lines = []
        self.poly = []
        self.refs = []
        self.scale = None
        self.projection = None
        self.units = None
        self.datum = None
        self._read_header(map_path)

    def _read_header(self, map_path):
        with open(map_path, 'rU') as map_file:
            for line in map_file:
                if '\x1A' in line:
                    break
                line = line.decode('cp1252', 'ignore')
                self.lines.append(line)
                if line.find('KNP/SC') > -1:
                    line = line.lstrip('KNP/')
                    values = line.split(',')
                    for val in values:
                        if val.startswith('SC='):
                            self.scale = int(val[3:len(val)])
                        elif val.startswith('PR='):
                            self.projection = val[3:len(val)]
                        elif val.startswith('GD='):
                            self.datum = val[3:len(val)]

                elif line.find('REF/') > -1:
                    ref = sub('REF/[0-9]*,', '', line).rstrip('\r\n')
                    self.refs.append(ref)

                elif line.find('UN=') > -1:
                    li = line.find('UN=') + 3
                    ri = line.find(',', li)
                    self.units = line[li:ri]

                elif line.find('CED/SE') > -1:
                    li = line.find('ED=') + 3
                    ri = li + 11
                    self.updated = line[li:ri]

                elif line.find('BSB/NA') > -1:
                    li = line.find('BSB/NA=') + 7
                    ri = line.find(',')
                    self.name = line[li:ri]

                elif line.find('PLY/') > -1:
                    lat = line.split(',')[1].lstrip(',')
                    lon = float(line.split(',')[2])
                    ply = lat + ',' + str(lon)
                    self.poly.append(ply.rstrip())
        if self.poly.__len__() > 0:
            self.poly.append(self.poly[0])  # add first coord to close polygon

    def get_is_valid(self):
        if self.scale is None or 'Cover for Chart' in self.name:
            return False

        return True

    def get_lines(self):
        return self.lines

    def get_updated(self):
        return self.updated.strip()

    def get_scale(self):
        return self.scale

    def get_zoom(self):
        if self.scale is None:
            return 0

        return findzoom.get_zoom(self.scale, self.get_center()[1])

    def get_projection(self):
        return self.projection.strip()

    def get_datum(self):
        return self.datum.strip()

    def get_base_filename(self):
        return os.path.basename(self.map_path)

    def get_name(self):
        return self.name.strip().replace('\'', '')

    def get_poly_list(self):
        return self.poly

    def get_outline(self):
        outline = ''
        for ply in self.get_poly_list():
            outline += ply + ':'
        return outline.rstrip(':')

    def get_depth_units(self):
        if self.units is None:
            self.units = 'Unknown'
        return self.units

    def crosses_dateline(self):
        lngs = []
        for ll in self.poly:
            lng = ll.split(',')[1]
            lngs.append(float(lng))

        if len(lngs) is 0:
            return False

        return min(lngs) < 0 and max(lngs) > 0

    def has_duplicate_refs(self):
        for ea in self.refs:
            if self.refs.count(ea) > 1:
                return True
        return False

    def get_center(self):
        lats = []
        lngs = []
        for ll in self.poly:
            lat, lon = ll.split(',')
            lats.append(float(lat))
            lngs.append(float(lon))

        if len(lats) is 0:
            centerlat = 0
        else:
            centerlat = min(lats) + (max(lats) - min(lats)) / 2

        if len(lngs) is 0:
            centerlng = 0
        else:
            centerlng = min(lngs) + (max(lngs) - min(lngs)) / 2

        return centerlng, centerlat

    def print_header(self):
        for line in self.lines:
            print line.strip()