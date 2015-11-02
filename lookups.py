#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''This contains methods for looking up information about a region chart file.
   The lookup methods are used by catalog.py to build a catalog of charts for
   a region.
'''

import datetime
import os

import bsb
import ukho_xlrd_lookup
import findzoom
import gdalds
import config

# coordinates need to be longitude,latitude,altitude
cutline_kml = '''<?xml version='1.0' encoding='UTF-8'?>
<kml xmlns='http://www.opengis.net/kml/2.2'>
  <Placemark>
    <name>cutline</name>
    <Polygon>
      <extrude>1</extrude>
      <altitudeMode>relativeToGround</altitudeMode>
      <outerBoundaryIs>
        <LinearRing>
          <coordinates>%s</coordinates>
        </LinearRing>
      </outerBoundaryIs>
    </Polygon>
  </Placemark>
</kml>
'''


def _get_cutline_kml(poly):
    return cutline_kml % (''.join('%s,%s,0 ' % (ea.split(',')[1], ea.split(',')[0]) for ea in poly))


def get_cutline_kml(poly_string):
    poly = []
    for coord_str in poly_string.split(':'):
        poly.append(coord_str)
    return _get_cutline_kml(poly)


class Lookup(object):
    """Lookup information using the bsb header"""
    def __init__(self):
        self.lookup_db = {}

    def _get(self, map_path):
        return self.lookup_db[map_path]

    def get_name(self, map_path):
        return self._get(map_path).get_name()

    def get_zoom(self, map_path):
        return self._get(map_path).get_zoom()

    def get_scale(self, map_path):
        return self._get(map_path).get_scale()

    def get_updated(self, map_path):
        return self._get(map_path).get_updated()

    def get_depth_units(self, map_path):
        return self._get(map_path).get_depth_units()

    def get_outline(self, map_path):
        return self._get(map_path).get_outline()

    def get_is_valid(self, map_path):
        return self._get(map_path).get_is_valid()


class BsbLookup(Lookup):

    def _get(self, map_path):
        if map_path not in self.lookup_db:
            self.lookup_db[map_path] = bsb.BsbHeader(map_path)

        # noinspection PyProtectedMember
        return super(BsbLookup, self)._get(map_path)


class UKHOLookup(Lookup):
    """Lookup information using the ukho excel meta data files"""
    def __init__(self):
        super(UKHOLookup, self).__init__()
        self.meta_lookup = ukho_xlrd_lookup.MetaLookup()

    def _get(self, map_path):
        return self.meta_lookup.get_data(map_path)

    def get_zoom(self, map_path):
        data_set = gdalds.get_ro_dataset(map_path)
        true_scale = gdalds.get_true_scale(data_set, config.ukho_chart_dpi)
        return findzoom.get_zoom_from_true_scale(true_scale)


class BsbGdalMixLookup(Lookup):
    """Lookup information using information coded in file names"""
    def __init__(self):
        super(BsbGdalMixLookup, self).__init__()
        self.bsb_lookup = BsbLookup()

    def _is_bsb(self, map_path):
        return map_path.upper().endswith('KAP')

    def get_name(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_name(map_path)

        return os.path.basename(map_path)[:-4]

    def get_zoom(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_zoom(map_path)

        return findzoom.get_zoom_from_true_scale(self.get_scale(map_path)) + 1

    def get_scale(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_scale(map_path)

        data_set = gdalds.get_ro_dataset(map_path)
        return int(gdalds.get_true_scale(data_set, 400))

    def get_updated(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_updated(map_path)

        return datetime.datetime.now().strftime('%b-%d-%Y')

    def get_depth_units(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_depth_units(map_path)

        return 'Unknown'

    def get_outline(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_outline(map_path)

        return self.get_outline_bounds(map_path)

    def get_outline_bounds(self, map_path):
        data_set = gdalds.get_ro_dataset(map_path)
        return gdalds.dataset_lat_lng_bounds_as_cutline(data_set)

    def get_is_valid(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_is_valid(map_path)

        return True


class WaveylinesLookup(BsbGdalMixLookup):
    """Lookup information using information coded in file names"""

    def __init__(self):
        super(WaveylinesLookup, self).__init__()
        ovr_dir = os.path.join(os.path.dirname(__file__), 'wl_overrides')
        self.overrides = {}
        for ea in os.listdir(ovr_dir):
            with open(os.path.join(ovr_dir, ea), 'r') as f:
                name = ea[:-4]
                outline = ''
                for ea_c in f.readlines():
                    outline += ea_c.strip() + ':'
                outline = outline[:-1]
                self.overrides[name] = outline

        self.bsb_lookup = BsbLookup()

    def get_depth_units(self, map_path):
        if self._is_bsb(map_path):
            return self.bsb_lookup.get_depth_units(map_path)

        return 'Meters'
