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

error_message = ''


def _x_dir_tile_count(dir_lst):
    """
    :param dir_lst: directory list
    :return: count of all the png tiles in the directory
    """
    count = 0
    for d in dir_lst:
        ne = d.split('.')
        if len(ne) != 2:
            continue
        name, ext = ne
        if name.isdigit() and ext.lower() == 'png':
            count += 1

    return count


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

    return i == n


def verify_catalog(catalog_name):
    """
    :param catalog_name: region name
    :return: if all tiles have been created for every chart in the catalog
    """
    global error_message
    error_message = ''

    reader = catalog.get_reader_for_region(catalog_name)
    region_tile_dir = os.path.join(config.unmerged_tile_dir, catalog_name)
    tile_chart_dirs = set(os.listdir(region_tile_dir))

    for chart in reader:
        name = os.path.basename(chart['path'])
        name = name[:name.rfind('.')]
        if name not in tile_chart_dirs:
            error_message = name + ' not found in chart directories'
            return False
        else:
            tile_dir = os.path.join(region_tile_dir, name)
            found_zoom_dirs = []

            #look for a zoom directory
            for z_dir in os.listdir(tile_dir):
                if z_dir.isdigit():
                    found_zoom_dirs.append(z_dir)

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

                    num_tiles = _x_dir_tile_count(os.listdir(os.path.join(z_dir, x_dirs[0])))
                    if num_tiles == 0:
                        error_message = 'zero tiles in directory path: ' + os.path.join(z_dir, x_dirs[0])
                        return False

                    for x_dir in x_dirs:
                        x_dir = os.path.join(z_dir, x_dir)
                        check_num = _x_dir_tile_count(os.listdir(x_dir))
                        if check_num != num_tiles:
                            error_message = 'wrong number of tiles found in directory: ' + x_dir
                            return False

            else:
                return False

    return True

if __name__=='__main__':
    print verify_opt('region_08')