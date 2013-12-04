#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''bearing and intersection methods between latitude / longitude points and lines
'''

import numpy


def crosses_dateline(lng1_d, lng2_d):
    sm = min(lng1_d, lng2_d)
    lg = max(lng1_d, lng2_d)
    return sm < -90 and lg > 90


def degree_to_radian(deg):
    return deg * numpy.pi / 180.


def radian_to_degree(rad):
    return rad * 180. / numpy.pi


def bearing(lat1_d, lng1_d, lat2_d, lng2_d):
    """returns the initial bearing from 1 latitude/longitude point to another
       see http://williams.best.vwh.net/avform.htm#Crs
       see see http://www.movable-type.co.uk/scripts/latlong.html
       lat1_d, lng1_d - latitude, longitude in degrees of point 1
       lat2_d, lng2_d - latitude, longitude in degrees of point 2
    """
    lat1 = degree_to_radian(lat1_d)
    lat2 = degree_to_radian(lat2_d)
    lng = degree_to_radian(lng2_d - lng1_d)
    y = numpy.sin(lng) * numpy.cos(lat2)
    x = numpy.cos(lat1) * numpy.sin(lat2) - \
        numpy.sin(lat1) * numpy.cos(lat2) * numpy.cos(lng)
    brng = numpy.arctan2(y, x)
    return (radian_to_degree(brng) + 360) % 360


def intersection2(lat1_d, lng1_d, lat2_d, lng2_d, lat3_d, lng3_d, lat4_d, lng4_d):
    """returns the point of intersection of two paths defined by lines
       see http://williams.best.vwh.net/avform.htm#Intersection
       see http://www.movable-type.co.uk/scripts/latlong.html
       lat1_d, lng1_d - latitude, longitude in degrees of line 1, point 1
       lat2_d, lng2_d - latitude, longitude in degrees of line 1, point
       lat3_d, lng3_d - latitude, longitude in degrees of line 2, point 1
       lat4_d, lng4_d - latitude, longitude in degrees of line 2, point 2
    """
    brng1 = bearing(lat1_d, lng1_d, lat2_d, lng2_d)
    brng2 = bearing(lat3_d, lng3_d, lat4_d, lng4_d)
    return intersection(lat1_d, lng1_d, brng1, lat3_d, lng3_d, brng2)


def intersection(lat1_d, lng1_d, brng1, lat2_d, lng2_d, brng2):
    """returns the point of intersection of two paths defined by point and bearing
       see http://williams.best.vwh.net/avform.htm#Intersection
       see http://www.movable-type.co.uk/scripts/latlong.html
       lat1_d, lng1_d - latitude, longitude in degrees of point 1
       brng1 - bearing of point 1 in degrees
       lat2_d, lng2_d - latitude, longitude in degrees of point 2
       brng2 - bearing of point 2 in degrees
    """
    lat1 = degree_to_radian(lat1_d)
    lng1 = degree_to_radian(lng1_d)
    lat2 = degree_to_radian(lat2_d)
    lng2 = degree_to_radian(lng2_d)
    brng13 = degree_to_radian(brng1)
    brng23 = degree_to_radian(brng2)
    d_lat = lat2 - lat1
    d_lng = lng2 - lng1
    dist12 = 2 * numpy.arcsin(numpy.sqrt(numpy.sin(d_lat/2) * numpy.sin(d_lat/2) +
             numpy.cos(lat1) * numpy.cos(lat2)*numpy.sin(d_lng/2) * numpy.sin(d_lng/2)))

    if dist12 is 0:
        return None

    brng_a = numpy.arccos((numpy.sin(lat2) - numpy.sin(lat1) * numpy.cos(dist12)) /
                          (numpy.sin(dist12) * numpy.cos(lat1)))
    if brng_a is None:
        brng_a = 0

    brng_b = numpy.arccos((numpy.sin(lat1) - numpy.sin(lat2) * numpy.cos(dist12)) /
                          (numpy.sin(dist12) * numpy.cos(lat2)))

    if numpy.sin(lng2 - lng1) > 0:
        brng12 = brng_a
        brng21 = 2 * numpy.pi - brng_b
    else:
        brng12 = 2 * numpy.pi - brng_a
        brng21 = brng_b

    alpha1 = (brng13 - brng12 + numpy.pi) % (2 * numpy.pi) - numpy.pi
    alpha2 = (brng21 - brng23 + numpy.pi) % (2 * numpy.pi) - numpy.pi

    if numpy.sin(alpha1) is 0 and numpy.sin(alpha2) is 0:
        return None

    if numpy.sin(alpha1) * numpy.sin(alpha2) < 0:
        return None

    #Ed Williams takes abs of alpha1/alpha2, but seems to break calculation?
    alpha3 = numpy.arccos(-numpy.cos(alpha1) * numpy.cos(alpha2) +
                           numpy.sin(alpha1) * numpy.sin(alpha2) * numpy.cos(dist12))
    dist13 = numpy.arctan2(numpy.sin(dist12) * numpy.sin(alpha1) * numpy.sin(alpha2),
                           numpy.cos(alpha2) + numpy.cos(alpha1) * numpy.cos(alpha3))
    lat3 = numpy.arcsin(numpy.sin(lat1) * numpy.cos(dist13) +
                        numpy.cos(lat1) * numpy.sin(dist13) * numpy.cos(brng13))
    d_lng13 = numpy.arctan2(numpy.sin(brng13) * numpy.sin(dist13) * numpy.cos(lat1),
                           numpy.cos(dist13) - numpy.sin(lat1) * numpy.sin(lat3))
    lng3 = lng1 + d_lng13
    lng3 = (lng3 + 3 * numpy.pi) % (2 * numpy.pi) - numpy.pi

    return radian_to_degree(lat3), radian_to_degree(lng3)