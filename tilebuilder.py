#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Builds zxy map tiles for a single map or all the maps within a map catalog (catalog.py)

   1.) A (stack) gdal vrt files is created as follows:

        --warped (base_w.vrt)
          rescaled to tile system pixels
          EPSG:900913 (tile system) re-projection if needed
          cropped cut line if defined
          rotated to be north up

        --expanded rgba if needed (base_c.vrt)--

        --base (the source map)--

    2.) The peek of the (stack) is offset (into tile window) and tiles are then rendered

    3.) The files in the vrt stack are then disposed of

   depends on gdal (1.10+)
        gdal python package
        gdal command line utilities
'''

import subprocess
import os
import shlex
import multiprocessing
from functools import partial

from osgeo import gdal

import tilesystem
import gdalds
import catalog
import config
import verify

#http://www.gdal.org/formats_list.html
geotiff = 'Gtiff'
bsb = 'BSB'
png = 'PNG'
supported_formats = {geotiff, bsb, png}

#needed to set this to be able to process new 400dpi charts from NOAA
#http://www.charts.noaa.gov/RNCs_400/
os.environ['BSB_IGNORE_LINENUMBERS'] = 'TRUE'
gdal.AllRegister()
mem_driver = gdal.GetDriverByName('MEM')
png_driver = gdal.GetDriverByName('PNG')


def _cleanup_tmp_vrt_stack(vrt_stack, verbose=False):
    """convenience method for removing temporary vrt files created with _build_tmp_vrt_stack_for_map()
    """
    for i in range(1, len(vrt_stack), 1):
        os.remove(vrt_stack[i])
        if verbose:
            print 'deleting temp file:', vrt_stack[i]


def _stack_peek(vrt_stack):
    """the peek of a vrt stack
    """
    return vrt_stack[-1]


def _build_tile_vrt_for_map(map_path, zoom_level, cutline=None, verbose=False):
    """builds a stack of temporary vrt files for an input path to a map file
       the peek of the stack is the target file to use to create tiles
       after use the temporary files should be deleted using cleanup_tmp_vrt_stack(the_stack)
       returns stack of map paths

       note: stack always has input map_path at the base, then expanded rgba vrt if necessary
             and tile-ready vrt result at the peek
    """
    map_stack = [map_path]

    dataset = gdal.Open(map_path, gdal.GA_ReadOnly)

    if dataset is None:
        raise Exception('could not open map file: ' + map_path)

    map_type = dataset.GetDriver().ShortName

    if not map_type in supported_formats:
        raise Exception(map_type + ' is not a supported format')

    #log = open(os.devnull, 'w')
    if verbose:
        log = subprocess.PIPE
    else:
        log = open(os.devnull, 'w')

    #-----paths and file names
    base_dir = os.path.dirname(map_path)
    map_fname = os.path.basename(map_path)
    map_name = map_fname[0:map_fname.find('.')]  # remove file extension

    #-----if map has a palette create vrt with expanded rgba
    if gdalds.dataset_has_color_palette(dataset):
        c_vrt_path = os.path.join(base_dir, map_name + '_c.vrt')
        if os.path.isfile(c_vrt_path):
            os.remove(c_vrt_path)

        command = "gdal_translate -of vrt -expand rgba %s %s" % (map_path, c_vrt_path)
        subprocess.Popen(shlex.split(command), stdout=log).wait()

        del dataset
        dataset = gdal.Open(c_vrt_path, gdal.GA_ReadOnly)

        map_stack.append(c_vrt_path)

    #-----repoject map to tilesystem projection, scale map to enveloping tiles window, crop to cutline
    w_vrt_path = os.path.join(base_dir, map_name + '_w.vrt')
    if os.path.isfile(w_vrt_path):
        os.remove(w_vrt_path)

    lat_lng_bounds = gdalds.dataset_lat_lng_bounds(dataset)
    zoom = int(zoom_level)
    pixel_min_x, pixel_max_y, pixel_max_x, pixel_min_y, res_x, res_y = \
        tilesystem.lat_lng_bounds_to_pixel_bounds_res(lat_lng_bounds, zoom)
    # tile_min_x, tile_max_y, tile_max_x, tile_min_y, num_tiles_x, num_tiles_y = \
    #     tilesystem.lat_lng_bounds_to_tile_bounds_count(lat_lng_bounds, zoom)
    #
    # offset_west = pixel_min_x % tilesystem.tile_size
    # offset_north = pixel_min_y % tilesystem.tile_size

    # print 'min_lng, max_lat, max_lng, min_lat', lat_lng_bounds
    # print 'min tile x:%d' % tile_min_x
    # print 'max tile x:%d' % tile_max_x
    # print 'min tile y:%d' % tile_min_y
    # print 'max tile y:%d' % tile_max_y
    #
    # print 'resolution x x:%d' % res_x
    # print 'resolution y:%d' % res_y
    # print 'num tiles x:%d' % num_tiles_x
    # print 'num tiles y:%d' % num_tiles_y
    #
    # print 'pixel min x:%d' % pixel_min_x
    # print 'pixel max x:%d' % pixel_max_x
    # print 'pixel min y:%d' % pixel_min_y
    # print 'pixel max y:%d' % pixel_max_y
    # print 'offset_west:%d' % offset_west
    # print 'offset_north:%d' % offset_north

    # todo: average resampling fails on some linux builds (non - north up charts)... result is fully transparent
    resampling = 'bilinear'  # near bilinear cubic cubicspline lanczos average mode

    #command = 'gdalwarp -of vrt -r %s -t_srs EPSG:900913' % resampling
    epsg_900913 = gdalds.dataset_get_as_epsg_900913(dataset)  # offset for crossing dateline
    command = ['gdalwarp', '-of', 'vrt', '-r', '%s' % resampling, '-t_srs', epsg_900913]

    if cutline is not None:
        cut_poly = gdalds.dataset_get_cutline_geometry(dataset, cutline)
        command += ['-wo', 'CUTLINE=%s' % cut_poly]
                    #'-te'] + extents # crop to cutline

    command += ['-ts', str(res_x), str(res_y),  # scale to tile pixel window
                _stack_peek(map_stack),  # gdal input source
                w_vrt_path]  # gdal output destination

    subprocess.Popen(command).wait()
    map_stack.append(w_vrt_path)

    return map_stack


def _render_tmp_vrt_stack_for_map(map_stack, zoom_level, out_dir):
    """renders a stack of vrts built with _build_tmp_vrt_stack_for_map()
       into tiles for specified zoom level
       rendered tiles placed in out_dir directory
       if out_dir is None or not a directory, tiles placed in map_stack, map directory
    """

    #---- render tiles in the same directory of the map if not specified
    if out_dir is None:
        out_dir = os.path.dirname(_stack_peek(map_stack))
        out_dir = os.path.join(out_dir, 'tiles')
    elif not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    elif verify.verify_tile_dir(out_dir):
        # print 'skipping: ' + out_dir
        return


    #---- open the peek vrt / map in the map_stack
    ds = gdal.Open(_stack_peek(map_stack), gdal.GA_ReadOnly)
    bands = ds.RasterCount

    lat_lng_bounds = gdalds.dataset_lat_lng_bounds(ds)
    zoom = int(zoom_level)

    pixel_min_x, pixel_max_y, pixel_max_x, pixel_min_y, res_x, res_y = \
        tilesystem.lat_lng_bounds_to_pixel_bounds_res(lat_lng_bounds, zoom)

    tile_min_x, tile_max_y, tile_max_x, tile_min_y, num_tiles_x, num_tiles_y = \
        tilesystem.lat_lng_bounds_to_tile_bounds_count(lat_lng_bounds, zoom)

    if pixel_max_x < pixel_min_x:  # dateline
        offset_west = pixel_max_x % tilesystem.tile_size
    else:  # standard
        offset_west = pixel_min_x % tilesystem.tile_size

    offset_north = pixel_min_y % tilesystem.tile_size

    # print 'min_lng, max_lat, max_lng, min_lat', lat_lng_bounds
    # print 'min tile x:%d' % tile_min_x
    # print 'max tile x:%d' % tile_max_x
    # print 'min tile y:%d' % tile_min_y
    # print 'max tile y:%d' % tile_max_y
    # print 'resolution x x:%d' % res_x
    # print 'resolution y:%d' % res_y
    # print 'num tiles x:%d' % num_tiles_x
    # print 'num tiles y:%d' % num_tiles_y
    # print 'offset_west:%d' % offset_west
    # print 'offset_north:%d' % offset_north

    # mem_driver = gdal.GetDriverByName('MEM')
    # png_driver = gdal.GetDriverByName('PNG')

    ##NOTE: This step skipped by re-scaling re-projected vrt in the map stack
    #print 'scaling map dataset to destination resolution for projection'
    ##in memory dataset scaled to destination resolution (num_pixels_x X num_pixels_y)
    #tmp = mem_driver.Create('', num_pixels_x, num_pixels_y, bands=bands)
    #for i in range(1, bands+1):
    #    gdal.RegenerateOverview(ds.GetRasterBand(i), tmp.GetRasterBand(i), 'average')
    #
    ##png_driver.CreateCopy('/Users/williamkamp/mxmcc/charts/noaa/BSB_ROOT/18453/rgo.png', tmp, strict=0)
    ##return
    #
    #del ds

    print 'offsetting map dataset to destination tile set window'
    #in memory dataset offset in tiled window
    tmp_offset = mem_driver.Create('', (num_tiles_x * tilesystem.tile_size) + 1,
                                   (num_tiles_y * tilesystem.tile_size) + 1, bands=bands)
    data = ds.ReadRaster(0, 0, ds.RasterXSize, ds.RasterYSize, ds.RasterXSize, ds.RasterYSize)
    tmp_offset.WriteRaster(offset_west, offset_north, ds.RasterXSize, ds.RasterYSize, data, band_list=range(1, bands+1))

    del ds
    del data

    print 'producing map tiles'

    if tile_min_x > tile_max_x:  # dateline wrap
        print 'wrapping tiles to dateline'
        cursor_pixel_x = _cut_tiles_in_range(tmp_offset, bands, tile_min_x, tilesystem.map_size_tiles(zoom),
                                             tile_min_y, tile_max_y, out_dir, zoom)
        _cut_tiles_in_range(tmp_offset, bands, 0, tile_max_x, tile_min_y, tile_max_y, out_dir, zoom, cursor_pixel_x)
    else:  # standard
        _cut_tiles_in_range(tmp_offset, bands, tile_min_x, tile_max_x, tile_min_y, tile_max_y, out_dir, zoom)

    del tmp_offset


def _cut_tiles_in_range(dataset, bands, tile_min_x, tile_max_x, tile_min_y, tile_max_y, out_dir, zoom, start_pixel=0):
    cursor_pixel_x = start_pixel
    cursor_pixel_y = 0

    for x in range(tile_min_x, tile_max_x + 1, 1):

        tile_dir = os.path.join(out_dir, str(zoom), str(x))

        for y in range(tile_min_y, tile_max_y+1, 1):
            tile_path = os.path.join(tile_dir, str(y) + '.png')
            data = dataset.ReadRaster(cursor_pixel_x, cursor_pixel_y, tilesystem.tile_size,
                                      tilesystem.tile_size, tilesystem.tile_size, tilesystem.tile_size)
            transparent = True
            if data is not None:
                for ea in data:
                    if ord(ea) != 0:
                        transparent = False

            #only create tiles that have data (not completely transparent)
            if not transparent:
                if not os.path.isdir(tile_dir):
                    os.makedirs(tile_dir)
                tile_mem = mem_driver.Create('', tilesystem.tile_size, tilesystem.tile_size, bands=bands)
                tile_mem.WriteRaster(0, 0, tilesystem.tile_size, tilesystem.tile_size, data, band_list=range(1, bands+1))
                #TODO: process png image data with http://pngquant.org/lib/ before saving to disk
                png_tile = png_driver.CreateCopy(tile_path, tile_mem, strict=0)

                del data
                del tile_mem
                del png_tile

            cursor_pixel_y += tilesystem.tile_size

        cursor_pixel_x += tilesystem.tile_size
        cursor_pixel_y = 0

    return cursor_pixel_x - tilesystem.tile_size


def build_tiles_for_map(map_path, zoom_level, cutline=None, out_dir=None):
    """builds tiles for a map_path - path to map to render tiles for
       zoom_level - int or string representing int of the single zoom level to render
       cutline - string defining the map border cutout... this can be None if the whole
       map should be rendered.
       out_dir - path to where tiles will be rendered to, if set to None then
       tiles will be rendered int map_path's base directory

       cutline string format example: 48.3,-123.2:48.5,-123.2:48.5,-122.7:48.3,-122.7:48.3,-123.2
       : dilineated latitude/longitude WGS-84 coordinates (in decimal degrees)
    """
    map_stack = _build_tile_vrt_for_map(map_path, zoom_level, cutline)
    _render_tmp_vrt_stack_for_map(map_stack, zoom_level, out_dir)
    _cleanup_tmp_vrt_stack(map_stack)


def _build_tiles_for_map_helper(entry, name):
    """helper method for multiprocessing pool map_async
    """
    map_name = os.path.basename(entry['path'])
    out_dir = os.path.join(config.unmerged_tile_dir, name, map_name[0:map_name.find('.')])
    build_tiles_for_map(entry['path'], entry['zoom'], entry['outline'], out_dir)


def build_tiles_for_catalog(catalog_name):
    """builds tiles for every map in a catalog
       tiles output to tile directory in config.py
    """
    catalog_name = catalog_name.upper()

    reader = catalog.get_reader_for_region(catalog_name)
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    pool.map_async(partial(_build_tiles_for_map_helper, name=catalog_name), reader)
    pool.close()
    pool.join()  # wait for pool to empty

if __name__ == '__main__':
    import bsb
    test_map = '/mnt/auxdrive/mxmcc/charts/noaa/BSB_ROOT/12348/12348_1.KAP'
    test_bsb = bsb.BsbHeader(test_map)
    build_tiles_for_map(test_map, test_bsb.get_zoom(), cutline=test_bsb.get_outline(), out_dir='/mnt/auxdrive/mxmcc/tiles/unmerged/REGION_03/12348_1')
