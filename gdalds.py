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
    geotransform = ds.GetGeoTransform()
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

    is_north_up = geotransform[2] + geotransform[5] == 0

    #min_lng, max_lat, max_lng, min_lat
    return (west, north, east, south), is_north_up


def get_rotation(gt):
    """ Get rotation angle from a geotransform
        @type gt: C{tuple/list}
        @param gt: geotransform
        @rtype: C{float}
        @return: rotation angle
    """
    try:
        return math.degrees(math.tanh(gt[2]/gt[5]))
    except:
        return 0


def InvGeoTransform(gt_in):
    '''
     ************************************************************************
     *                        InvGeoTransform(gt_in)
     ************************************************************************

     **
     * Invert Geotransform.
     *
     * This function will invert a standard 3x2 set of GeoTransform coefficients.
     *
     * @param  gt_in  Input geotransform (six doubles - unaltered).
     * @return gt_out Output geotransform (six doubles - updated) on success,
     *                None if the equation is uninvertable.
    '''
    #    ******************************************************************************
    #    * This code ported from GDALInvGeoTransform() in gdaltransformer.cpp
    #    * as it isn't exposed in the python SWIG bindings until GDAL 1.7
    #    * copyright & permission notices included below as per conditions.
    #
    #    ******************************************************************************
    #    * $Id: gdaltransformer.cpp 15024 2008-07-24 19:25:06Z rouault $
    #    *
    #    * Project:  Mapinfo Image Warper
    #    * Purpose:  Implementation of one or more GDALTrasformerFunc types, including
    #    *           the GenImgProj (general image reprojector) transformer.
    #    * Author:   Frank Warmerdam, warmerdam@pobox.com
    #    *
    #    ******************************************************************************
    #    * Copyright (c) 2002, i3 - information integration and imaging
    #    *                          Fort Collin, CO
    #    *
    #    * Permission is hereby granted, free of charge, to any person obtaining a
    #    * copy of this software and associated documentation files (the "Software"),
    #    * to deal in the Software without restriction, including without limitation
    #    * the rights to use, copy, modify, merge, publish, distribute, sublicense,
    #    * and/or sell copies of the Software, and to permit persons to whom the
    #    * Software is furnished to do so, subject to the following conditions:
    #    *
    #    * The above copyright notice and this permission notice shall be included
    #    * in all copies or substantial portions of the Software.
    #    *
    #    * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
    #    * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    #    * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
    #    * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    #    * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    #    * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    #    * DEALINGS IN THE SOFTWARE.
    #    ****************************************************************************

    # we assume a 3rd row that is [1 0 0]

    # Compute determinate
    det = gt_in[1] * gt_in[5] - gt_in[2] * gt_in[4]

    if( abs(det) < 0.000000000000001 ):
        return

    inv_det = 1.0 / det

    # compute adjoint, and divide by determinate
    gt_out = [0,0,0,0,0,0]
    gt_out[1] =  gt_in[5] * inv_det
    gt_out[4] = -gt_in[4] * inv_det

    gt_out[2] = -gt_in[2] * inv_det
    gt_out[5] =  gt_in[1] * inv_det

    gt_out[0] = ( gt_in[2] * gt_in[3] - gt_in[0] * gt_in[5]) * inv_det
    gt_out[3] = (-gt_in[1] * gt_in[3] + gt_in[0] * gt_in[4]) * inv_det

    return gt_out


def ApplyGeoTransform(inx,iny,gt):
    ''' Apply a geotransform
        @param  inx:       Input x coordinate (double)
        @param  iny:       Input y coordinate (double)
        @param  gt:        Input geotransform (six doubles)

        @return: outx,outy Output coordinates (two doubles)
    '''
    outx = gt[0] + inx*gt[1] + iny*gt[2]
    outy = gt[3] + inx*gt[4] + iny*gt[5]
    return (outx,outy)


def MapToPixel(mx,my,gt):
    ''' Convert map to pixel coordinates
        @param  mx:    Input map x coordinate (double)
        @param  my:    Input map y coordinate (double)
        @param  gt:    Input geotransform (six doubles)
        @return: px,py Output coordinates (two ints)

        @change: changed int(p[x,y]+0.5) to int(p[x,y]) as per http://lists.osgeo.org/pipermail/gdal-dev/2010-June/024956.html
        @change: return floats
        @note:   0,0 is UL corner of UL pixel, 0.5,0.5 is centre of UL pixel
    '''
    if gt[2]+gt[4]==0: #Simple calc, no inversion required
        px = (mx - gt[0]) / gt[1]
        py = (my - gt[3]) / gt[5]
    else:
        px,py=ApplyGeoTransform(mx,my,InvGeoTransform(gt))
    #return int(px),int(py)
    return px,py

if __name__ == '__main__':
    ds = gdal.Open('/mnt/auxdrive/mxmcc/charts/noaa/BSB_ROOT/11411/11411_1.KAP', gdal.GA_ReadOnly)
    print dataset_lat_lng_bounds(ds)

# if __name__ == '__main__':
#     import tilesystem as ts
#     # Upper Left  ( -115365.105, 3231585.148) ( 83d 2'10.83"W, 27d51'43.17"N)
#     # Lower Left  ( -115365.105, 3165502.094) ( 83d 2'10.83"W, 27d20' 9.27"N)
#     # Upper Right (  -65697.559, 3231585.148) ( 82d35'24.62"W, 27d51'43.17"N)
#     # Lower Right (  -65697.559, 3165502.094) ( 82d35'24.62"W, 27d20' 9.27"N)
#     # Center      (  -90531.332, 3198543.621) ( 82d48'47.72"W, 27d35'57.36"N)
#
#     ds = gdal.Open('/mnt/auxdrive/mxmcc/charts/noaa/BSB_ROOT/11411/temp.vrt', gdal.GA_ReadOnly)
#     bands = ds.RasterCount
#
#     wnes, is_north_up = dataset_lat_lng_bounds(ds)
#     tile_min_x, tile_max_y, tile_max_x, tile_min_y, num_tiles_x, num_tiles_y = ts.lat_lng_bounds_to_tile_bounds_count(wnes, 15)
#     x = tile_min_x + (tile_max_x - tile_min_x) / 2
#     y = tile_max_y + (tile_max_y - tile_min_y) / 2
#     px, py = ts.tile_xy_to_pixel_xy(x, y)  # top left
#     mx, my = ts.pixels_to_meters(px, py, 15)
#
#     gt = ds.GetGeoTransform()
#     xoff, yoff =  MapToPixel(mx, my, gt)
#     # #todo: convert meters to map pixels
#     xoff = 5000
#     yoff = 7000
#     data = ds.ReadRaster(int(xoff), int(yoff), ts.tile_size, ts.tile_size, ts.tile_size, ts.tile_size)
#
#     gdal.AllRegister()
#     mem_driver = gdal.GetDriverByName('MEM')
#     png_driver = gdal.GetDriverByName('PNG')
#
#     tile_mem = mem_driver.Create('', ts.tile_size, ts.tile_size, bands=bands)
#     tile_mem.WriteRaster(0, 0, ts.tile_size, ts.tile_size, data, band_list=range(1, bands+1))
#     #TODO: process png image data with http://pngquant.org/lib/ before saving to disk
#     png_tile = png_driver.CreateCopy('/mnt/auxdrive/mxmcc/charts/noaa/BSB_ROOT/11411/out.png', tile_mem, strict=0)
