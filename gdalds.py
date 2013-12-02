#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

from osgeo import gdal
import osr

'''some convenience methods for information about gdal data sets
'''


def dataset_get_cutline_in_srs_wkt_geometry(gdal_ds, cutline):
    """return a cutline in WKT geometry with coordinates expressed in dataset source pixel/line coordinates.

       cutline string format example: 48.3,-123.2:48.5,-123.2:48.5,-122.7:48.3,-122.7:48.3,-123.2
       : dilineated latitude/longitude WGS-84 coordinates (in decimal degrees)
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

    for latlng in cutline.split(':'):
        lat, lng = latlng.split(',')
        geo_x, geo_y = transform.TransformPoint(float(lng), float(lat))[:2]
        px = int(inv_geotransform[0] + inv_geotransform[1] * geo_x + inv_geotransform[2] * geo_y)
        py = int(inv_geotransform[3] + inv_geotransform[4] * geo_x + inv_geotransform[5] * geo_y)
        polygon_wkt += '%d %d,' % (px, py)

    return polygon_wkt[:-1] + '))'


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

    #min_lng, max_lat, max_lng, min_lat
    return west, north, east, south

#if __name__ == '__main__':
#    import tilesystem
#    import gpxrte
#    map_path = '/Volumes/USB-DATA/mxmcc/charts/noaa/Test/18423_3.kap'
#    ds = gdal.Open(map_path, gdal.GA_ReadOnly)
#    bounds = dataset_lat_lng_bounds(ds)
#    min_lng, max_lat, max_lng, min_lat = bounds
#    gpxrte.export_bounds(bounds, '/Volumes/USB-DATA/mxmcc/charts/noaa/Test/test.gpx')
#    print bounds
#    print tilesystem.lat_lng_bounds_to_tile_bounds_count(bounds, 15)