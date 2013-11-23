#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Description of what this does.'''

import numpy
import globalmercator
from osgeo import gdal
import osr
import findzoom


def vrt_tiles_info(input_file, tilesize=256, dpi=None, scale=None, verbose=False):
    dataset = gdal.Open(input_file, gdal.GA_ReadOnly)

    #if the dataset is vrt continue
    if dataset.GetDriver().ShortName != "VRT":
        print "dataset is not VRT!"
        return

    if dataset is None:
        print "dataset cannot be read!"
        return

    if dataset.GetRasterBand(1).GetRasterColorTable() != None:
        print "dataset has palette!"
        return

    geotransform = dataset.GetGeoTransform()
    projection = dataset.GetProjectionRef()

    #useful information about geotransform
    #geotransform[0] #top left X
    #geotransform[1] #w-e pixel resolution
    #geotransform[2] #rotation, 0 if image is "north up"
    #geotransform[3] #top left Y
    #geotransform[4] #rotation, 0 if image is "north up"
    #geotransform[5] n-s pixel resolution

    if geotransform[2] != 0 or geotransform[4] != 0:
        print "dataset is not North Up!"
        return

    pixresew = geotransform[1]  # meters per pixel east to west
    pixresns = geotransform[5]  # meters per pixel north to south

    dataset_srs = osr.SpatialReference(projection)
    geo_srs = dataset_srs.CloneGeogCS()
    transform = osr.CoordinateTransformation(dataset_srs, geo_srs)

    dataset_bbox_cells = (
        (0., 0.),
        (0, dataset.RasterYSize),
        (dataset.RasterXSize, dataset.RasterYSize),
        (dataset.RasterXSize, 0),
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

    max_lng, max_lat = transform.TransformPoint(east, north)[:2]
    min_lng, min_lat = transform.TransformPoint(west, south)[:2]
    ctr_lat = min_lat + (max_lat - min_lat) / 2

    mercator = globalmercator.GlobalMercator(tilesize)

    diagonal_meters_haversine = findzoom.haversine_distance((max_lng, max_lat), (min_lng, min_lat))
    diagonal_meters_cartesian = findzoom.cartesian_distance((max_lng, max_lat), (min_lng, min_lat))
    distortion_avg = diagonal_meters_cartesian / diagonal_meters_haversine
    distortion_ctr = findzoom.latitude_distortion(ctr_lat)

    if dpi != None:
        #actual size if printed out at specified dpi
        diag_inches = numpy.sqrt(dataset.RasterXSize**2 + dataset.RasterYSize**2) / float(dpi)
    else:
        diag_inches = None

    #set the zoom level preferably by scale, next by dpi, and lastly by pixel size
    if scale != None:
        zoom = 30
        tweakPercent = .70
        truescale = scale * distortion_ctr
        tscale = truescale * tweakPercent
        while tscale > 1:
            tscale = tscale / 2
            zoom -= 1
    elif dpi != None:
        zoom = 30;
        truescale = (diagonal_meters_haversine) / (diag_inches / globalmercator.INCHES_PER_METER)
        scale = truescale * distortion_avg
        tscale = truescale
        while tscale > 1:
            tscale = tscale / 2
            zoom -= 1
    else:
        zoom = mercator.ZoomForPixelSize(abs(pixresew))

    #generate min max tile coordinates for zoomlevel
    tminx, tminy = mercator.MetersToTile( west, south, zoom )
    tmaxx, tmaxy = mercator.MetersToTile( east, north, zoom )
    # crop tiles extending world limits (+-180,+-90)
    tminx, tminy = max(0, tminx), max(0, tminy)
    tmaxx, tmaxy = min(2**zoom-1, tmaxx), min(2**zoom-1, tmaxy)

    if verbose:
        print "=" * 80
        print "input file:", input_file
        print "driver:", dataset.GetDriver().ShortName
        print "max latitude:", max_lat
        print "max longitude:", max_lng
        print "min latitude:", min_lat
        print "min longitude:", min_lng
        print "scale:", scale
        print "meters per pixel east - west: ", pixresew
        print "meters per pixel north - south:", pixresns
        print "meters accross:", east - west
        print "print diagonal inches:", diag_inches
        print "haversine meters diagonal:", diagonal_meters_haversine
        print "cartesian meters diagonal:", diagonal_meters_cartesian
        print "mercator distortion average:", distortion_avg
        print "mercator distortion map center latitude:", distortion_ctr
        print "size Pixels:", dataset.RasterXSize, "x", dataset.RasterYSize, "x(bands)", dataset.RasterCount
        print "projection:", projection
        print "north, south, east, west: ", (north, south, east, west)
        print "tile zoom:", zoom
        print "tile min X:", tminx
        print "tile max X:", tmaxx
        print "tile min Y:", tminy
        print "tile max Y:", tmaxy
        print "=" * 80

    return zoom