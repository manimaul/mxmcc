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
import traceback
import json
import shutil
from PIL import Image

from osgeo import gdal
import osr

import logger
import tilesystem
import gdalds
import catalog
import config


# http://www.gdal.org/formats_list.html
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


def _cleanup_tmp_vrt_stack(vrt_stack):
    """convenience method for removing temporary vrt files created with _build_tmp_vrt_stack_for_map()
    """
    for i in range(1, len(vrt_stack), 1):
        os.remove(vrt_stack[i])
        logger.log(logger.OFF, 'deleting temp file:', vrt_stack[i])


def _stack_peek(vrt_stack):
    """the peek of a vrt stack
    """
    return vrt_stack[-1]


def _build_tile_vrt_for_map(map_path, cutline=None):
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

    # log = open(os.devnull, 'w')  # subprocess.PIPE
    log = subprocess.PIPE

    #-----paths and file names
    base_dir = os.path.dirname(map_path)
    map_fname = os.path.basename(map_path)
    map_name = map_fname[0:map_fname.find('.')]  # remove file extension

    #-----if map has a palette create vrt with expanded rgba
    if gdalds.dataset_has_color_palette(dataset):
        logger.log(logger.ON, 'dataset has color palette')
        c_vrt_path = os.path.join(base_dir, map_name + '_c.vrt')
        if os.path.isfile(c_vrt_path):
            os.remove(c_vrt_path)

        # try:
        command = "gdal_translate -of vrt -expand rgba \'%s\' \'%s\'" % (map_path, c_vrt_path)
        subprocess.Popen(shlex.split(command), stdout=log).wait()

        logger.log(logger.ON, 'creating c_vrt with command', command)

        del dataset
        dataset = gdal.Open(c_vrt_path, gdal.GA_ReadOnly)

        logger.log(logger.ON, 'openning dataset')

        map_stack.append(c_vrt_path)
        # except BaseException as e:
        #     logger.log(logger.ON, e)

    #-----repoject map to tilesystem projection, crop to cutline
    w_vrt_path = os.path.join(base_dir, map_name + '.vrt')
    if os.path.isfile(w_vrt_path):
        os.remove(w_vrt_path)

    epsg_900913 = gdalds.dataset_get_as_epsg_900913(dataset)  # offset for crossing dateline

    resampling = 'average'

    command = ['gdalwarp', '-of', 'vrt', '-r', resampling, '-t_srs', epsg_900913]

    # logger.log(logger.ON, 'using ply overrides', use_ply_overrides)
    # if use_ply_overrides:
    #     override = overrides.get_poly_override(map_path)
    #     if override is not None:
    #         cutline = override

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

    logger.log(logger.ON, '_render_tmp_vrt_stack_for_map: out_dir = ' + out_dir + ', zoom = ' + zoom)

    # elif verify.verify_tile_dir(out_dir):
    #    logger.log(logger.ON, 'skipping: ' + out_dir
    #    return

    logger.log(logger.ON, 'tile out dir:', out_dir)

    map_path = _stack_peek(map_stack)

    ds = gdal.Open(map_path, gdal.GA_ReadOnly)

    if ds is None:
        logger.log(logger.ON, 'unable to open', map_path)
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

    logger.log(logger.OFF, 'west east', tile_west, tile_east)

    if tile_west > tile_east:  # dateline wrap
        logger.log(logger.OFF, 'wrapping tile to dateline')
        _cut_tiles_in_range(0, tile_west, tile_south, tile_north, transform,
                            inv_transform, zoom_level, out_dir, ds)
        _cut_tiles_in_range(tile_east, tilesystem.map_size_tiles(zoom_level),
                            tile_south, tile_north, transform, inv_transform, zoom_level, out_dir, ds)
    else:
        _cut_tiles_in_range(tile_west, tile_east, tile_south, tile_north, transform,
                            inv_transform, zoom_level, out_dir, ds)

    del ds


def _scale_tile(tile_dir, z, x, y):
    have_scale_tile = False
    zoom_in_level = z + 1
    tile_size = tilesystem.tile_size
    diff = abs(z - zoom_in_level)
    m_tile_size = tile_size >> diff
    xx = x << diff
    yy = y << diff
    num_tiles = 1 << diff
    in_tile_paths = []
    for xi in range(num_tiles):
        for yi in range(num_tiles):
            lower_x = xx + xi
            lower_y = yy + yi
            p = os.path.join(tile_dir, '%s/%s/%s.png' % (zoom_in_level, lower_x, lower_y))
            if os.path.isfile(p):
                in_tile_paths.append(p)
                have_scale_tile = True
            else:
                in_tile_paths.append(None)

    if have_scale_tile:
        im = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
        i = 0
        xoff = 0
        yoff = 0
        for in_tile_path in in_tile_paths:
            if i == 1:
                yoff += m_tile_size
            if i == 2:
                yoff -= m_tile_size
                xoff += m_tile_size
            if i == 3:
                yoff += m_tile_size
            if in_tile_path is not None:
                im.paste(Image.open(in_tile_path).resize((m_tile_size, m_tile_size), Image.ANTIALIAS), (xoff, yoff))
            i += 1

        t_dir = os.path.join(tile_dir, '%s/%s' % (z, x))
        if not os.path.isdir(t_dir):
            os.makedirs(t_dir)
        im.save(os.path.join(t_dir, '%s.png' % y))

    return have_scale_tile


def _cut_tiles_in_range(tile_min_x, tile_max_x, tile_min_y, tile_max_y, transform,
                        inv_transform, zoom_level, out_dir, ds):
    for tile_x in range(tile_min_x, tile_max_x + 1, 1):
        tile_dir = os.path.join(out_dir, '%s/%s' % (zoom_level, tile_x))

        for tile_y in range(tile_min_y, tile_max_y + 1, 1):
            tile_path = os.path.join(tile_dir, '%s.png' % tile_y)
            logger.log(logger.OFF, tile_path)

            # logger.debug = True

            #skip tile if exists
            if os.path.isfile(tile_path):
                logger.log(logger.OFF, 'skipping tile that exists', tile_path)
                continue

            #we can continue if the upper zoom exists even if _scale_tile returns false
            #because all upper zoom tiles may not exist if they were all fully transparent
            upper_zoom_exists = os.path.isdir(os.path.join(out_dir, str(zoom_level + 1)))

            #attempt to create tile from existing lower zoom tile
            if _scale_tile(out_dir, zoom_level, tile_x, tile_y) or upper_zoom_exists:
                logger.log(logger.OFF, 'scaled tile', tile_path)
                continue

            logger.log(logger.OFF, 'creating tile', tile_path)

            # logger.debug = False

            m_px, m_py = tilesystem.tile_xy_to_pixel_xy(tile_x, tile_y)
            lat, lng = tilesystem.pixel_xy_to_lat_lng(m_px, m_py, zoom_level)
            geo_x, geo_y = transform.TransformPoint(float(lng), float(lat))[:2]
            ds_px = int(inv_transform[0] + inv_transform[1] * geo_x + inv_transform[2] * geo_y)
            ds_py = int(inv_transform[3] + inv_transform[4] * geo_x + inv_transform[5] * geo_y)

            lat, lng = tilesystem.pixel_xy_to_lat_lng(m_px + tilesystem.tile_size, m_py + tilesystem.tile_size,
                                                      zoom_level)
            geo_x, geo_y = transform.TransformPoint(float(lng), float(lat))[:2]
            ds_pxx = int(inv_transform[0] + inv_transform[1] * geo_x + inv_transform[2] * geo_y)
            ds_pyy = int(inv_transform[3] + inv_transform[4] * geo_x + inv_transform[5] * geo_y)

            logger.log(logger.OFF, 'ds_px, ds_py is the datset coordinate of tile (upper left)')
            logger.log(logger.OFF, 'ds_px', ds_px, 'ds_py', ds_py)
            logger.log(logger.OFF, 'ds_pxx, ds_pyy is the datset coordinate of tile (lower right)')
            logger.log(logger.OFF, 'ds_pxx', ds_pxx, 'ds_pyy', ds_pyy)
            logger.log(logger.OFF, 'lat lng', lat, lng)
            logger.log(logger.OFF, 'geo', geo_x, geo_y)
            logger.log(logger.OFF, 'raster actual size x y', ds.RasterXSize, ds.RasterYSize)

            ds_px_clip = tilesystem.clip(ds_px, 0, ds.RasterXSize)
            ds_pxx_clip = tilesystem.clip(ds_pxx, 0, ds.RasterXSize)
            x_size_clip = ds_pxx_clip - ds_px_clip

            ds_py_clip = tilesystem.clip(ds_py, 0, ds.RasterYSize)
            ds_pyy_clip = tilesystem.clip(ds_pyy, 0, ds.RasterYSize)
            y_size_clip = ds_pyy_clip - ds_py_clip

            if x_size_clip <= 0 or y_size_clip <= 0:
                continue

            logger.log(logger.OFF, 'ds_px_clip', ds_px_clip)
            logger.log(logger.OFF, 'ds_py_clip', ds_py_clip)
            logger.log(logger.OFF, 'x_size_clip', x_size_clip)
            logger.log(logger.OFF, 'y_size_clip', y_size_clip)
            logger.log(logger.OFF, '-----------------------------')

            logger.log(logger.OFF, 'reading dataset')
            data = ds.ReadRaster(int(ds_px_clip), int(ds_py_clip), int(x_size_clip), int(y_size_clip))

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
                logger.log(logger.OFF, 'x_size', x_size)
                logger.log(logger.OFF, 'y_size', y_size)

                if not os.path.isdir(tile_dir):
                    os.makedirs(tile_dir)

                logger.log(logger.OFF, 'ds_pxx', ds_pxx)
                logger.log(logger.OFF, 'ds_pxx_clip', ds_pxx_clip)
                logger.log(logger.OFF, 'ds_pyy', ds_pyy)
                logger.log(logger.OFF, 'ds_pyy_clip', ds_pyy_clip)

                if ds_pxx == ds_pxx_clip:
                    xoff = x_size - x_size_clip
                elif ds_px_clip == 0 and ds_px < 0:
                    xoff = abs(ds_px)
                else:
                    xoff = 0
                if ds_pyy == ds_pyy_clip:
                    yoff = y_size - y_size_clip
                elif ds_py_clip == 0 and ds_py < 0:
                    yoff = abs(ds_py)
                else:
                    yoff = 0

                logger.log(logger.OFF, 'xoff', xoff)
                logger.log(logger.OFF, 'yoff', yoff)
                tile_bands = ds.RasterCount + 1

                logger.log(logger.OFF, 'create mem window')
                tmp = mem_driver.Create('', int(x_size), int(y_size), bands=ds.RasterCount)

                logger.log(logger.OFF, 'write mem window')
                tmp.WriteRaster(int(xoff), int(yoff), int(x_size_clip), int(y_size_clip), data,
                                band_list=range(1, tile_bands))

                logger.log(logger.OFF, 'create mem tile')
                tile = mem_driver.Create('', tilesystem.tile_size, tilesystem.tile_size, bands=ds.RasterCount)

                scaling_up = int(x_size) < tilesystem.tile_size or int(y_size) < tilesystem.tile_size

                #check if we're scaling image up
                if scaling_up:
                    logger.log(logger.OFF, 'scaling up')
                    tmp.SetGeoTransform((0.0, tilesystem.tile_size / float(x_size), 0.0,
                                         0.0, 0.0, tilesystem.tile_size / float(y_size)))
                    tile.SetGeoTransform((0.0, 1.0, 0.0, 0.0, 0.0, 1.0))
                    gdal.ReprojectImage(tmp, tile, None, None, gdal.GRA_Average)
                #or scaling image down
                else:
                    logger.log(logger.OFF, 'scaling down')
                    for i in range(1, ds.RasterCount + 1):
                        gdal.RegenerateOverview(tmp.GetRasterBand(i), tile.GetRasterBand(i), 'average')

                logger.log(logger.OFF, 'write to file')
                png_driver.CreateCopy(tile_path, tile, strict=0)

                del data
                del tmp
                del tile


def build_tiles_for_map(kap, map_path, start_zoom, stop_zoom, cutline=None, out_dir=None):
    """builds tiles for a map_path - path to map to render tiles for
       zoom_level - int or string representing int of the single zoom level to render
       cutline - string defining the map border cutout... this can be None if the whole
       map should be rendered.
       out_dir - path to where tiles will be rendered to, if set to None then
       tiles will be rendered int map_path's base directory

       cutline string format example: 48.3,-123.2:48.5,-123.2:48.5,-122.7:48.3,-122.7:48.3,-123.2
       : dilineated latitude/longitude WGS-84 coordinates (in decimal degrees)
    """
    map_stack = _build_tile_vrt_for_map(map_path, cutline=cutline)

    #---- render tiles in the same directory of the map if not specified
    if out_dir is None:
        out_dir = os.path.dirname(_stack_peek(map_stack))
        out_dir = os.path.join(out_dir, 'tiles')
    elif not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    #---- if we are only rendering 1 zoom level, over-shoot by one so we can scale down with anti-aliasing
    single_z_mode = config.use_single_zoom_over_zoom and stop_zoom == start_zoom
    logger.log(logger.ON, 'single zoom mode', single_z_mode)
    if single_z_mode:
        stop_zoom += 1

    zoom_range = range(stop_zoom, start_zoom - 1, -1)

    if single_z_mode:
        stop_zoom -= 1

    logger.log(logger.ON, 'zoom range', zoom_range)

    logger.log(logger.ON, 'out_dir', out_dir)

    try:
        # Mxmcc tiler
        for z in zoom_range:
            logger.log(logger.ON, 'rendering map_stack peek')
            _render_tmp_vrt_stack_for_map(map_stack, str(z), out_dir)

        if single_z_mode:
            oz_dir = os.path.join(out_dir, str(stop_zoom + 1))
            logger.log(logger.ON, 'removing overzoom dir: ', oz_dir)
            shutil.rmtree(oz_dir)

        ds = gdal.Open(map_path, gdal.GA_ReadOnly)
        bounds, _ = gdalds.dataset_lat_lng_bounds(ds)
        west, north, east, south = bounds

        tilejson_tilemap = {
            'name': kap,
            'description': None,
            'attribution': 'MXMariner.com',
            'type': 'overlay',
            'version': '1',
            'format': 'png',
            'minzoom': start_zoom,
            'maxzoom': stop_zoom,
            'bounds':  '%s,%s,%s,%s' % (west, south, east, north),
            'profile': 'mercator',
            'basename': kap,
            'tilejson': '2.0.0',
            'scheme': 'xyz'
        }

        logger.log(logger.ON, 'writing tile json', tilejson_tilemap)

        write_tilejson_tilemap(out_dir, tilejson_tilemap)

        copy_viewer(out_dir)

    except BaseException as e:
        traceback.print_exc()
        logger.log(logger.ON, str(e))

    _cleanup_tmp_vrt_stack(map_stack)


def write_tilejson_tilemap(dst_dir, tilemap):
    f = os.path.join(dst_dir, 'metadata.json')
    logger.log(logger.OFF, "writing ", f)
    if os.path.exists(f):
        os.remove(f)
    with open(f, 'w') as f:
        json.dump(tilemap, f, indent=2)


def copy_viewer(dest):
    for f in ['viewer.js', 'viewer-esri.html', 'viewer-google.html', 'viewer-mapbox.html', 'viewer-openlayers.html']:
        src = os.path.join(os.path.dirname(os.path.realpath(__file__)), f)
        dst = os.path.join(dest, f)
        shutil.copy(src, dst)


def _build_tiles_for_map_helper(entry, name):
    """helper method for multiprocessing pool map_async
    """
    try:
        m_name = os.path.basename(entry['path'])
        out_dir = os.path.join(config.unmerged_tile_dir, name, m_name[0:m_name.find('.')])
        m_path = entry['path']
        m_zoom = int(entry['zoom'])
        m_outline = entry['outline']
        build_tiles_for_map(m_name, m_path, m_zoom, m_zoom, cutline=m_outline, out_dir=out_dir)

    except BaseException as e:
        traceback.print_exc()
        logger.log(logger.ON, e)


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
    test_map = config.noaa_bsb_dir + '/BSB_ROOT/11303/11303_1.KAP'
    test_bsb = bsb.BsbHeader(test_map)
    build_tiles_for_map('11303_1.KAP', test_map, test_bsb.get_zoom(), test_bsb.get_zoom(), test_bsb.get_outline())
    # build_tiles_for_map('11303_1.KAP', test_map, test_bsb.get_zoom(), test_bsb.get_zoom(), test_bsb.get_outline(),
    #                     out_dir='/data/mxmcc/charts/noaa/BSB_ROOT/11303/no_ovrply', use_ply_overrides=False)
