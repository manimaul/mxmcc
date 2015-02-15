#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2015, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Creates dictionary containing a list of charts for each region based on if they are in defined boundaries
'''

import os
import json

from shapely.geometry import Polygon
from noaaxml import NoaaXmlReader
import config
import gdalds
from region_constants import *
from search import MapPathSearch

BOUNDARIES = {REGION_WL1: Polygon(((20.653346, -75.816650),
                                   (27.973699, -71.410607),
                                   (27.973699, -81.793212),
                                   (20.653346, -81.793212),
                                   (20.653346, -75.816650))),

              REGION_WL2: Polygon(((20.653346, -75.816661),
                                   (16.445521, -75.816661),
                                   (16.445521, -66.040652),
                                   (28.030423, -66.040652),
                                   (27.030423, -71.381531),
                                   (20.653346, -75.816661)))}

JSON_PATH = os.path.join(config.wl_meta_dir, 'region_files.json')


def _should_include(region, poly):
    return BOUNDARIES[region].intersects(poly)


def get_file_list_region_dictionary(n=True):
    if os.path.isfile(JSON_PATH):
        with open(JSON_PATH, 'r') as json_file:
            return json.loads(json_file.read())
    elif n:
        _make_file_list_region_dictionary()
        return get_file_list_region_dictionary(n=False)
    else:
        raise Exception('failed to get or create json manifest')


def _make_file_list_region_dictionary():
    reader = NoaaXmlReader('REGION_10')
    mps = MapPathSearch(config.noaa_bsb_dir, ['kap'], reader.get_map_files())

    matched = {REGION_WL1: [],
               REGION_WL2: mps.file_paths}

    num_matched = 0

    mps = MapPathSearch(config.wavey_line_geotiff_dir, ['tif'])
    n = 1
    o = len(mps.file_paths)
    for abs_map_path in mps.file_paths:
        map_name = os.path.basename(abs_map_path)
        map_name = map_name[:map_name.rfind('.')]  # remove extension
        print 'inspecting', map_name, 'for inclusion', '%s of %s' % (n, o)
        n += 1
        ds = gdalds.get_ro_dataset(abs_map_path)
        wnes, is_north_up = gdalds.dataset_lat_lng_bounds(ds)
        del ds
        west, north, east, south = wnes
        poly = Polygon(((north, west), (north, east), (south, east), (south, west), (north, west)))

        for region in BOUNDARIES.keys():
            if _should_include(region, poly):
                matched[region].append(abs_map_path)
                num_matched += 1

    print 'num_matched : ', num_matched
    print 'skipped : ', max(0, o - num_matched)

    with open(os.path.join(JSON_PATH), 'w') as f:
        json.dump(matched, f, indent=2)


if __name__ == '__main__':
    print get_file_list_region_dictionary()