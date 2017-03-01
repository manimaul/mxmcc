#!/usr/bin/env python

import os
from operator import itemgetter
from search import MapPathSearch
import regions
import config
import lookups
import json
import shapely.geometry as geo
from chart_outline_geometry import ChartOutline, SVG_TEMPLATE

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''This builds a csv catalog of map information (sorted by scale) as follows:
   <path, name, zoom, scale, date, depths, outline>
   (csv values are tab separated)
'''


class CatalogMapItem(object):
    def __init__(self, items):
        self.__dict__ = items
        self._chart_outline = ChartOutline(self.outline)

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
        return self._chart_outline.geometry


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
    def geometry(self):
        geometries = []
        for each in self:
            item = CatalogMapItem(each)
            geometries.append(item.outline_geometry)
        return geo.GeometryCollection(geometries)

    def svg(self):
        envelope = self.geometry.envelope
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
