#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''This is the wrapper program that ties it all together to complete this set of programs'
   task of compiling charts into the MX Mariner format.
'''

from . import regions
from . import catalog
from . import tilebuilder
from . import tilesmerge
from . import gemf
from . import zdata
from . import verify
from . import tiles_opt
from .checkpoint import *
from . import encryption_shim
import os
import mbutil as mb
import re

import shutil

PROFILE_MX_R = 'MX_REGION'  # (default) renders standard MX Mariner gemf + zdat
PROFILE_MB_C = 'MB_CHARTS'  # renders each chart as mbtiles file
PROFILE_MB_R = 'MB_REGION'  # renders entire region as mbtiles file


def _build_catalog(checkpoint_store, profile, region):
    # build catalog
    point = CheckPoint.CHECKPOINT_CATALOG
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print('building catalog for:', region)

        if not regions.is_valid_region(region):
            region_dir = regions.find_custom_region_path(region)
            if region_dir is not None:
                catalog.build_catalog_for_bsb_directory(region_dir, region)
            else:
                raise Exception('custom region: %s does not have a directory' % region)
        else:
            catalog.build_catalog_for_region(region)

        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _create_tiles(checkpoint_store, profile, region):
    # create tiles
    point = CheckPoint.CHECKPOINT_TILE_VERIFY
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print('building tiles for:', region)
        tilebuilder.build_tiles_for_catalog(region)

        # verify
        if not verify.verify_catalog(region):
            raise Exception(region + ' was not verified... ' + verify.error_message)

        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _merge_tiles(checkpoint_store, profile, region):
    # merge
    point = CheckPoint.CHECKPOINT_MERGE
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print('merging tiles for:', region)
        tilesmerge.merge_catalog(region)
        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _optimize_tiles(checkpoint_store, profile, region, base_dir=config.merged_tile_dir):
    # optimize
    point = CheckPoint.CHECKPOINT_OPT
    if checkpoint_store.get_checkpoint(region, profile) < point:
        # if platform.system() == 'Windows':
        #   tiles_opt.set_nothreads()
        tiles_opt.optimize_dir(os.path.join(base_dir, region))

        # verify all optimized tiles are there
        if not verify.verify_opt(region, base_dir=base_dir):
            raise Exception(region + ' was not optimized fully')

        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _should_encrypt(region):
    encrypted_providers = {regions.provider_wavey_lines, regions.provider_ukho}
    return regions.provider_for_region(region) in encrypted_providers


def _encrypt_region(checkpoint_store, profile, region):
    print('encrypting tiles for region:', region)
    # encryption
    point = CheckPoint.CHECKPOINT_ENCRYPTED
    if checkpoint_store.get_checkpoint(region, profile) < point:
        if not encryption_shim.encrypt_region(region):
            raise Exception('encryption failed!')

        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _create_gemf(checkpoint_store, profile, region):
    point = CheckPoint.CHECKPOINT_ARCHIVE
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print('archiving gemf for region:', region)
        should_encrypt = _should_encrypt(region)
        if should_encrypt:
            name = region + '.enc'
        else:
            name = region + '.opt'
        gemf.generate_gemf(name, add_uid=should_encrypt)
        if should_encrypt:
            encryption_shim.generate_token(region)
        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _create_zdat(checkpoint_store, profile, region):
    point = CheckPoint.CHECKPOINT_METADATA
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print('building zdat metadata archive for:', region)
        zdata.generate_zdat_for_catalog(region)
        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _fill_tiles(region):
    # fill
    # print('filling tile \"holes\"', region)
    # filler.fill_all_in_region(region)
    print(region, 'fill skipped')


def _create_region_mb_tiles(checkpoint_store, profile, region):
    point = CheckPoint.CHECKPOINT_ARCHIVE
    if checkpoint_store.get_checkpoint(region, profile) < point:
        print('archiving mbtiles for region:', region)
        region_dir = os.path.join(config.merged_tile_dir, region + '.opt')
        mbtiles_file = os.path.join(config.compiled_dir, region + '.mbtiles')
        if os.path.isfile(mbtiles_file):
            os.remove(mbtiles_file)
        mb.disk_to_mbtiles(region_dir, mbtiles_file, format='png', scheme='xyz')

        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def __create_chart_mb_tiles(region):
    region_charts_dir = os.path.join(config.unmerged_tile_dir, region + '.opt')
    for chart in os.listdir(region_charts_dir):
        print('archiving mbtiles for chart:', chart)
        chart_dir = os.path.join(region_charts_dir, chart)
        prefix = re.sub(r'\W+', '_', chart).lower()
        mbtiles_file = os.path.join(config.compiled_dir, prefix + '.mbtiles')
        if os.path.isfile(mbtiles_file):
            os.remove(mbtiles_file)
        mb.disk_to_mbtiles(chart_dir, mbtiles_file, format='png', scheme='xyz')


def _create_chart_mb_tiles(checkpoint_store, profile, region):
    point = CheckPoint.CHECKPOINT_ARCHIVE
    if checkpoint_store.get_checkpoint(region, profile) < point:
        __create_chart_mb_tiles(region)
        checkpoint_store.clear_checkpoint(region, profile, point)
    else:
        print('skipping checkpoint', point)


def _skip_zoom(region):
    tile_path = os.path.join(config.unmerged_tile_dir, region)
    for chart in os.listdir(tile_path):
        zs = []
        for z_dir in os.listdir(os.path.join(tile_path, chart)):
            try:
                z = int(z_dir)
                zs.append(z)
            except ValueError:
                pass
        zs.sort(reverse=True)
        if len(zs) > 1 and (zs[0] - zs[1]) == 1:
            i = 0
            for z in zs:
                if i % 2:
                    p = os.path.join(tile_path, chart, str(z))
                    shutil.rmtree(p)
                i += 1


def compile_region(region, profile=PROFILE_MX_R, perform_clean=True):
    region = region.upper()
    profile = profile.upper()

    checkpoint_store = CheckPointStore()

    _build_catalog(checkpoint_store, profile, region)

    _create_tiles(checkpoint_store, profile, region)

    if 'REGION' in profile:
        _merge_tiles(checkpoint_store, profile, region)
        _fill_tiles(region)
        _optimize_tiles(checkpoint_store, profile, region)

        if 'MX_' in profile:
            should_encrypt = _should_encrypt(region)
            if should_encrypt:
                _encrypt_region(checkpoint_store, profile, region)
            _create_gemf(checkpoint_store, profile, region)
            _create_zdat(checkpoint_store, profile, region)

        if 'MB_' in profile:
            _create_region_mb_tiles(checkpoint_store, profile, region)

    elif 'CHARTS' in profile and 'MB_' in profile:
        _skip_zoom(region)
        _optimize_tiles(checkpoint_store, profile, region, base_dir=config.unmerged_tile_dir)
        _create_chart_mb_tiles(checkpoint_store, profile, region)

    print('final checkpoint', checkpoint_store.get_checkpoint(region, profile))
    if perform_clean and checkpoint_store.get_checkpoint(region, profile) > CheckPoint.CHECKPOINT_ENCRYPTED:
        cleanup(region, config.unmerged_tile_dir)
        cleanup(region, config.merged_tile_dir)


def cleanup(region, base_dir):
    for ea in os.listdir(base_dir):
        if region in ea:
            abs_path = os.path.join(base_dir, ea)
            print('clean', abs_path)
            for root, dirs, files in os.walk(abs_path, topdown=False):
                for name in files:
                    p = os.path.join(root, name)
                    try:
                        os.remove(p)
                    except:
                        print('failed to delete', p)
                for name in dirs:
                    os.rmdir(os.path.join(root, name))


def print_usage():
    print('usage:\n$python mxmcc.py <region> <optional profile>')


if __name__ == "__main__":
    import sys

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
        print('Your mxmcc directory structure is not ready\n' +
              'Please edit the top portion of config.py, run config.py,\n' +
              'and place charts in their corresponding directories.')
