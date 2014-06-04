#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

from osgeo import gdal
import osr
import math

'''some convenience methods for information about gdal data sets
'''


def dataset_get_cutline_geometry(gdal_ds, cutline):
    """return a cutline in WKT geometry with coordinates expressed in dataset source pixel/line coordinates.

       cutline string format example: 48.3,-123.2:48.5,-123.2:48.5,-122.7:48.3,-122.7:48.3,-123.2
       : dilineated latitude,longitude WGS-84 coordinates (in decimal degrees)
    """

    #---- create coordinate transform from lat lng to data set coords
    ds_wkt = dataset_get_projection_wkt(gdal_ds)
    ds_srs = osr.SpatialReference()
    ds_srs.ImportFromWkt(ds_wkt)

    wgs84_srs = osr.SpatialReference()
    wgs84_srs.ImportFromEPSG(4326)

    transform = osr.CoordinateTransformation(wgs84_srs, ds_srs)

    #---- grab inverted geomatrix from ground control points
    gcps = gdal_ds.GetGCPs()
    geotransform = gdal.GCPsToGeoTransform(gcps)
    _success, inv_geotransform = gdal.InvGeoTransform(geotransform)

    #---- transform lat long to dataset coordinates, then coordinates to pixel/lines
    polygon_wkt = 'POLYGON (('

    #x_coords = []
    #y_coords = []

    for latlng in cutline.split(':'):
        lat, lng = latlng.split(',')
        geo_x, geo_y = transform.TransformPoint(float(lng), float(lat))[:2]
        px = int(inv_geotransform[0] + inv_geotransform[1] * geo_x + inv_geotransform[2] * geo_y)
        py = int(inv_geotransform[3] + inv_geotransform[4] * geo_x + inv_geotransform[5] * geo_y)
        #x_coords.append(geo_x)
        #y_coords.append(geo_y)
        polygon_wkt += '%d %d,' % (px, py)

    polygon_wkt = polygon_wkt[:-1] + '))'

    ##--- get extents
    #extents = [str(min(x_coords)), str(min(y_coords)), str(max(x_coords)), str(max(y_coords))]  # xmin ymin xmax ymax

    return polygon_wkt


def dataset_get_projection_wkt(gdal_ds):
    """returns a gdal dataset's projection in well known text"""
    ds_wkt = gdal_ds.GetProjectionRef()
    if ds_wkt is '':
        ds_wkt = gdal_ds.GetGCPProjection()

    return ds_wkt


def dataset_get_proj4_srs_declaration(gdal_ds):
    ds_wkt = dataset_get_projection_wkt(gdal_ds)
    sr = osr.SpatialReference(ds_wkt)
    return sr.ExportToProj4()


def dataset_get_as_epsg_900913(gdal_ds):
    epsg_900913 = '+proj=merc %s +k=1 +x_0=0 +y_0=0 +a=6378137 +b=6378137 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs'
    srs = dataset_get_proj4_srs_declaration(gdal_ds)
    val = '0'
    for ea in srs.split(' '):
        ea = ea.strip()
        if ea.startswith('+lon_0='):
            val = ea[7:]

    return epsg_900913 % ('+lon_0=' + val)


def dataset_has_color_palette(gdal_ds):
    """returns true of false wether a gdal dataset has a color palette
    """
    return gdal_ds.GetRasterBand(1).GetRasterColorTable() is not None


def dataset_lat_lng_bounds(gdal_ds):
    """returns the bounding box of a gdal dataset in latitude,longitude WGS-84 coordinates (in decimal degrees)
       bounding box returned as: min_lng, min_lat, max_lng, max_lat
    """

    out_srs = osr.SpatialReference()
    out_srs.ImportFromEPSG(4326)

    ds_wkt = dataset_get_projection_wkt(gdal_ds)
    ds_srs = osr.SpatialReference()
    ds_srs.ImportFromWkt(ds_wkt)

    #we need a north up dataset
    ds = gdal.AutoCreateWarpedVRT(gdal_ds, ds_wkt, ds_wkt)
    geotransform = get_geo_transform(ds)
    transform = osr.CoordinateTransformation(ds_srs, out_srs)

    #useful information about geotransform
    #geotransform[0] #top left X
    #geotransform[1] #w-e pixel resolution
    #geotransform[2] #rotation, 0 if image is "north up"
    #geotransform[3] #top left Y
    #geotransform[4] #rotation, 0 if image is "north up"
    #geotransform[5] n-s pixel resolution

    west = geotransform[0]
    east = west + ds.RasterXSize * geotransform[1]
    north = geotransform[3]
    south = north - ds.RasterYSize * geotransform[1]

    east, south = transform.TransformPoint(east, south)[:2]
    west, north = transform.TransformPoint(west, north)[:2]

    gt = get_geo_transform(gdal_ds)

    if gt is None:
        is_north_up = False
    else:
        rotation = get_rotation(gt)
        is_north_up = rotation < .5 or rotation > 359.5

    #min_lng, max_lat, max_lng, min_lat
    return (west, north, east, south), is_north_up


def dataset_meters_bounds(gdal_ds):
    """returns the bounding box of a gdal dataset in latitude,longitude WGS-84 coordinates (in decimal degrees)
       bounding box returned as: min_lng, min_lat, max_lng, max_lat
    """

    out_srs = osr.SpatialReference()
    out_srs.ImportFromEPSG(900913)

    ds_wkt = dataset_get_projection_wkt(gdal_ds)
    ds_srs = osr.SpatialReference()
    ds_srs.ImportFromWkt(ds_wkt)

    #we need a north up dataset
    ds = gdal.AutoCreateWarpedVRT(gdal_ds, ds_wkt, ds_wkt)
    geotransform = get_geo_transform(ds)
    transform = osr.CoordinateTransformation(ds_srs, out_srs)

    #useful information about geotransform
    #geotransform[0] #top left X
    #geotransform[1] #w-e pixel resolution
    #geotransform[2] #rotation, 0 if image is "north up"
    #geotransform[3] #top left Y
    #geotransform[4] #rotation, 0 if image is "north up"
    #geotransform[5] n-s pixel resolution

    west = geotransform[0]
    east = west + ds.RasterXSize * geotransform[1]
    north = geotransform[3]
    south = north - ds.RasterYSize * geotransform[1]

    east, south = transform.TransformPoint(east, south)[:2]
    west, north = transform.TransformPoint(west, north)[:2]

    rotation = get_rotation(get_geo_transform(gdal_ds))
    is_north_up = rotation < .5 or rotation > 359.5

    #min_lng, max_lat, max_lng, min_lat
    return (west, north, east, south), is_north_up


def get_geo_transform(gdal_ds):
    """
    :param gdal_ds: gdal dataset
    :return: a geo transform from ground control points if possible
    """
    gcps = gdal_ds.GetGCPs()
    if gcps is not None:
        gt = gdal.GCPsToGeoTransform(gcps)

    if gt is None:
        gt = gdal_ds.GetGeoTransform()

    return gt


def get_rotation(gt):
    """ Get rotation angle from a geotransform
        @type gt: C{tuple/list}
        @param gt: geotransform
        @rtype: C{float}
        @return: rotation angle
    """
    # noinspection PyBroadException
    try:
        return math.degrees(math.tanh(gt[2]/gt[5])) % 360
    except:
        return 0


def apply_geo_transform(inx, iny, gt):
    """ Apply a geotransform
        @param  inx:       Input x coordinate (double)
        @param  iny:       Input y coordinate (double)
        @param  gt:        Input geotransform (six doubles)

        @return: outx, outy Output coordinates (two doubles)
    """
    outx = gt[0] + inx*gt[1] + iny*gt[2]
    outy = gt[3] + inx*gt[4] + iny*gt[5]
    return outx, outy


def map_to_pixels(mx, my, gt):
    """Convert map to pixel coordinates
        @param  mx:    Input map x coordinate (double)
        @param  my:    Input map y coordinate (double)
        @param  gt:    Input geotransform (six doubles)
        @return: px,py Output coordinates (two ints)

        @change: changed int(p[x,y]+0.5) to int(p[x,y]) as per http://lists.osgeo.org/pipermail/gdal-dev/2010-June/024956.html
        @change: return floats
        @note:   0,0 is UL corner of UL pixel, 0.5,0.5 is centre of UL pixel
    """
    if gt[2] + gt[4] == 0:  # Simple calc, no inversion required
        px = (mx - gt[0]) / gt[1]
        py = (my - gt[3]) / gt[5]
    else:
        px, py = apply_geo_transform(mx, my, gdal.InvGeoTransform(gt))
    return int(px), int(py)


# if __name__ == '__main__':
#     import tilesystem as ts
#     import bsb
#     m_path = '/Users/williamkamp/charts/BSB_ROOT/13297/13297_1.KAP'
#     ds = gdal.Open(m_path, gdal.GA_ReadOnly)
#     bounds, _ = dataset_lat_lng_bounds(ds)
#     west, north, east, south = bounds
#     print '---------------------'
#     print 'lat north', north
#     print 'lat south', south
#     print 'lat east', east
#     print 'lat west', west
#
#     west, north, east, south, _, _ = ts.lat_lng_bounds_to_tile_bounds_count(bounds, 16)
#     print '---------------------'
#     print 'tile north', north
#     print 'tile south', south
#     print 'tile east', east
#     print 'tile west', west
#
#     print '---------------------'
#     print dataset_get_cutline_geometry(ds, bsb.BsbHeader(m_path).get_outline())