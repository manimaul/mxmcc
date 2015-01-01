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
import os

import config
import regions
import catalog
import tilebuilder
import tilesmerge
import gemf
import zdata
import verify
import tiles_opt


# import filler
import encryption_shim
import util as mb

PROFILE_MX_R = 'MX_REGION'  # (default) renders standard MX Mariner gemf + zdat
PROFILE_MB_C = 'MB_CHARTS'  # renders each chart as mbtiles file
PROFILE_MB_R = 'MB_REGION'  # renders entire region as mbtiles file


def compile_region(region, profile=PROFILE_MX_R):
    region = region.upper()
    profile = profile.upper()

    print 'building catalog for:', region
    if not regions.is_valid_region(region):
        region_dir = regions.find_custom_region_path(region)
        if region_dir is not None:
            catalog.build_catalog_for_bsb_directory(region_dir, region)
        else:
            raise Exception('custom region: %s does not have a directory' % region)
    else:
        catalog.build_catalog_for_region(region)

    # create tiles
    print 'building tiles for:', region
    tilebuilder.build_tiles_for_catalog(region)

    # verify
    if not verify.verify_catalog(region):
        raise Exception(region + ' was not verified... ' + verify.error_message)

    if 'REGION' in profile:
        # merge
        print 'merging tiles for:', region
        tilesmerge.merge_catalog(region)

        # fill
        # print 'filling tile \"holes\"', region
        # filler.fill_all_in_region(region)

        # optimize
        tiles_opt.optimize_dir(os.path.join(config.merged_tile_dir, region))

        # verify all optimized tiles are there
        if not verify.verify_opt(region):
            raise Exception(region + ' was not optimized fully')

        if 'MX_' in profile:
            # gemf
            print 'archiving gemf for region:', region
            should_encrypt = regions.provider_for_region(region) is regions.provider_ukho
            if should_encrypt:
                if encryption_shim.encrypt_region(region):
                    name = region + '.enc'
                else:
                    raise Exception('encryption failed!')
            else:
                name = region + '.opt'
            gemf.generate_gemf(name, add_uid=should_encrypt)

            if should_encrypt:
                encryption_shim.generate_token(region)

            # zdat
            print 'building zdat metadata archive for:', region
            zdata.generate_zdat_for_catalog(region)

        if 'MB_' in profile:
            # mbtiles
            print 'archiving mbtiles for region:', region
            region_dir = os.path.join(config.merged_tile_dir, region + '.opt')
            mbtiles_file = os.path.join(config.compiled_dir, region + '.mbtiles')
            if os.path.isfile(mbtiles_file):
                os.remove(mbtiles_file)
            mb.disk_to_mbtiles(region_dir, mbtiles_file, format='png', scheme='xyz')

    elif 'CHARTS' in profile and 'MB_' in profile:
        region_charts_dir = os.path.join(config.unmerged_tile_dir, region)
        for chart in os.listdir(region_charts_dir):
            print 'archiving mbtiles for chart:', chart
            chart_dir = os.path.join(region_charts_dir, chart)
            mbtiles_file = os.path.join(config.compiled_dir, chart + '.mbtiles')
            if os.path.isfile(mbtiles_file):
                os.remove(mbtiles_file)
            mb.disk_to_mbtiles(chart_dir, mbtiles_file, format='png', scheme='xyz')


def print_usage():
    print 'usage:\n$python mxmcc.py <region> <optional profile>'


if __name__ == "__main__":
    if config.check_dirs():
        args = sys.argv
        if len(args) < 2:
            print_usage()
        else:
            rgn = args[1]
            if len(args) >= 3:
                prof = args[2]
            else:
                prof = PROFILE_MX_R
            compile_region(rgn, prof)
    else:
        print 'Your mxmcc directory structure is not ready\n' + \
              'Please edit the top portion of config.py, run config.py,\n' + \
              'and place charts in their corresponding directories.'