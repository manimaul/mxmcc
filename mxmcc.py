#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''This is the program that ties it all together to complete this programs
   task of compiling charts into the MX Mariner format.
'''

import sys

import config
import regions
import catalog


def compile_region(region):
    print 'building catalog for:', region
    catalog.build_catalog_for_region(region)

    reader = catalog.get_reader_for_region(region)
    print reader[0]

    #for map_entry in reader:
    #    pass  # TODO:

        #tile tif, bsb or png

        #merge


        #optimize

        #gemf

        #zdat


def print_usage():
    print 'usage:\n$python mxmcc.py <region>'


if __name__ == "__main__":
    if config.check_dirs():
        args = sys.argv
        if len(args) is not 2 or not regions.is_valid_region(args[1]):
            print_usage()
        else:
            compile_region(args[1])
    else:
        print 'Your mxmcc directory structure is not ready\n' + \
              'Please edit the top portion of config.py, run config.py,\n' + \
              'and place charts in their corresponding directories.'