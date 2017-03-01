#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''This builds a csv catalog of map information (sorted by scale) as follows:
   <path, name, zoom, scale, date, depths, outline>
   (csv values are tab separated)
'''

import os
from operator import itemgetter

from search import MapPathSearch
import regions
import config
import lookups
import json
import shapely.geometry as geo

SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   version="1.1"
   id="svg2"
   viewBox="-180 -90 360 180">
  <defs
     id="defs4" />
  <metadata
     id="metadata7">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title></dc:title>
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     id="layer1">
    {}
  </g>
</svg>
"""

west = geo.Polygon(shell=geo.LinearRing([(-180, 90), (0, 90), (0, -90), (-180, -90), (-180, 90)]))
east = geo.Polygon(shell=geo.LinearRing([(180, 90), (0, 90), (0, -90), (180, -90), (180, 90)]))


class CatalogMapItem(object):
    def __init__(self, items):
        self.__dict__ = items

    @property
    def path(self):
        return self.__dict__['path']

    @property
    def name(self):
        return self.__dict__['name']

    @property
    def min_zoom(self):
        return self.__dict__['min_zoom']

    @property
    def max_zoom(self):
        return self.__dict__['max_zoom']

    @property
    def scale(self):
        return self.__dict__['scale']

    @property
    def date(self):
        return self.__dict__['date']

    @property
    def depths(self):
        return self.__dict__['depths']

    @property
    def outline(self):
        return self.__dict__['outline']

    @property
    def outline_geometry(self):
        coords = []
        for lat_lng_str in self.outline.split(':'):
            lat_str, lng_str = lat_lng_str.split(',')
            lng = float(lng_str)
            lat = float(lat_str)
            coords.append((lng, lat))

        ply = geo.Polygon(shell=geo.LinearRing(coords))
        w = ply.intersection(west)
        e = ply.intersection(east)
        if not w.is_empty and not e.is_empty:
            return geo.GeometryCollection([w, e])
        else:
            return ply


class CatalogReader:
    def __init__(self, catalog_path):
        self._entries = []
        with open(catalog_path, 'r') as fp:
            self._entries = json.load(fp)

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, index):
        return self._entries[index]

    def get_item(self, index):
        return CatalogMapItem(self._entries[index])

    @property
    def envelope_geometry(self):
        geometries = []
        for each in self:
            item = CatalogMapItem(each)
            geometries.append(item.outline_geometry)
        geometry = geo.GeometryCollection(geometries)
        return geometry.envelope

    def visualize(self):
        envelope = self.envelope_geometry
        paths = envelope.svg(scale_factor=.5)
        for each in self:
            item = CatalogMapItem(each)
            paths += item.outline_geometry.svg(scale_factor=.25) + '\n'
        return SVG_TEMPLATE.format(paths)


def get_reader_for_region(catalog_name):
    catalog_path = os.path.join(config.catalog_dir, catalog_name.upper() + '.json')
    if not os.path.isfile(catalog_path):
        raise Exception('catalog does not exist: %s' % catalog_path)

    return CatalogReader(catalog_path)


def build_catalog(region, list_of_map_paths, lookup):
    catalog_path = os.path.join(config.catalog_dir, region + '.json')

    if os.path.isfile(catalog_path):
        os.remove(catalog_path)

    catalog = open(catalog_path, 'w')
    rows = []
    for map_path in list_of_map_paths:
        if lookup.get_is_valid(map_path):
            row = {"path": map_path,
                   "name": lookup.get_name(map_path),
                   "min_zoom": lookup.get_min_zoom(map_path),
                   "max_zoom": lookup.get_max_zoom(map_path),
                   "scale": lookup.get_scale(map_path),
                   "date": lookup.get_updated(map_path),
                   "depths": lookup.get_depth_units(map_path),
                   "outline": lookup.get_outline(map_path)}
            rows.append(row)

    # sort row items by scale descending and write to catalog
    rows = sorted(rows, key=itemgetter("scale"), reverse=True)
    json.dump(rows, catalog, indent=2)


def build_catalog_for_region(region):
    build_catalog(region.upper(), regions.map_list_for_region(region), regions.lookup_for_region(region))


def build_catalog_for_bsb_directory(bsb_dir, name=None):
    map_search = MapPathSearch(bsb_dir, ['kap'])

    if name is None:
        name = os.path.basename(bsb_dir).lower()

    build_catalog(name.upper(), map_search.file_paths, lookups.BsbLookup())

# if __name__ == "__main__":
#     r = 'REGION_FAA_PLANNING'
#     build_catalog_for_region(r)
#     reader = get_reader_for_region(r)
#     for item in reader:
#         for key in reader.key_set():
#             print key, ':', item[key]
