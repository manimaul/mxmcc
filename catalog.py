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
import csv
from operator import itemgetter

import regions
import config
import lookups


class CatalogReader:
    def __init__(self, catalog_path):
        self._entries = []
        with open(catalog_path, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t', quotechar='\"')
            self._entry_keys = reader.next()
            for row in reader:
                self._entries.append(dict(zip(self._entry_keys, row)))

    def keys(self):
        return self._entry_keys

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, index):
        return self._entries[index]


def get_reader_for_region(catalog_name):
    catalog_path = os.path.join(config.catalog_dir, catalog_name.upper() + '.csv')

    if not os.path.isfile(catalog_path):
        raise Exception('catalog does not exist: %s' % catalog_path)

    return CatalogReader(catalog_path)


def build_catalog(region, list_of_map_paths, lookup):
    catalog_path = os.path.join(config.catalog_dir, region + '.csv')

    if os.path.isfile(catalog_path):
        os.remove(catalog_path)

    catalog = open(catalog_path, 'w')
    catalog.write('path\tname\tzoom\tscale\tdate\tdepths\toutline\n')

    rows = []

    for map_path in list_of_map_paths:
        if lookup.get_is_valid(map_path):
            row = [map_path,
                   lookup.get_name(map_path),
                   lookup.get_zoom(map_path),
                   lookup.get_scale(map_path),
                   lookup.get_updated(map_path),
                   lookup.get_depth_units(map_path),
                   lookup.get_outline(map_path)]
            rows.append(row)

    # sort row items by scale descending and write to catalog
    for i in sorted(rows, key=itemgetter(3), reverse=True):
        catalog.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (tuple(s for s in i)))


def build_catalog_for_region(region):
    build_catalog(region.upper(), regions.map_list_for_region(region), regions.lookup_for_region(region))


def build_catalog_for_bsb_directory(bsb_dir, name=None):
    map_search = regions.MapPathSearch(bsb_dir, ['kap'])

    if name is None:
        name = os.path.basename(bsb_dir).lower()

    build_catalog(name.upper(), map_search.file_paths, lookups.BsbLookup())

if __name__ == '__main__':
    # map_path = '/Users/will/mxmcc/charts/noaa/BSB_ROOT'
    # build_catalog_for_bsb_directory(map_path, 'Test')

    build_catalog_for_region('region_uk1')

#     region = 'region_08'
#
#     print 'building catalog for:', region
#     if not regions.is_valid_region(region):
#         print 'custom region'
#         region_dir = regions.find_custom_region_path(region)
#         if region_dir is not None:
#             build_catalog_for_bsb_directory(region_dir, region)
#         else:
#             raise Exception('custom region: %s does not have a directory' % region)
#
#     else:
#         print 'known region'
#         build_catalog_for_region(region)