#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''This will find the optimal zoom level  on a zxy tiled map for a BSB chart.
   The calculated zoom accounts and compensates for latitude distortion of scales.
'''

import math

from shapely.geometry import Point
from pyproj import Proj


def haversine_distance(origin, destination):
    lon1, lat1 = origin
    lon2, lat2 = destination
    radius = 6371  # kilometers
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c
    return d * 1000  # meters


def cartesian_distance(origin, destination):
    lon1, lat1 = origin
    lon2, lat2 = destination
    proj = Proj(init="epsg:3785")  # spherical mercator, should work anywhere
    point1 = proj(lon1, lat1)
    point2 = proj(lon2, lat2)
    point1_cart = Point(point1)
    point2_cart = Point(point2)
    return point1_cart.distance(point2_cart)  # meters


def latitude_distortion(latitude):
    origin = (0, latitude)
    destination = (1, latitude)
    hdist = haversine_distance(origin, destination)
    cdist = cartesian_distance(origin, destination)
    return cdist/hdist


def get_zoom(scale, latitude):
    true_scale = scale * latitude_distortion(latitude)
    return get_zoom_from_true_scale(true_scale)


def get_zoom_from_true_scale(true_scale):
    t = 30
    # tweak_percent = .87
    tweak_percent = .70
    tweak_scale = true_scale * tweak_percent
    while tweak_scale > 1:
        tweak_scale /= 2
        t -= 1
    return t
