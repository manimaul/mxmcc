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
#EDIT THIS SECTION ONLY###############################################
######################################################################

#InputOutput directory
#_root_dir = os.path.join(os.getenv('HOME'), 'mxmcc')
_root_dir = os.path.join('/Volumes/USB-DATA/', 'mxmcc')

#UKHO specific meta data excel sheets that change every quarter
ukho_quarterly_extract = 'Quarterly Extract of Metadata for Raster Charts Sep 2013.xls'
ukho_source_breakdown = 'Source Breakdown for Raster Charts Q4 2013.xls'
ukho_chart_data = 'Titles,Scale,Edition,Codes,Projection,Vertices,Shifts,Sep 2013.xls'

######################################################################
#END EDITABLE SECTION#################################################
######################################################################
#YOU DON'T NEED TO EDIT ANYTHING ELSE#################################
######################################################################

#chart directories
_map_dir = os.path.join(_root_dir, 'charts')
brazil_bsb_dir = os.path.join(_map_dir, 'brazil')
linz_bsb_dir = os.path.join(_map_dir, 'linz')
noaa_bsb_dir = os.path.join(_map_dir, 'noaa')
ukho_geotiff_dir = os.path.join(_map_dir, 'ukho/geotiff')
ukho_png_dir = os.path.join(_map_dir, 'ukho/png')
wavey_line_geotiff_dir = os.path.join(_map_dir, 'wavey-lines/geotiff')

#finished directory
compiled_dir = os.path.join(_root_dir, 'compiled')

#tile directories
_tile_dir = os.path.join(_root_dir, 'tiles')
merged_tile_dir = os.path.join(_tile_dir, 'merged')
unmerged_tile_dir = os.path.join(_tile_dir, 'unmerged')

#meta data and catalogs
_meta_dir = os.path.join(_root_dir, 'metadata')
catalog_dir = os.path.join(_meta_dir, 'catalogs')
ukho_meta_dir = os.path.join(_meta_dir, 'ukho')
noaa_meta_dir = os.path.join(_meta_dir, 'noaa')


#add corresponding absolute path to ukho meta data excel sheets
ukho_quarterly_extract = os.path.join(ukho_meta_dir, ukho_quarterly_extract)
ukho_source_breakdown = os.path.join(ukho_meta_dir, ukho_source_breakdown)
ukho_quarterly_extract = os.path.join(ukho_meta_dir, ukho_quarterly_extract)

epoch = int(time.time())

_all_dirs = [_root_dir,
             _map_dir,
             _meta_dir,
             ukho_meta_dir,
             noaa_meta_dir,
             catalog_dir,
             tile_dir,
             merged_tile_dir,
             unmerged_tile_dir,
             noaa_bsb_dir,
             linz_bsb_dir,
             brazil_bsb_dir,
             ukho_geotiff_dir,
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

    for each in _all_dirs:
        if not os.path.isdir(each):
            print 'creating directory: ' + each
            os.makedirs(each)

    print 'MXMCC directory structure is ready :)'

######################################################################

if __name__ == '__main__':
    setup_dir_structure()