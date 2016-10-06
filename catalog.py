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


class CatalogReader:
    def __init__(self, catalog_path):
        self._entries = []
        with open(catalog_path, 'r') as fp:
            self._entries = json.load(fp)

    @staticmethod
    def key_set():
        return {"path",
                "name",
                "min_zoom",
                "max_zoom",
                "scale",
                "date",
                "depths",
                "outline"}

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, index):
        return self._entries[index]


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

if __name__ == "__main__":
    build_catalog_for_region('REGION_FAA')
    reader = get_reader_for_region('REGION_FAA')
    for item in reader:
        for key in reader.key_set():
            print key, ':', item[key]