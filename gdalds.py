#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

import osr

'''some convenience methods for information about gdal data sets
'''


def dataset_has_color_palette(gdal_ds):
    """returns true of false wether a gdal dataset has a color palette
    """
    return gdal_ds.GetRasterBand(1).GetRasterColorTable() is not None


def dataset_lat_lng_bounds(gdal_ds):
    """returns the bounding box of a gdal dataset in latitude,longitude WGS-84 coordinates (in decimal degrees)
       bounding box returned as: min_lng, min_lat, max_lng, max_lat
    """

    geotransform = gdal_ds.GetGeoTransform()

    #useful information about geotransform
    #geotransform[0] #top left X
    #geotransform[1] #w-e pixel resolution
    #geotransform[2] #rotation, 0 if image is "north up"
    #geotransform[3] #top left Y
    #geotransform[4] #rotation, 0 if image is "north up"
    #geotransform[5] n-s pixel resolution

    dataset_bbox_cells = (
        (0., 0.),
        (0, gdal_ds.RasterYSize),
        (gdal_ds.RasterXSize, gdal_ds.RasterYSize),
        (gdal_ds.RasterXSize, 0),
    )

    geo_pts = []  # upper left, lower left, lower right, upper right

    for x, y in dataset_bbox_cells:
        xx = geotransform[0] + geotransform[1] * x + geotransform[2] * y
        yy = geotransform[3] + geotransform[4] * x + geotransform[5] * y
        geo_pts.append((xx, yy))

    northwest, southwest, southeast, northeast = geo_pts
    north = max(northwest[1], northeast[1])
    east = max(southeast[0], northeast[0])
    south = min(southwest[1], southeast[1])
    west = min(southwest[0], northwest[0])

    wgs84_wkt = """
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"]]"""
    geo_srs = osr.SpatialReference()
    geo_srs.ImportFromWkt(wgs84_wkt)

    org_srs = osr.SpatialReference(gdal_ds.GetProjectionRef())
    transform = osr.CoordinateTransformation(org_srs, geo_srs)

    max_lng, max_lat = transform.TransformPoint(east, north)[:2]
    min_lng, min_lat = transform.TransformPoint(west, south)[:2]

    return min_lng, min_lat, max_lng, max_lat