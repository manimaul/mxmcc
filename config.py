#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''This is the global configuration for mxmcc which consists of a
   directory structure where map and meta data files (should) live.
   Charts and meta data files** need to be placed in their corresponding
   directories. It is up to you to obtain the files from their providing
   hydro-graphic office.

   **With the exception of NOAA xml files which are fetched automatically
     as needed.
'''

import os
import time

######################################################################
# EDIT THIS SECTION ONLY##############################################
######################################################################

png_nq_binary = 'pngnq'
# png_nq_binary = 'C:\\pngnq\\pngnqi.exe'

# InputOutput directory
# _root_dir = os.path.join(os.getenv('HOME'), 'mxmcc')
_root_dir = os.path.join('/Volumes/USB_DATA', 'mxmcc')
# _root_dir = os.path.join('D:\\', 'mxmcc')
# _root_dir = os.path.join('/mnt/auxdrive', 'mxmcc')
# _root_dir = os.path.join('/media/william/USB-DATA', 'mxmcc')

# set to true when rendering a single zoom level and you want the following behavior:
# - render a (down zoom) layer first
# - then use anti-aliased image scale down for the final pass to render the target single zoom
use_single_zoom_over_zoom = False

# UKHO specific meta data excel sheets that change every quarter
ukho_quarterly_extract = 'Quarterly Extract of Metadata for Raster Charts July 2016.xls'
ukho_source_breakdown = 'Raster source information (Standard Version) Q3 2016.xls'
ukho_chart_data = 'Titles,Scales,Editions,Codes,Projection,Vertices,Shifts July 2016.xls'
ukho_chart_dpi = 127

######################################################################
# END EDITABLE SECTION################################################
######################################################################
# YOU DON'T NEED TO EDIT ANYTHING ELSE################################
######################################################################

# chart directories
map_dir = os.path.join(_root_dir, 'charts')
brazil_bsb_dir = os.path.join(map_dir, 'brazil')
linz_bsb_dir = os.path.join(map_dir, 'linz')
noaa_bsb_dir = os.path.join(map_dir, 'noaa')
faa_geotiff_dir = os.path.join(map_dir, 'faa')
ukho_geotiff_dir = os.path.join(map_dir, 'ukho/geotiff')
ukho_dup_dir = os.path.join(map_dir, 'ukho/duplicates')
ukho_png_dir = os.path.join(map_dir, 'ukho/png')
wavey_line_geotiff_dir = os.path.join(map_dir, 'wavey_lines/geotiff')

# finished directory
compiled_dir = os.path.join(_root_dir, 'compiled')

# tile directories
_tile_dir = os.path.join(_root_dir, 'tiles')
merged_tile_dir = os.path.join(_tile_dir, 'merged')
unmerged_tile_dir = os.path.join(_tile_dir, 'unmerged')

# meta data and catalogs
_meta_dir = os.path.join(_root_dir, 'metadata')
catalog_dir = os.path.join(_meta_dir, 'catalogs')
ukho_meta_dir = os.path.join(_meta_dir, 'ukho')
wl_meta_dir = os.path.join(_meta_dir, "wl")
noaa_meta_dir = os.path.join(_meta_dir, 'noaa')
brazil_meta_dir = os.path.join(_meta_dir, 'brazil')


# add corresponding absolute path to ukho meta data excel sheets
ukho_quarterly_extract = os.path.join(ukho_meta_dir, ukho_quarterly_extract)
ukho_source_breakdown = os.path.join(ukho_meta_dir, ukho_source_breakdown)
ukho_chart_data = os.path.join(ukho_meta_dir, ukho_chart_data)

# java encryption source in not publicly published (and not needed for most/unencrypted regions)
java_encryption_src = os.path.join(os.path.dirname(__file__), '../mx-mariner-encryption/src')

epoch = int(time.time())

_all_dirs = [_root_dir,
             map_dir,
             _meta_dir,
             ukho_meta_dir,
             wl_meta_dir,
             noaa_meta_dir,
             catalog_dir,
             _tile_dir,
             merged_tile_dir,
             unmerged_tile_dir,
             noaa_bsb_dir,
             linz_bsb_dir,
             brazil_bsb_dir,
             ukho_geotiff_dir,
             faa_geotiff_dir,
             ukho_dup_dir,
             ukho_png_dir,
             wavey_line_geotiff_dir,
             compiled_dir]


def check_dirs():
    for each in _all_dirs:
        if not os.path.isdir(each):
            return False
    return True


def setup_dir_structure():
    print 'Setting up MXMCC directory structure'
    if not os.path.isdir(_root_dir):
        os.makedirs(_root_dir)

    if not os.path.isdir(_root_dir):
        raise Exception(_root_dir + ' does not exist!')

    for each in _all_dirs:
        if not os.path.isdir(each):
            print 'creating directory: ' + each
            os.makedirs(each)

    print 'MXMCC directory structure is ready :)'

######################################################################

if __name__ == '__main__':
    setup_dir_structure()
