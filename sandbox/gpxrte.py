#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''description of file
'''

template = '''<?xml version="1.0"?>
<gpx version="1.1" creator="mxmcc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" xmlns:mxmariner="http://www.mxmariner.com">
  <rte>
    %s
  </rte>
</gpx>'''

point = '<rtept lat="%f" lon="%f"></rtept>\n'


def export_bounds(bounds, gpx_path):
    min_lng, max_lat, max_lng, min_lat = bounds
    points = ''
    points += point % (max_lat, min_lng)
    points += point % (max_lat, max_lng)
    points += point % (min_lat, max_lng)
    points += point % (min_lat, min_lng)
    gpx_txt = template % points
    gpx_f = open(gpx_path, 'w')
    gpx_f.write(gpx_txt)
