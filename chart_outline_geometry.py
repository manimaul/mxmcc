#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2017, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''
Extracts a chart outline string into a Geometry
'''

import shapely.geometry as geo

SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   version="1.1"
   id="svg2"
   viewBox="-180 -90 360 180">
  <defs
     id="defs4" />
  <metadata
     id="metadata7">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title></dc:title>
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     id="layer1">
    {}
  </g>
</svg>
"""

_west_hemi = geo.Polygon(shell=geo.LinearRing([(-180, 90), (0, 90), (0, -90), (-180, -90), (-180, 90)]))
_east_hemi = geo.Polygon(shell=geo.LinearRing([(180, 90), (0, 90), (0, -90), (180, -90), (180, 90)]))


def _outline_str_to_coordinates(outline_str):
    coords = []
    for lat_lng_str in outline_str.split(':'):
        lat_str, lng_str = lat_lng_str.split(',')
        lng = float(lng_str)
        lat = float(lat_str)
        coords.append((lng, lat))
    return coords


def _split_hemisphere_coordinates(coords):
    projected_west_coords = []
    projected_east_coords = []
    for lng, lat in coords:
        if lng > 0:
            p_lng = -360 + lng
            projected_east_coords.append((lng, lat))
            projected_west_coords.append((p_lng, lat))
        elif lng < 0:
            p_lng = 360.0 - abs(lng)
            projected_east_coords.append((p_lng, lat))
            projected_west_coords.append((lng, lat))
        else:
            projected_east_coords.append((lng, lat))
            projected_west_coords.append((lng, lat))
    return geo.Polygon(shell=geo.LinearRing(projected_west_coords)).intersection(_west_hemi), \
           geo.Polygon(shell=geo.LinearRing(projected_east_coords)).intersection(_east_hemi)


class ChartOutline(object):
    def __init__(self, outline_str):
        coords = _outline_str_to_coordinates(outline_str)
        west, east = _split_hemisphere_coordinates(coords)
        if not west.is_empty and not east.is_empty:
            self._geometry = geo.MultiPolygon([west, east])
        elif not west.is_empty:
            self._geometry = west
        else:
            self._geometry = east

    @property
    def geometry(self):
        return self._geometry
