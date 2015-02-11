import os

from shapely.geometry import Polygon

import config
import gdalds
from region_constants import *
from search import MapPathSearch

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2015, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Creates dictionary containing a list of charts for each region based on if they are in defined boundaries
'''

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


def _should_include(region, poly):
    return BOUNDARIES[region].intersects(poly)


def make_file_list_region_dictionary():

    matched = {REGION_WL1: [],
               REGION_WL2: []}

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
                matched[region].append(abs_map_path + '\n')
                num_matched += 1

    print 'num_matched : ', num_matched
    print 'skipped : ', max(0, o - num_matched)

    return matched


if __name__ == '__main__':
    print make_file_list_region_dictionary()