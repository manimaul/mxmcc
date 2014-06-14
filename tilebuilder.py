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
import osr
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


def _build_tile_vrt_for_map(map_path, cutline=None, verbose=False):
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
    _, is_north_up = gdalds.dataset_lat_lng_bounds(dataset)

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

    #-----repoject map to tilesystem projection, crop to cutline
    w_vrt_path = os.path.join(base_dir, map_name + '_w.vrt')
    if os.path.isfile(w_vrt_path):
        os.remove(w_vrt_path)

    epsg_900913 = gdalds.dataset_get_as_epsg_900913(dataset)  # offset for crossing dateline

    # average resampling fails on some rotated maps... result is fully transparent or (interlaced transparent)
    if is_north_up:
        resampling = 'average'
    else:
        resampling = 'bilinear'

    print 'using resampling', resampling

    command = ['gdalwarp', '-of', 'vrt', '-r', resampling, '-t_srs', epsg_900913]

    if cutline is not None:
        cut_poly = gdalds.dataset_get_cutline_geometry(dataset, cutline)
        command += ['-wo', 'CUTLINE=%s' % cut_poly]

    command += [_stack_peek(map_stack),  # gdal input source
                w_vrt_path]  # gdal output destination

    subprocess.Popen(command).wait()
    map_stack.append(w_vrt_path)

    return map_stack


def _render_tmp_vrt_stack_for_map(map_stack, zoom, out_dir):
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
        print 'skipping: ' + out_dir
        return

    print 'tile out dir:', out_dir

    map_path = _stack_peek(map_stack)

    ds = gdal.Open(map_path, gdal.GA_ReadOnly)

    if ds is None:
        print 'unable to open', map_path
        return

    zoom_level = int(zoom)

    ### fetch vrt data-set extends as tile bounds
    lat_lng_bounds_wnes, is_north_up = gdalds.dataset_lat_lng_bounds(ds)

    tile_bounds_wnes = tilesystem.lat_lng_bounds_to_tile_bounds_count(lat_lng_bounds_wnes, zoom_level)

    tile_west, tile_north, tile_east, tile_south, tile_count_x, tile_count_y = tile_bounds_wnes

    #---- create coordinate transform from lat lng to data set coords
    ds_wkt = gdalds.dataset_get_projection_wkt(ds)
    ds_srs = osr.SpatialReference()
    ds_srs.ImportFromWkt(ds_wkt)

    wgs84_srs = osr.SpatialReference()
    wgs84_srs.ImportFromEPSG(4326)

    transform = osr.CoordinateTransformation(wgs84_srs, ds_srs)

    #---- grab inverted geomatrix from ground control points
    geotransform = gdalds.get_geo_transform(ds)
    _success, inv_transform = gdal.InvGeoTransform(geotransform)

    # print 'west east', tile_west, tile_east
    # print 'south north', tile_south, tile_north

    if tile_west > tile_east:  # dateline wrap
        # print 'wrapping tile to dateline'
        _cut_tiles_in_range(0, tile_west, tile_south, tile_north, transform,
                            inv_transform, zoom_level, out_dir, ds)
        _cut_tiles_in_range(tile_east, tilesystem.map_size_tiles(zoom_level),
                            tile_south, tile_north, transform, inv_transform, zoom_level, out_dir, ds)
    else:
        _cut_tiles_in_range(tile_west, tile_east, tile_south, tile_north, transform,
                            inv_transform, zoom_level, out_dir, ds)


def _cut_tiles_in_range(tile_min_x, tile_max_x, tile_min_y, tile_max_y, transform,
                        inv_transform, zoom_level, out_dir, ds):

    for tile_x in range(tile_min_x, tile_max_x + 1, 1):

        # if tile_x != 9084:
        #     continue

        tile_dir = os.path.join(out_dir, str(zoom_level), str(tile_x))

        for tile_y in range(tile_min_y, tile_max_y + 1, 1):

            # if tile_y != 13815:
            #     continue

            tile_path = os.path.join(tile_dir, str(tile_y) + '.png')
            # print tile_path

            m_px, m_py = tilesystem.tile_xy_to_pixel_xy(tile_x, tile_y)
            lat, lng = tilesystem.pixel_xy_to_lat_lng(m_px, m_py, zoom_level)
            geo_x, geo_y = transform.TransformPoint(float(lng), float(lat))[:2]
            ds_px = int(inv_transform[0] + inv_transform[1] * geo_x + inv_transform[2] * geo_y)
            ds_py = int(inv_transform[3] + inv_transform[4] * geo_x + inv_transform[5] * geo_y)

            lat, lng = tilesystem.pixel_xy_to_lat_lng(m_px+tilesystem.tile_size, m_py+tilesystem.tile_size, zoom_level)
            geo_x, geo_y = transform.TransformPoint(float(lng), float(lat))[:2]
            ds_pxx = int(inv_transform[0] + inv_transform[1] * geo_x + inv_transform[2] * geo_y)
            ds_pyy = int(inv_transform[3] + inv_transform[4] * geo_x + inv_transform[5] * geo_y)

            # print 'ds_px', ds_px, 'ds_py', ds_py
            # print 'ds_pxx', ds_pxx, 'ds_pyy', ds_pyy
            # print 'lat lng', lat, lng
            # print 'geo', geo_x, geo_y
            # print 'raster size x y', ds.RasterXSize, ds.RasterYSize

            ds_px_clip = tilesystem.clip(ds_px, 0, ds.RasterXSize)
            ds_pxx_clip = tilesystem.clip(ds_pxx, 0, ds.RasterXSize)
            x_size_clip = ds_pxx_clip - ds_px_clip

            ds_py_clip = tilesystem.clip(ds_py, 0, ds.RasterYSize)
            ds_pyy_clip = tilesystem.clip(ds_pyy, 0, ds.RasterYSize)
            y_size_clip = ds_pyy_clip - ds_py_clip

            if x_size_clip <= 0 or y_size_clip <= 0:
                continue

            # print 'ds_px_clip', ds_px_clip
            # print 'ds_py_clip', ds_py_clip
            # print 'x_size_clip', x_size_clip
            # print 'y_size_clip', y_size_clip
            # print '-----------------------------'
            #
            # print 'reading'
            data = ds.ReadRaster(ds_px_clip, ds_py_clip, x_size_clip, y_size_clip)

            transparent = True
            if data is not None:
                for ea in data:
                    if ord(ea) != 0:
                        transparent = False
                        break

            #only create tiles that have data (not completely transparent)
            if not transparent:
                x_size = ds_pxx - ds_px
                y_size = ds_pyy - ds_py
                # print 'x_size', x_size
                # print 'y_size', y_size

                if not os.path.isdir(tile_dir):
                    os.makedirs(tile_dir)
                # print 'create mem window'
                tmp = mem_driver.Create('', x_size, y_size, bands=ds.RasterCount)

                if ds_pxx == ds_pxx_clip:
                    xoff = x_size - x_size_clip
                else:
                    xoff = 0
                if ds_pyy == ds_pyy_clip:
                    yoff = y_size - y_size_clip
                else:
                    yoff = 0

                # print 'xoff', xoff
                # print 'yoff', yoff

                # print 'write mem window'
                tmp.WriteRaster(xoff, yoff, x_size_clip, y_size_clip, data, band_list=range(1, ds.RasterCount+1))

                # print 'create mem tile'
                tile = mem_driver.Create('', tilesystem.tile_size, tilesystem.tile_size, bands=ds.RasterCount)

                # print 'scale mem window to mem tile'
                for i in range(1, ds.RasterCount+1):
                    gdal.RegenerateOverview(tmp.GetRasterBand(i), tile.GetRasterBand(i), 'average')

                # print 'write to file'
                png_driver.CreateCopy(tile_path, tile, strict=0)


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
    map_stack = _build_tile_vrt_for_map(map_path, cutline)
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


# if __name__ == '__main__':
#     import bsb
#     # test_map = '/Users/williamkamp/charts/BSB_ROOT/13297/13297_1.KAP'
#     test_map = '/Volumes/USB_DATA/mxmcc/charts/noaa/BSB_ROOT/11428/11428_3.KAP'
#     h = bsb.BsbHeader(test_map)
#     z = h.get_zoom()
#     c = h.get_outline()
#     s = _build_tile_vrt_for_map(test_map, c)
#     _render_tmp_vrt_stack_for_map(s, z, None)
