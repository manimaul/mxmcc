#!/usr/bin/env python

# converted to python by (from C# and Java sources):
__author__ = 'Will Kamp'
__email__ = 'will@mxmariner.com'
# most of the credit belongs to:
__credits__ = ['http://msdn.microsoft.com/en-us/library/bb259689.aspx',
               'http://www.klokan.cz/projects/gdal2tiles/gdal2tiles.py']
__copyright__ = 'Copyright (c) 2013, Matrix Mariner Inc.\n' + \
                'Copyright (c) 2006-2009 Microsoft Corporation.  All rights reserved.\n' + \
                'Copyright (c) 2008, Klokan Petr Pridal'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'
__license__ = 'It\'s not too clear from the original source ?(Public domain)'


'''Microsoft, Google, OpenStreetMap (ZXY) tile system conversion methods to and from:
   WGS84 latitude longitude, and EPSG:900913 meter
'''

import numpy

tile_size = 256
earth_radius = 6378137.
earth_circumference = 2. * numpy.pi * earth_radius  # at equator
origin_shift = earth_circumference / 2.  # 20037508.342789244
min_latitude = -85.05112878
max_latitude = 85.05112878
min_longitude = -180.
max_longitude = 180.
inches_per_meter = 39.3701
max_zoom_level = 23

##Following methods adapted from http://msdn.microsoft.com/en-us/library/bb259689.aspx


def clip(num, min_value, max_value):
    """num - the number to clip
       min_value - minimum allowable value
       max_value - maximum allowable value
    """
    return numpy.minimum(numpy.maximum(num, min_value), max_value)


def map_size(level_of_detail):
    """determines the map width and height (in pixels) at a specified level of detail
       level_of_detail, from 1 (lowest detail) to 23 (highest detail)
       returns map height and width in pixels
    """
    return float(tile_size << level_of_detail)


def map_size_tiles(level_of_detail):
    """determines the map width and height (in tiles) at a specified level of detail
       level_of_detail, from 1 (lowest detail) to 23 (highest detail)
       returns map height and width in number of tiles
    """
    return int(map_size(level_of_detail) / tile_size)


def ground_resolution(latitude, level_of_detail):
    """determines the ground resolution (in meters per pixel) at a specifiec latitude and
       level of detail
       latitude - (in decimal degrees) at which to measure the ground resolution
       level_of_detail, from 1 (lowest detail) to 23 (highest detail)
       returns the ground resolution in meters per pixel
    """
    latitude = clip(latitude, min_latitude, max_latitude)
    return numpy.cos(latitude * numpy.pi / 180.) * 2 * numpy.pi * earth_radius / map_size(level_of_detail)


def map_scale(latitude, level_of_detail, dpi):
    """determines the map scale at a specified latitude, level of detail, and dpi resolution
       latitude - (in decimal degrees) at which to measure the ground resolution
       level_of_detail, from 1 (lowest detail) to 23 (highest detail)
       dpi - resolution in dots per inch
    """
    return ground_resolution(latitude, level_of_detail) * dpi / 0.0254


def lat_lng_to_pixel_xy(latitude, longitude, level_of_detail):
    """converts latitude/longitude WGS-84 coordinates (in decimal degrees) into pixel x,y
       latitude - (in decimal degrees) to convert
       longitude - (in decimal degrees) to convert
       level_of_detail, from 1 (lowest detail) to 23 (highest detail)
    """
    latitude = clip(latitude, min_latitude, max_latitude)
    longitude = clip(longitude, min_longitude, max_longitude)

    x = (longitude + 180.) / 360.
    sin_lat = numpy.sin(latitude * numpy.pi / 180.)
    y = .5 - numpy.log((1. + sin_lat) / (1. - sin_lat)) / (4. * numpy.pi)

    m_size = map_size(level_of_detail)
    x = int(clip(x*m_size + .5, 0, m_size - 1))
    y = int(clip(y*m_size + .5, 0, m_size - 1))
    return x, y


def lat_lng_to_tile_xy(latitude, longitude, level_of_detail):
    """gives you zxy tile coordinate for given latitude, longitude WGS-84 coordinates (in decimal degrees)
    """
    x, y = lat_lng_to_pixel_xy(latitude, longitude, level_of_detail)
    return pixel_xy_to_tile_xy(x, y)


def pixel_xy_to_lat_lng(x, y, level_of_detail):
    """converts a pixel x,y coordinates at a specified level of detail into
       latitude,longitude WGS-84 coordinates (in decimal degrees)
       x - coordinate of point in pixels
       y - coordinate of point in pixels
       level_of_detail, from 1 (lowest detail) to 23 (highest detail)
    """
    m_size = map_size(level_of_detail)

    x = (clip(x, 0, m_size - 1) / m_size) - .5
    y = .5 - (clip(y, 0, m_size - 1) / m_size)

    lat = 90. - 360. * numpy.arctan(numpy.exp(-y * 2 * numpy.pi)) / numpy.pi
    lng = 360. * x
    return lat, lng


def pixel_xy_to_tile_xy(x, y):
    """converts pixel x,y coordinates into tile x,y coordinates of the tile containing the specified pixel
       x - pixel coordinate
       y - pixel coordinate
    """
    return x / tile_size, y / tile_size


def tile_xy_to_pixel_xy(tile_x, tile_y):
    """converts tile x,y coordinates into pixel x,y coordinates of the upper-left pixel of the specified tile
       tile_x - tile coordinate
       tile_y - tile coordinate
    """
    return tile_x * tile_size, tile_y * tile_size


def level_of_detail_for_pixel_size(latitude, pixel_size):
    """maximal scale down zoom of the pyramid closest to the pixel_size
    """
    for zoom in range(max_zoom_level):
        if pixel_size > ground_resolution(latitude, zoom):
            if zoom is not 0:
                return zoom
            else:
                return 0  # We don't want to scale up


#Following methods adapted from http://www.klokan.cz/projects/gdal2tiles/gdal2tiles.py
#and changed from TMS pyramid coordinate to ZXY coordinate outputs

def pixels_to_meters(px, py, level_of_detail):
    """
        :param px: X tile system pixels
        :param py: Y tile system pixels
        :param level_of_detail: tile system zoom level
        :return: EPSG:900913 map coordinates
    """
    res = ground_resolution(0, level_of_detail)
    mx = px * res - origin_shift
    my = py * res - origin_shift
    return mx, my


def meters_to_pixels(meters_x, meters_y, level_of_detail):
    """converts XY point from Spherical Mercator EPSG:900913 to ZXY pixel coordinates
    """
    res = ground_resolution(0, level_of_detail)  # ground resolution at equator
    x = int((meters_x + origin_shift) / res)
    y = int((meters_y + origin_shift) / res)
    return tms_to_zxy_coord(x, y, level_of_detail)


def meters_to_tile(meters_x, meters_y, level_of_detail):
    """converts XY point from Spherical Mercator EPSG:900913 to ZXY tile coordinates
    """
    x, y = meters_to_pixels(meters_x, meters_y, level_of_detail)
    tx, ty = pixel_xy_to_tile_xy(x, y)
    return tx, ty


def meters_to_lat_lng(meters_x, meters_y):
    """converts XY point from Spherical Mercator EPSG:900913 to lat/lon in WGS84 Datum
    """
    lng = (meters_x / origin_shift) * 180.0
    lat = (meters_y / origin_shift) * 180.0

    lat = 180 / numpy.pi * (2 * numpy.arctan(numpy.exp(lat * numpy.pi / 180.0)) - numpy.pi / 2.0)
    return lat, lng


# def lat_lng_to_meters(lat, lng):
#     """converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913
#     """
#     meters_x = lng * origin_shift / 180.0
#     meters_y = numpy.log(numpy.tan((90 + lat) * numpy.pi / 360.0)) / (numpy.pi / 180.0)
#
#     meters_y = meters_y * origin_shift / 180.0
#     return meters_x, meters_y


#conversions from TMS tile system coordinates
#TMS coordinates originate from bottom left
#ZXY coordinates originate from the top left

def tms_to_zxy_coord(px, py, zoom):
    """Converts TMS pixel coordinates to ZXY pixel coordinates
       or vise versa
    """
    return px, (2**zoom) * tile_size - py - 1


def tms_tile_to_zxy_tile(tx, ty, zoom):
    """Converts TMS tile coordinates to ZXY tile coordinates
       or vise versa
    """
    return tx, (2**zoom - 1) - ty


def lat_lng_bounds_to_pixel_bounds_res((min_lng, max_lat, max_lng, min_lat), level_of_detail):
    """
        Latitude longitude bounds to tile system pixel bounds
        :param level_of_detail: tile system zoom level
        :return: tile system pixel extents and resolution
    """
    #this seems counter intuitive... tile / pixel 0,0 is top left where as lat long 0,0 is bottom left
    pixel_west, pixel_north = lat_lng_to_pixel_xy(min_lat, min_lng, int(level_of_detail))
    pixel_east, pixel_south = lat_lng_to_pixel_xy(max_lat, max_lng, int(level_of_detail))
    res_x = pixel_east - pixel_west + 1
    res_y = pixel_north - pixel_south + 1

    #dateline wrap
    if res_x < 0:
        res_x = (map_size(level_of_detail) - pixel_west) + pixel_east + 2

    return pixel_west, pixel_north, pixel_east, pixel_south, res_x, res_y


def lat_lng_bounds_to_tile_bounds_count((min_lng, max_lat, max_lng, min_lat), level_of_detail):
    """
        Latitude longitude bounds to tile system bounds
        :param level_of_detail: tile system zoom level
        :return: tile bounding extents and count
    """
    #this seems counter intuitive... tile / pixel 0,0 is top left where as lat long 0,0 is bottom left
    tile_west, tile_north = lat_lng_to_tile_xy(min_lat, min_lng, level_of_detail)
    tile_east, tile_south = lat_lng_to_tile_xy(max_lat, max_lng, level_of_detail)
    num_tiles_west_east = tile_east - tile_west + 1
    num_tiles_north_south = tile_north - tile_south + 1

    #dateline wrap
    if num_tiles_west_east < 0:
        num_tiles_west_east = (map_size_tiles(level_of_detail) - tile_west) + tile_east + 2

    return tile_west, tile_north, tile_east, tile_south, num_tiles_west_east, num_tiles_north_south