#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2014, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''This verifies tiles were created for every chart in a catalog
'''

import catalog
import os.path
import config
from PIL import Image

error_message = ''


def _full_transparency(img):
    """is image fully transparent"""
    rgba = img.split()
    if len(rgba) < 4:
        return False

    (r, g, b, a) = rgba
    (a_min, a_max) = a.getextrema()  # get min/max values for alpha channel
    return a_min == 0 and a_max == 0


def _x_dir_has_tiles(x_dir):
    """
    :param x_dir: zxy tile x directory
    :return: count of all the png tiles in the directory
    """

    dir_lst = os.listdir(x_dir)
    for d in dir_lst:
        ne = d.split('.')
        if len(ne) != 2:
            continue
        name, ext = ne
        if name.isdigit() and ext.lower() == 'png':
            img_path = os.path.join(x_dir, d)
            img = Image.open(img_path)
            if _full_transparency(img):
                print img_path
            else:
                return True

    return False


def verify_opt(catalog_name):
    merged_region_tile_dir = os.path.join(config.merged_tile_dir, catalog_name)
    opt_dir = merged_region_tile_dir + ".opt"
    i = 0
    for path, subdirs, files in os.walk(merged_region_tile_dir):
        for _ in files:
            i += 1
    n = 0
    for path, subdirs, files in os.walk(opt_dir):
        for _ in files:
            n += 1

    return i == n and i != 0


def verify_catalog(catalog_name):
    """
    :param catalog_name: region name
    :return: if all tiles have been created for every chart in the catalog
    """
    global error_message
    error_message = ''

    # noinspection PyBroadException
    try:
        reader = catalog.get_reader_for_region(catalog_name)
    except:
        return False

    region_tile_dir = os.path.join(config.unmerged_tile_dir, catalog_name)

    if not os.path.isdir(region_tile_dir):
        error_message = region_tile_dir + ' is not a directory'
        return False

    tile_chart_dirs = set(os.listdir(region_tile_dir))

    for chart in reader:
        name = os.path.basename(chart['path'])
        name = name[:name.rfind('.')]
        if name not in tile_chart_dirs:
            error_message = name + ' not found in chart directories'
            return False
        else:
            tile_dir = os.path.join(region_tile_dir, name)
            if not (verify_tile_dir(tile_dir)):
                return False

    return True


def verify_tile_dir(tile_dir):
    if not os.path.isdir(tile_dir):
        return False

    found_zoom_dirs = []

    #look for a zoom directory
    for z_dir in os.listdir(tile_dir):
        if z_dir.isdigit():
            found_zoom_dirs.append(z_dir)

    global error_message
    error_message = ''

    #we should have at least one zoom dir
    if len(found_zoom_dirs) > 0:

        #check for tiles
        for z_dir in found_zoom_dirs:
            z_dir = os.path.join(tile_dir, z_dir)
            x_dirs = os.listdir(z_dir)

            #we should have at least one x dir
            if len(x_dirs) == 0:
                error_message = 'zero x directories found in path: ' + z_dir
                return False

            # num_tiles = _x_dir_tile_count(os.listdir(os.path.join(z_dir, x_dirs[0])))
            # if num_tiles == 0:
            #     error_message = 'zero tiles in directory path: ' + os.path.join(z_dir, x_dirs[0])
            #     return False

            for x_dir in x_dirs:
                x_dir = os.path.join(z_dir, x_dir)
                if not _x_dir_has_tiles(x_dir):
                    error_message = 'zero tiles in directory path: ' + os.path.join(z_dir, x_dir)
                    return False

    else:
        error_message = 'zero zoom directories found for ' + tile_dir
        return False

    return True


def verify(region_lst):
    for region in region_lst:
        region = region.upper()
        v = verify_catalog(region)
        print region, 'verify:', v
        if not v:
            print error_message
        v = verify_opt(region)
        print region, 'verify opt:', v
        if not v:
            print error_message
        print '------------------------------'


# if __name__ == '__main__':
#     # import regions
#     # verify(regions._db.db['noaa'].keys())
#     verify(['REGION_03', 'REGION_30'])