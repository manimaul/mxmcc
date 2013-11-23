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

import bsb

#coordinates need to be longitude,latitude,altitude
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


class BsbLookup:
    """Lookup information using the bsb header"""
    def __init__(self):
        self.lookup_db = {}

    def _get(self, map_path):
        if not map_path in self.lookup_db:
            self.lookup_db[map_path] = bsb.BsbHeader(map_path)

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


class UKHOLookup:
    """Lookup information using the ukho excel meta data files"""
    def __init__(self):
        pass  # TODO:

    def get_name(self, map_path):
        pass

    def get_zoom(self, map_path):
        pass

    def get_scale(self, map_path):
        pass

    def get_updated(self, map_path):
        pass

    def get_depth_units(self, map_path):
        pass

    def get_outline(self, map_path):
        pass


class WaveylinesLookup:
    """Lookup information using information coded in file names"""
    def __init__(self):
        pass  # TODO:

    def get_name(self, map_path):
        pass

    def get_zoom(self, map_path):
        pass

    def get_scale(self, map_path):
        pass

    def get_updated(self, map_path):
        pass

    def get_depth_units(self, map_path):
        pass

    def get_outline(self, map_path):
        pass