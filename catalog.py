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


def get_reader_for_region(region):
    return CatalogReader(os.path.join(config.catalog_dir, region.upper() + '.csv'))


def build_catalog(region, list_of_map_paths, lookup):
    catalog_path = os.path.join(config.catalog_dir, region + '.csv')

    if os.path.isfile(catalog_path):
        os.remove(catalog_path)

    catalog = open(catalog_path, 'w')
    catalog.write('path\tname\tzoom\tscale\tdate\tdepths\toutline\n')

    rows = []

    for map_path in list_of_map_paths:
        row = [map_path,
               lookup.get_name(map_path),
               lookup.get_zoom(map_path),
               lookup.get_scale(map_path),
               lookup.get_updated(map_path),
               lookup.get_depth_units(map_path),
               lookup.get_outline(map_path)]
        rows.append(row)

    #sort row items by scale descending and write to catalog
    for i in sorted(rows, key=itemgetter(3), reverse=True):
        catalog.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (tuple(s for s in i)))


def build_catalog_for_region(region):
    build_catalog(region.upper(), regions.map_list_for_region(region), regions.lookup_for_region(region))

    #if __name__ == '__main__':
    #    build_catalog_by_region('noaa', 'region_15')
    #    cr = CatalogReader(os.path.join(config.catalog_dir, 'region_15.csv'))
    #    for entry in cr:
    #        for key in cr.keys():
    #            print key + ':' + entry[key]
    #        print '----------------------------------------------'