import os

from shapely.geometry import Polygon

from .search import MapPathSearch
from .region_constants import *
from . import config
from . import gdalds
from . import ukho_remove_duplicates


__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2014, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Creates (txt) manifests containing a list of charts for each region based on if they are in defined boundaries
'''

EXCLUDES = {REGION_UK1: {'4102-0.tif', '0245-0.tif', '1121-0.tif', '2724-0.tif', '0245-0.tif'},

            REGION_UK2: {'4102-0.tif', '1123-0.tif', '1179-0.tif', '1178-0.tif'},

            REGION_UK3: {'1123-0.tif'},

            REGION_UK4: {'2182A-0.tif', '2182B-0.tif', '1407-0.tif', '1125-0_UD.tif', '1127-0.tif', '2656-0.tif'}}

BOUNDARIES = {REGION_UK1: Polygon(((60.432475243, -6.312084094), (61.7815364, 0.77050051),
                                   (55.232640709, 3.514615661), (53.991841279, -1.970770244),
                                   (55.318427775, -2.913842661), (56.50474705, -4.761153867),
                                   (58.677242823, -4.989699171), (60.432475243, -6.312084094))),

              REGION_UK2: Polygon(((53.991841279, -1.970770244), (55.232640709, 3.514615661),
                                   (51.209816332, 4.979579361), (47.000448924, -4.086128932),
                                   (46.952325482, -8.282052045), (49.475693247, -7.168619247),
                                   (50.806726787, -3.806672546), (51.091490479, -2.355807505),
                                   (52.024815432, -0.61793567), (53.991841279, -1.970770244))),

              REGION_UK3: Polygon(((60.432475243, -6.312084094), (59.562319205, -15.742039595),
                                   (46.723720352, -15.580151947), (46.952325482, -8.282052045),
                                   (49.475693247, -7.168619247), (51.873368713, -8.840058188),
                                   (53.136809109, -7.567761152), (55.213543445, -7.277588144),
                                   (55.982797256, -7.210625142), (56.50474705, -4.761153867),
                                   (58.677242823, -4.989699171), (60.432475243, -6.312084094))),

              REGION_UK4: Polygon(((56.50474705, -4.761153867), (55.982797256, -7.210625142),
                                   (55.213543445, -7.277588144), (53.136809109, -7.567761152),
                                   (51.873368713, -8.840058188), (49.475693247, -7.168619247),
                                   (50.806726787, -3.801092295), (51.094995182, -2.350227255),
                                   (52.024815432, -0.61793567), (53.991841279, -1.970770244),
                                   (55.318427775, -2.913842661), (56.50474705, -4.761153867)))}


def should_include(region, map_name, poly):
    return not map_name.startswith('40') and map_name not in EXCLUDES[region] and BOUNDARIES[region].intersects(poly)


def populate_previous(bak):
    with open(bak, 'r') as manifest:
        return manifest.readlines()


def compare_previous(this_list, previous_list):
    tl = set(this_list)
    pl = set(previous_list)

    difference = list(tl.symmetric_difference(pl))
    difference.sort()
    print('difference:', len(difference))


def make_manifest():
    if ukho_remove_duplicates.has_duplicates():
        raise Exception('duplicate charts detected, run ukho_remove_duplicates first')

    matched = {REGION_UK1: [],
               REGION_UK2: [],
               REGION_UK3: [],
               REGION_UK4: []}

    num_matched = 0

    previous = {}

    mps = MapPathSearch(config.ukho_geotiff_dir, ['tif'])
    n = 1
    o = len(mps.file_paths)
    for abs_map_path in mps.file_paths:
        map_name = os.path.basename(abs_map_path)
        map_name = map_name[:map_name.rfind('.')]  # remove extension
        print('inspecting', map_name, 'for inclusion', '%s of %s' % (n, o))
        n += 1
        ds = gdalds.get_ro_dataset(abs_map_path)
        wnes, is_north_up = gdalds.dataset_lat_lng_bounds(ds)
        west, north, east, south = wnes
        poly = Polygon(((north, west), (north, east), (south, east), (south, west), (north, west)))

        for region in BOUNDARIES.keys():
            if should_include(region, map_name, poly):
                matched[region].append(map_name + '\n')
                num_matched += 1

    print('writing included - ', num_matched)
    for region in matched.keys():
        match_lst = matched[region]
        num = len(match_lst)
        if num > 0:
            print(region, num)
            manifest_path = os.path.join(config.ukho_meta_dir, region + '.txt')
            if os.path.exists(manifest_path):
                bak = manifest_path + '.bak'  # '%s_BAK.txt' % time.time()
                os.remove(bak)
                os.rename(manifest_path, bak)
                previous[region] = populate_previous(bak)
            with open(manifest_path, 'w+') as manifest:
                # todo: check crest burner to see if we write png to tif
                manifest.writelines(matched[region])

    print('skipped - ', o - num_matched)

    for region in previous.keys():
        print('comparing region:', region, 'with previous generated list')
        compare_previous(matched[region], previous[region])


if __name__ == "__main__":
    make_manifest()

