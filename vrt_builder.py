#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Builds a vrt with expanded rgba and cropped cut line for a given map and cutline'''

from osgeo import gdal


def build_vrt_for_map(map_path, cutline):
    dataset = gdal.Open(map_path, gdal.GA_ReadOnly)

    vrt_drv = gdal.GetDriverByName('VRT')
    vrt_drv.CreateCopy('test.vrt', dataset)

if __name__ == "__main__":
    map_path = '/mnt/auxdrive/mxmcc/charts/noaa/BSB_ROOT/18453/18453_1.KAP'
    build_vrt_for_map(map_path, None)