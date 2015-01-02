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

import regions
import catalog
import tilebuilder
import tilesmerge
import gemf
import zdata
import verify
import tiles_opt
from checkpoint import *


# import filler
import encryption_shim
import util as mb

PROFILE_MX_R = 'MX_REGION'  # (default) renders standard MX Mariner gemf + zdat
PROFILE_MB_C = 'MB_CHARTS'  # renders each chart as mbtiles file
PROFILE_MB_R = 'MB_REGION'  # renders entire region as mbtiles file


def compile_region(region, profile=PROFILE_MX_R):
    region = region.upper()
    profile = profile.upper()

    checkpoint_store = CheckPointStore()
    # ------------------------------------------------------------------------------------------------------------------

    # build catalog
    point = CheckPoint.CHECKPOINT_CATALOG
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print 'building catalog for:', region

        if not regions.is_valid_region(region):
            region_dir = regions.find_custom_region_path(region)
            if region_dir is not None:
                catalog.build_catalog_for_bsb_directory(region_dir, region)
            else:
                raise Exception('custom region: %s does not have a directory' % region)
        else:
            catalog.build_catalog_for_region(region)

        checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
    else:
        print 'skipping checkpoint', point
    # ------------------------------------------------------------------------------------------------------------------

    # create tiles
    point = CheckPoint.CHECKPOINT_TILE_VERIFY
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print 'building tiles for:', region
        tilebuilder.build_tiles_for_catalog(region)

        # verify
        if not verify.verify_catalog(region):
            raise Exception(region + ' was not verified... ' + verify.error_message)

        checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
    else:
        print 'skipping checkpoint', point
    # ------------------------------------------------------------------------------------------------------------------

    if 'REGION' in profile:
        # merge
        point = CheckPoint.CHECKPOINT_MERGE
        if checkpoint_store.get_checkpoint(region, profile) < point:
            print 'merging tiles for:', region
            tilesmerge.merge_catalog(region)
            checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
        else:
            print 'skipping checkpoint', point
        # --------------------------------------------------------------------------------------------------------------

        # fill
        # print 'filling tile \"holes\"', region
        # filler.fill_all_in_region(region)

        # optimize
        point = CheckPoint.CHECKPOINT_OPT
        if checkpoint_store.get_checkpoint(region, profile) < point:
            tiles_opt.optimize_dir(os.path.join(config.merged_tile_dir, region))

            # verify all optimized tiles are there
            if not verify.verify_opt(region):
                raise Exception(region + ' was not optimized fully')

            checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
        else:
            print 'skipping checkpoint', point
        # --------------------------------------------------------------------------------------------------------------

        if 'MX_' in profile:

            should_encrypt = regions.provider_for_region(region) is regions.provider_ukho
            if should_encrypt:
                print 'encrypting tiles for region:', region
                # encryption
                point = CheckPoint.CHECKPOINT_ENCRYPTED
                if checkpoint_store.get_checkpoint(region, profile) < point:
                    if not encryption_shim.encrypt_region(region):
                        raise Exception('encryption failed!')

                    checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
                else:
                    print 'skipping checkpoint', point
                name = region + '.enc'
            else:
                name = region + '.opt'

            # ----------------------------------------------------------------------------------------------------------

            # gemf
            point = CheckPoint.CHECKPOINT_ARCHIVE
            if checkpoint_store.get_checkpoint(region, profile) < point:
                print 'archiving gemf for region:', region
                gemf.generate_gemf(name, add_uid=should_encrypt)

                if should_encrypt:
                    encryption_shim.generate_token(region)

                checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
            else:
                print 'skipping checkpoint', point
            # ----------------------------------------------------------------------------------------------------------

            # zdat
            point = CheckPoint.CHECKPOINT_METADATA
            if checkpoint_store.get_checkpoint(region, profile) < point:
                print 'building zdat metadata archive for:', region
                zdata.generate_zdat_for_catalog(region)
                checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
            else:
                print 'skipping checkpoint', point
                # ----------------------------------------------------------------------------------------------------------

        if 'MB_' in profile:
            # mbtiles
            point = CheckPoint.CHECKPOINT_ARCHIVE
            if checkpoint_store.get_checkpoint(region, profile) < point:
                print 'archiving mbtiles for region:', region
                region_dir = os.path.join(config.merged_tile_dir, region + '.opt')
                mbtiles_file = os.path.join(config.compiled_dir, region + '.mbtiles')
                if os.path.isfile(mbtiles_file):
                    os.remove(mbtiles_file)
                mb.disk_to_mbtiles(region_dir, mbtiles_file, format='png', scheme='xyz')

                checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
            else:
                print 'skipping checkpoint', point
                # ----------------------------------------------------------------------------------------------------------

    elif 'CHARTS' in profile and 'MB_' in profile:
        # mbtiles
        point = CheckPoint.CHECKPOINT_ARCHIVE
        if checkpoint_store.get_checkpoint(region, profile) < point:
            region_charts_dir = os.path.join(config.unmerged_tile_dir, region)
            for chart in os.listdir(region_charts_dir):
                print 'archiving mbtiles for chart:', chart
                chart_dir = os.path.join(region_charts_dir, chart)
                mbtiles_file = os.path.join(config.compiled_dir, chart + '.mbtiles')
                if os.path.isfile(mbtiles_file):
                    os.remove(mbtiles_file)
                mb.disk_to_mbtiles(chart_dir, mbtiles_file, format='png', scheme='xyz')
            checkpoint_store.clear_checkpoint(checkpoint_store, region, profile, point)
        else:
            print 'skipping checkpoint', point
            # ----------------------------------------------------------------------------------------------------------


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