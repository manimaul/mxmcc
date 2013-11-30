#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Builds zxy map tiles for a single map or all the maps within a map catalog (catalog.py)

   1.) A (stack) gdal vrt files is created as follows:
        --rescale to tilesystem pixels--
        --EPSG:900913 (tilesystem) re-projection if needed--
        --cropped cut line if defined--
        --expanded rgba if needed--

    2.) The peek of the (stack) is offset (into tile window) and tiles are then rendered

    3.) The files in the vrt stack are then disposed of

   depends on gdal (1.10+)
        gdal python package
        gdal command line utilities
'''

from osgeo import gdal
import osr
import subprocess
import os
import shlex
import lookups
import tilesystem
import gdalds
import catalog
import config
import multiprocessing
from functools import partial

#http://www.gdal.org/formats_list.html
geotiff = 'Gtiff'
bsb = 'BSB'
png = 'PNG'
supported_formats = {geotiff, bsb, png}

#needed to set this to be able to process new 400dpi charts from NOAA
#http://www.charts.noaa.gov/RNCs_400/
os.environ['BSB_IGNORE_LINENUMBERS'] = 'TRUE'

#running = multiprocessing.Value("i", 0)


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


def _build_tmp_vrt_stack_for_map(map_path, zoom_level, cutline=None):
    """builds a stack of temporary vrt files for an input path to a map file
       the peek of the stack is the target file to use to create tiles
       after use the temporary files should be deleted using cleanup_tmp_vrt_stack(the_stack)
       also calculates min max tile pixels to render for final vrt
       return (stack of vrt paths, (minx, miny, maxx, maxy))
    """
    dataset = gdal.Open(map_path, gdal.GA_ReadOnly)

    map_stack = [map_path]

    if dataset is None:
        raise Exception('could not open map file: ' + map_path)

    map_type = dataset.GetDriver().ShortName

    if not map_type in supported_formats:
        raise Exception(map_type + ' is not a supported format')

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

        command = "gdal_translate -of vrt -expand rgba %s %s" % (_stack_peek(map_stack), c_vrt_path)
        subprocess.Popen(shlex.split(command), stdout=log).wait()

        map_stack.append(c_vrt_path)

    #-----create a cutline
    if cutline is not None:
        #----create kml with cutline polygon
        kml_path = os.path.join(base_dir, map_name + '_cutline.kml')
        kml_file = open(kml_path, 'w')
        kml_file.write(lookups.get_cutline_kml(cutline))
        kml_file.close()

        #-----create vrt of dataset using cutline
        vrt_path = os.path.join(base_dir, map_name + '.vrt')

        if os.path.isfile(vrt_path):
            os.remove(vrt_path)

        #if map_type is png:
        #    command = "gdalwarp -of vrt -cutline %s -crop_to_cutline -overwrite %s %s" \
        #              % (kml_path, _stack_peek(map_stack), vrt_path)
        #else:
        #    command = "gdalwarp -of vrt -cutline %s -crop_to_cutline -overwrite -dstnodata 0 -dstalpha %s %s" \
        #              % (kml_path, _stack_peek(map_stack), vrt_path)

        command = "gdalwarp -of vrt -r average -cutline %s -crop_to_cutline -overwrite %s %s" \
                  % (kml_path, _stack_peek(map_stack), vrt_path)

        subprocess.Popen(shlex.split(command), stdout=log).wait()

        os.remove(kml_path)  # we are done with the kml and can delete it now
        map_stack.append(vrt_path)

    #-----rescale map to tile system pixels
    dataset = gdal.Open(_stack_peek(map_stack), gdal.GA_ReadOnly)
    min_lng, min_lat, max_lng, max_lat = gdalds.dataset_lat_lng_bounds(dataset)
    pixel_min_x, pixel_max_y = tilesystem.lat_lng_to_pixel_xy(min_lat, min_lng, int(zoom_level))
    pixel_max_x, pixel_min_y = tilesystem.lat_lng_to_pixel_xy(max_lat, max_lng, int(zoom_level))
    num_pixels_x = pixel_max_x - pixel_min_x + 1
    num_pixels_y = pixel_max_y - pixel_min_y + 1

    #we can safely scale map to the intended resolution
    if dataset.RasterXSize is not num_pixels_x or dataset.RasterYSize is not num_pixels_y:
        s_vrt_path = os.path.join(base_dir, map_name + '_s.vrt')
        if os.path.isfile(s_vrt_path):
            os.remove(s_vrt_path)
        command = 'gdal_translate -of vrt -outsize %d %d %s %s' % (num_pixels_x, num_pixels_y, _stack_peek(map_stack), s_vrt_path)
        subprocess.Popen(shlex.split(command), stdout=log).wait()

        map_stack.append(s_vrt_path)

    del dataset

    #-----if map projection is not EPSG:900913, create re-projected vrt
    vrt_ds = gdal.Open(_stack_peek(map_stack), gdal.GA_ReadOnly)

    in_srs = osr.SpatialReference()
    in_srs_wkt = vrt_ds.GetGCPProjection()
    in_srs.ImportFromWkt(in_srs_wkt)

    out_srs = osr.SpatialReference()
    out_srs.ImportFromEPSG(900913)

    if in_srs.ExportToProj4() is not out_srs.ExportToProj4():
        w_vrt_path = os.path.join(base_dir, map_name + '_w.vrt')
        if os.path.isfile(w_vrt_path):
            os.remove(w_vrt_path)
        out_projection = out_srs.ExportToWkt()
        gdal.AutoCreateWarpedVRT(vrt_ds, vrt_ds.GetGCPProjection(), out_projection)
        vrt_ds.GetDriver().CreateCopy(w_vrt_path, vrt_ds)

        map_stack.append(w_vrt_path)

    return map_stack


def _render_tmp_vrt_stack_for_map(map_stack, zoom_level, out_dir):
    """renders a stack of vrts built with _build_tmp_vrt_stack_for_map()
       into tiles for specified zoom level
       rendered tiles placed in out_dir directory
       if out_dir is None or not a directory, tiles placed in map_stack, map directory
    """

    gdal.AllRegister()

    #---- render tiles in the same directory of the map if not specified
    if out_dir is None:
        out_dir = os.path.dirname(_stack_peek(map_stack))
        out_dir = os.path.join(out_dir, 'tiles')
    elif not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    #---- open the peek vrt / map in the map_stack
    ds = gdal.Open(_stack_peek(map_stack), gdal.GA_ReadOnly)
    bands = ds.RasterCount

    min_lng, min_lat, max_lng, max_lat = gdalds.dataset_lat_lng_bounds(ds)

    mem_driver = gdal.GetDriverByName('MEM')
    png_driver = gdal.GetDriverByName('PNG')

    #this seems counter intuitive... tile and pixel 0,0 is top left where as lat long 0,0 is bottom left
    zoom = int(zoom_level)
    pixel_min_x, pixel_max_y = tilesystem.lat_lng_to_pixel_xy(min_lat, min_lng, zoom)
    tile_min_x, tile_max_y = tilesystem.lat_lng_to_tile_xy(min_lat, min_lng, zoom)

    pixel_max_x, pixel_min_y = tilesystem.lat_lng_to_pixel_xy(max_lat, max_lng, zoom)
    tile_max_x, tile_min_y = tilesystem.lat_lng_to_tile_xy(max_lat, max_lng, zoom)

    #number of tiles x and y in destination
    num_tiles_x = tile_max_x - tile_min_x + 1
    num_tiles_y = tile_max_y - tile_min_y + 1
    #print 'num tiles x:%d' % num_tiles_x
    #print 'num tiles y:%d' % num_tiles_y

    #number of pixels x and y (to be inserted in tile window with offsets)
    num_pixels_x = pixel_max_x - pixel_min_x + 1
    num_pixels_y = pixel_max_y - pixel_min_y + 1
    #print 'num px x:%d' % num_pixels_x
    #print 'num px y:%d' % num_pixels_y
    
    offset_west = pixel_min_x % tilesystem.tile_size
    offset_north = pixel_min_y % tilesystem.tile_size
    #offset_east = tilesystem.tile_size - (pixel_max_x % tilesystem.tile_size)
    #offset_south = tilesystem.tile_size - (pixel_max_y % tilesystem.tile_size)
    #print 'offset w:%d, n:%d, e:%d, s:%d' % (offset_west, offset_north, offset_east, offset_south)

    ###NOTE: This step skipped by re-scaling re-projected vrt in the map stack
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
    #in memory dataset properly offset in tile window
    tmp_offset = mem_driver.Create('', num_tiles_x * tilesystem.tile_size, num_tiles_y * tilesystem.tile_size, bands=bands)
    data = ds.ReadRaster(0, 0, num_pixels_x, num_pixels_y, num_pixels_x, num_pixels_y)
    tmp_offset.WriteRaster(offset_west, offset_north, num_pixels_x, num_pixels_y, data, band_list=range(1, bands+1))

    del ds
    del data

    cursor_pixel_x = 0
    cursor_pixel_y = 0
    print 'producing map tiles'
    for x in range(tile_min_x, tile_max_x + 1, 1):

        tile_dir = os.path.join(out_dir, str(zoom), str(x))
        if not os.path.isdir(tile_dir):
            os.makedirs(tile_dir)

        for y in range(tile_min_y, tile_max_y+1, 1):
            tile_path = os.path.join(tile_dir, str(y) + '.png')
            data = tmp_offset.ReadRaster(cursor_pixel_x, cursor_pixel_y, tilesystem.tile_size, tilesystem.tile_size, tilesystem.tile_size, tilesystem.tile_size)
            tile_mem = mem_driver.Create('', tilesystem.tile_size, tilesystem.tile_size, bands=bands)
            tile_mem.WriteRaster(0, 0, tilesystem.tile_size, tilesystem.tile_size, data, band_list=range(1, bands+1))
            #TODO: process png image data with http://pngquant.org/lib/ before saving to disk
            png_driver.CreateCopy(tile_path, tile_mem, strict=0)

            del data
            del tile_mem

            cursor_pixel_y += tilesystem.tile_size

        cursor_pixel_x += tilesystem.tile_size
        cursor_pixel_y = 0

    del tmp_offset


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
    map_stack = _build_tmp_vrt_stack_for_map(map_path, zoom_level, cutline)
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
    reader = catalog.get_reader_for_region(catalog_name)
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    pool.map_async(partial(_build_tiles_for_map_helper, name=catalog_name), reader)
    pool.close()
    pool.join() # wait for pool to empty