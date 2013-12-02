#!/usr/bin/env python
#
###############################################################################
# Copyright (c) 2008, Klokan Petr Pridal
# 
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
# 
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
# 
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
###############################################################################

import numpy

MAXZOOMLEVEL = 19
INCHES_PER_METER = 39.3701


class GlobalMercator:
    """
    TMS Global Mercator Profile
    ---------------------------

    Functions necessary for generation of tiles in Spherical Mercator projection,
    EPSG:900913 (EPSG:gOOglE, Google Maps Global Mercator), EPSG:3785, OSGEO:41001.

    Such tiles are compatible with Google Maps, Microsoft Virtual Earth, Yahoo Maps,
    UK Ordnance Survey OpenSpace API, ...
    and you can overlay them on top of base maps of those web mapping applications.

    Pixel and tile coordinates are in TMS notation (origin [0,0] in bottom-left).

    What coordinate conversions do we need for TMS Global Mercator tiles::

         LatLon      <->       Meters      <->     Pixels    <->       Tile

     WGS84 coordinates   Spherical Mercator  Pixels in pyramid  Tiles in pyramid
         lat/lon            XY in metres     XY pixels Z zoom      XYZ from TMS
        EPSG:4326           EPSG:900913
         .----.              ---------               --                TMS
        /      \     <->     |       |     <->     /----/    <->      Google
        \      /             |       |           /--------/          quad_tree
         -----               ---------         /------------/
       KML, public         WebMapService         Web Clients      TileMapService

    What is the coordinate extent of Earth in EPSG:900913?

      [-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244]
      Constant 20037508.342789244 comes from the circumference of the Earth in meters,
      which is 40 thousand kilometers, the coordinate origin is in the middle of extent.
      In fact you can calculate the constant as: 2 * math.pi * 6378137 / 2.0
      $ echo 180 85 | gdaltransform -s_srs EPSG:4326 -t_srs EPSG:900913
      Polar areas with abs(latitude) bigger then 85.05112878 are clipped off.

    What are zoom level constants (pixels/meter) for pyramid with EPSG:900913?

      whole region is on top of pyramid (zoom=0) covered by 256x256 pixels tile,
      every lower zoom level resolution is always divided by two
      initial_resolution = 20037508.342789244 * 2 / 256 = 156543.03392804062

    What is the difference between TMS and Google Maps/quad_tree tile name convention?

      The tile raster itself is the same (equal extent, projection, pixel size),
      there is just different identification of the same raster tile.
      Tiles in TMS are counted from [0,0] in the bottom-left corner, id is XYZ.
      Google placed the origin [0,0] to the top-left corner, reference is XYZ.
      Microsoft is referencing tiles by a quad_tree name, defined on the website:
      http://msdn2.microsoft.com/en-us/library/bb259689.aspx

    The lat/lon coordinates are using WGS84 datum, yeh?

      Yes, all lat/lon we are mentioning should use WGS84 Geodetic Datum.
      Well, the web clients like Google Maps are projecting those coordinates by
      Spherical Mercator, so in fact lat/lon coordinates on sphere are treated as if
      the were on the WGS84 ellipsoid.

      From MSDN documentation:
      To simplify the calculations, we use the spherical form of projection, not
      the ellipsoidal form. Since the projection is used only for map display,
      and not for displaying numeric coordinates, we don"t need the extra precision
      of an ellipsoidal projection. The spherical projection causes approximately
      0.33 percent scale distortion in the Y direction, which is not visually noticable.

    How do I create a raster in EPSG:900913 and convert coordinates with PROJ.4?

      You can use standard GIS tools like gdalwarp, cs2cs or gdaltransform.
      All of the tools supports -t_srs "epsg:900913".

      For other GIS programs check the exact definition of the projection:
      More info at http://spatialreference.org/ref/user/google-projection/
      The same projection is degined as EPSG:3785. WKT definition is in the official
      EPSG database.

      Proj4 Text:
        +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0
        +k=1.0 +units=m +nadgrids=@null +no_defs

      Human readable WKT format of EPGS:900913:
         PROJCS["Google Maps Global Mercator",
             GEOGCS["WGS 84",
                 DATUM["WGS_1984",
                     SPHEROID["WGS 84",6378137,298.257223563,
                         AUTHORITY["EPSG","7030"]],
                     AUTHORITY["EPSG","6326"]],
                 PRIMEM["Greenwich",0],
                 UNIT["degree",0.0174532925199433],
                 AUTHORITY["EPSG","4326"]],
             PROJECTION["Mercator_1SP"],
             PARAMETER["central_meridian",0],
             PARAMETER["scale_factor",1],
             PARAMETER["false_easting",0],
             PARAMETER["false_northing",0],
             UNIT["metre",1,
                 AUTHORITY["EPSG","9001"]]]
    """

    def __init__(self, tile_size=256):
        """Initialize the TMS Global Mercator pyramid"""
        self.tile_size = tile_size
        self.initial_resolution = 2 * numpy.pi * 6378137 / self.tile_size
        # 156543.03392804062 for tile_size 256 pixels
        self.origin_shift = 2 * numpy.pi * 6378137 / 2.0
        # 20037508.342789244

    def lat_lng_to_meters(self, lat, lon):
        """Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913"""
        mx = lon * self.origin_shift / 180.0
        my = numpy.log(numpy.tan((90 + lat) * numpy.pi / 360.0)) / (numpy.pi / 180.0)

        my = my * self.origin_shift / 180.0
        return mx, my

    def meters_to_lat_lng(self, mx, my ):
        """Converts XY point from Spherical Mercator EPSG:900913 to lat/lon in WGS84 Datum"""
        lon = (mx / self.origin_shift) * 180.0
        lat = (my / self.origin_shift) * 180.0

        lat = 180 / numpy.pi * (2 * numpy.arctan(numpy.exp(lat * numpy.pi / 180.0)) - numpy.pi / 2.0)
        return lat, lon

    def pixels_to_meters(self, px, py, zoom):
        """Converts pixel coordinates in given zoom level of pyramid to EPSG:900913"""
        res = self.resolution(zoom)
        mx = px * res - self.origin_shift
        my = py * res - self.origin_shift
        return mx, my

    def meters_to_pixels(self, mx, my, zoom):
        """Converts EPSG:900913 to pyramid pixel coordinates in given zoom level"""
        res = self.resolution(zoom)
        px = (mx + self.origin_shift) / res
        py = (my + self.origin_shift) / res
        return px, py

    def pixels_to_tile(self, px, py):
        """Returns a tile covering region in given pixel coordinates"""
        tx = int(numpy.ceil(px / float(self.tile_size)) - 1)
        ty = int(numpy.ceil(py / float(self.tile_size)) - 1)
        return tx, ty

    def meters_to_tile(self, mx, my, zoom):
        """Returns tile for given mercator coordinates"""
        px, py = self.meters_to_pixels(mx, my, zoom)
        return self.pixels_to_tile(px, py)

    def tile_bounds(self, tx, ty, zoom):
        """Returns bounds of the given tile in EPSG:900913 coordinates"""
        minx, miny = self.pixels_to_meters(tx*self.tile_size, ty*self.tile_size, zoom)
        maxx, maxy = self.pixels_to_meters((tx+1)*self.tile_size, (ty+1)*self.tile_size, zoom)
        return minx, miny, maxx, maxy

    def tile_lat_lng_bounds(self, tx, ty, zoom ):
        """Returns bounds of the given tile in latutude/longitude using WGS84 datum"""
        bounds = self.tile_bounds(tx, ty, zoom)
        minLat, minLon = self.meters_to_lat_lng(bounds[0], bounds[1])
        maxLat, maxLon = self.meters_to_lat_lng(bounds[2], bounds[3])

        return minLat, minLon, maxLat, maxLon

    def resolution(self, zoom):
        """resolution (meters/pixel) for given zoom level (measured at Equator)"""
        #return (2 * numpy.pi * 6378137) / (self.tile_size * 2**zoom)
        return self.initial_resolution / (2**zoom)

    def zoom_for_pixel_size(self, pixel_size):
        """Maximal scale down zoom of the pyramid closest to the pixel_size."""
        for i in range(MAXZOOMLEVEL):
            if pixel_size > self.resolution(i):
                if i is not 0:
                    return i-1
                else:
                    return 0  # We don"t want to scale up

    def google_tile(self, tx, ty, zoom):
        """Converts TMS tile coordinates to Google Tile coordinates"""
        # coordinate origin is moved from bottom-left to top-left corner of the extent
        return tx, (2**zoom - 1) - ty

    def quad_tree(self, tx, ty, zoom):
        """Converts TMS tile coordinates to Microsoft QuadTree"""
        quad_key = ""
        ty = (2**zoom - 1) - ty
        for i in range(zoom, 0, -1):
            digit = 0
            mask = 1 << (i-1)
            if (tx & mask) != 0:
                digit += 1
            if (ty & mask) != 0:
                digit += 2
            quad_key += str(digit)

        return quad_key