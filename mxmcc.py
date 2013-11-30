#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''This is the wrapper program that ties it all together to complete this set of programs'
   task of compiling charts into the MX Mariner format.
'''

import sys

import config
import regions
import catalog
import tilebuilder
import tilesmerge
import gemf
import zdata
import os


def compile_region(region):
    print 'building catalog for:', region
    if not regions.is_valid_region(region):
        #look for a custom directory if this is not a known region
        found = False
        for root, dirs, files in os.walk(config.map_dir):
            if region in dirs:
                found = True
                catalog.build_catalog_for_bsb_directory(os.path.join(root, region), region)
                break

        if not found:
            print region, 'not found'
            return

    else:
        catalog.build_catalog_for_region(region)

    #create tiles (handle tif, bsb or png datasets)
    print 'building tiles for:', region
    tilebuilder.build_tiles_for_catalog(region)

    #merge
    print 'merging tiles for:', region
    tilesmerge.merge_catalog(region)

    #optimize
    #TODO:

    #gemf
    print 'archiving:', region
    gemf.generate_gemf(region, add_uid=regions.provider_for_region(region) is regions.provider_ukho)

    #zdat
    print 'building metadata archive for:', region
    zdata.generate_zdat_for_catalog(region)


def print_usage():
    print 'usage:\n$python mxmcc.py <region>'


if __name__ == "__main__":
    if config.check_dirs():
        args = sys.argv
        if len(args) is not 2:
            print_usage()
        else:
            compile_region(args[1])
    else:
        print 'Your mxmcc directory structure is not ready\n' + \
              'Please edit the top portion of config.py, run config.py,\n' + \
              'and place charts in their corresponding directories.'