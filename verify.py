#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2014, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''This verifies tiles were created for every chart in a catalog
'''

import os.path

from PIL import Image

from . import catalog
from . import config


error_message = ''
IGNORED = {'.DS_Store'}


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
                print(img_path)
            else:
                return True

    return False


def verify_opt(catalog_name, base_dir=config.merged_tile_dir):
    un_opt_dir = os.path.join(base_dir, catalog_name)
    opt_dir = un_opt_dir + ".opt"
    un_opt_set = set()
    for path, dirs, files in os.walk(un_opt_dir):
        p = path.replace(un_opt_dir, '')
        for f in files:
            if not f.startswith('.'):
                un_opt_set.add(os.path.join(p, f))
    opt_set = set()
    for path, dirs, files in os.walk(opt_dir):
        p = path.replace(opt_dir, '')
        for f in files:
            if not f.startswith('.'):
                opt_set.add(os.path.join(p, f))

    i = len(un_opt_set)
    n = len(opt_set)
    print('un-opt dir count:{}'.format(i))
    print('opt dir count:{}'.format(n))
    missing = opt_set ^ un_opt_set
    print('number of missing charts: {} \n {}'.format(len(missing), missing))
    return i == n and i != 0


def verify_catalog(catalog_name):
    """
    :param catalog_name: region name
    :return: if all tiles have been created for every chart in the catalog
    """
    result = True
    global error_message

    # noinspection PyBroadException
    try:
        reader = catalog.get_reader_for_region(catalog_name)
    except:
        error_message = 'error reading catalog'
        return False

    region_tile_dir = os.path.join(config.unmerged_tile_dir, catalog_name)

    if not os.path.isdir(region_tile_dir):
        error_message += region_tile_dir + ' is not a directory\n'
        result = False

    tile_chart_dirs = set(os.listdir(region_tile_dir))

    for chart in reader:
        name = os.path.basename(chart['path'])
        name = name[:name.rfind('.')]
        if name not in tile_chart_dirs:
            error_message = name + ' not found in chart directories\n'
            result = False
        else:
            tile_dir = os.path.join(region_tile_dir, name)
            if not (verify_tile_dir(tile_dir)):
                result = False

    return result


def verify_tile_dir(tile_dir):
    if not os.path.isdir(tile_dir):
        return False

    found_zoom_dirs = []

    # look for a zoom directory
    for z_dir in os.listdir(tile_dir):
        if z_dir.isdigit():
            found_zoom_dirs.append(z_dir)

    global error_message

    # we should have at least one zoom dir
    if len(found_zoom_dirs) > 0:

        # check for tiles
        for z_dir in found_zoom_dirs:
            z_dir = os.path.join(tile_dir, z_dir)
            x_dirs = os.listdir(z_dir)

            # we should have at least one x dir
            if len(x_dirs) == 0:
                error_message += 'zero x directories found in path: ' + z_dir + '\n'
                return False

            # num_tiles = _x_dir_tile_count(os.listdir(os.path.join(z_dir, x_dirs[0])))
            # if num_tiles == 0:
            #     error_message = 'zero tiles in directory path: ' + os.path.join(z_dir, x_dirs[0])
            #     return False

            for x_dir in x_dirs:
                if x_dir in IGNORED:
                    continue
                x_dir = os.path.join(z_dir, x_dir)
                if not _x_dir_has_tiles(x_dir):
                    error_message += 'zero tiles in directory path: ' + os.path.join(z_dir, x_dir) + '\n'
                    return False

    else:
        error_message += 'zero zoom directories found for ' + tile_dir + '\n'
        return False

    return True


def verify(region_lst):
    for region in region_lst:
        region = region.upper()
        v = verify_catalog(region)
        print(region, 'verify:', v)
        if not v:
            print(error_message)
        v = verify_opt(region)
        print(region, 'verify opt:', v)
        if not v:
            print(error_message)
        print('------------------------------')


if __name__ == '__main__':
    # import regions
    # verify(regions._db.db['noaa'].keys())
    verify(['REGION_FAA'])