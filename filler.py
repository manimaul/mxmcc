#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2014, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Prototype"  # "Prototype", "Development", or "Production"

'''Fills the "holes" (transparent portions) in merged tiles using a 1 up, 6 down search pattern
'''

import os

from PIL import Image

from tilesystem import tile_size
from regions import is_valid_region
from search import MapPathSearch
import logger
import config


MAX_ZOOM_TIMES = 8
STD_ZOOM_TIMES = 6


def fill_all_in_region(region):
    for ea in get_tile_list(region):
        mt = MapTile(*get_tile(ea))
        mt.fill_if_necessary()


def get_tile(abs_path):
    z = -1
    x = -1
    y = -1
    stack = abs_path.split('/')
    while z == -1 or x == -1 or y == -1:
        if len(stack) == 0:
            break
        item = stack.pop()
        if y == -1:
            y = int(item[:-4])
        elif x == -1:
            x = int(item)
        elif z == -1:
            z = int(item)

    tile_dir = os.path.join('/', *stack)
    return z, x, y, tile_dir


def get_tile_list(region):
    region = region.upper()
    if is_valid_region(region):
        tile_dir = os.path.join(config.merged_tile_dir, region)
        png_ps = MapPathSearch(tile_dir, ['png'])
        return png_ps.file_paths

    return []


def _has_transparency(img):
    r, g, b, a = img.split()
    a_min, a_max = a.getextrema()
    return a_min == 0 or a_max == 0


def _stack_images(top_img, bottom_img):
    if top_img is None and bottom_img is not None:
        return bottom_img

    if bottom_img is None and top_img is not None:
        return top_img

    return Image.composite(top_img, bottom_img, top_img)


# noinspection PyProtectedMember
def _stack_overzoom_images(map_tile, top_img, zoom_times):
    btm_img = map_tile._find_over_zoom_tile_img(STD_ZOOM_TIMES, zoom_times)
    if btm_img is not None:
        return _stack_images(top_img, btm_img)
    return top_img


# noinspection PyProtectedMember
class MapTile:
    def __init__(self, z, x, y, tile_dir):
        self.tile_dir = tile_dir
        self.image = None
        self.z = int(z)
        self.x = int(x)
        self.y = int(y)

    def fill_if_necessary(self):
        if self.has_transparency():
            abs_path = self.get_path()
            logger.log(logger.OFF, 'filling: ' + abs_path)
            self.get_image().save(abs_path)
    
    def get_image(self):
        if self.has_transparency():
            bottom = self._find_zoom_tile_img(STD_ZOOM_TIMES, 1)
            if bottom is not None:
                self.image = _stack_images(self._get_image(), bottom)

        return self._get_image()

    def get_path(self):
        return os.path.join(self.tile_dir, str(self.z), str(self.x), str(self.y) + '.png')

    def exists(self):
        return os.path.exists(self.get_path())

    def get_zxy(self):
        return self.z, self.x, self.y

    def has_transparency(self):
        if not self.exists():
            return False

        return _has_transparency(self._get_image())

    def _get_image(self):
        if self.image is None:
            self.image = Image.open(self.get_path(), 'r').convert("RGBA")

        return self.image

    def _find_zoom_tile_img(self, max_upper_zoom, zoom_times):
        uz_img = self._find_under_zoom_tile_img()
        if uz_img is not None:
            logger.log(logger.OFF, 'uz_image found')
            if not _has_transparency(uz_img):
                return uz_img
            else:
                oz_img = self._find_over_zoom_tile_img(max_upper_zoom, zoom_times)
                return _stack_images(uz_img, oz_img)

        logger.log(logger.OFF, 'uz_image not found')
        return self._find_over_zoom_tile_img(max_upper_zoom, zoom_times)

    def _find_over_zoom_tile_img(self, max_upper_zoom, zoom_times):
        logger.log(logger.OFF, '_find_over_zoom_tile_img zoom_times %d' % zoom_times)
        if zoom_times >= MAX_ZOOM_TIMES:
            logger.log(logger.OFF, 'exceeded 8 times limit')
            return

        upper_zoom = self.z - zoom_times
        diff = abs(self.z - upper_zoom)
        m_tile_size = tile_size >> diff
        logger.log(logger.OFF, '_find_over_zoom_tile_img m_tile_size %d' % m_tile_size)
        upper_tile = MapTile(upper_zoom, self.x >> diff, self.y >> diff, self.tile_dir)
        if upper_tile.exists():
            img = upper_tile._get_image().copy()
            xx = (self.x % (1 << diff)) * m_tile_size
            yy = (self.y % (1 << diff)) * m_tile_size
            #left, upper, right, lower
            img = img.crop((xx, yy, xx + m_tile_size, yy + m_tile_size)) \
                     .resize((tile_size, tile_size), Image.NEAREST)
            if _has_transparency(img):
                _stack_overzoom_images(self, img, zoom_times + 1)
            else:
                return img
        elif upper_tile.z >= max_upper_zoom:
            return self._find_over_zoom_tile_img(max_upper_zoom, zoom_times + 1)

        #return self._get_image()

    def _find_under_zoom_tile_img(self):
        have_scale_tile = False
        zoom_in_level = self.z + 1
        diff = abs(self.z - zoom_in_level)
        m_tile_size = tile_size >> diff
        xx = self.x << diff
        yy = self.y << diff
        num_tiles = 1 << diff
        in_tile_paths = []
        for xi in range(num_tiles):
            for yi in range(num_tiles):
                lower_x = xx + xi
                lower_y = yy + yi
                p = os.path.join(self.tile_dir, '%s/%s/%s.png' % (zoom_in_level, lower_x, lower_y))
                if os.path.isfile(p):
                    in_tile_paths.append(p)
                    have_scale_tile = True
                else:
                    in_tile_paths.append(None)

        if have_scale_tile:
            im = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
            i = 0
            xoff = 0
            yoff = 0
            for in_tile_path in in_tile_paths:
                if i == 1:
                    yoff += m_tile_size
                if i == 2:
                    yoff -= m_tile_size
                    xoff += m_tile_size
                if i == 3:
                    yoff += m_tile_size
                if in_tile_path is not None:
                    im.paste(Image.open(in_tile_path).resize((m_tile_size, m_tile_size), Image.ANTIALIAS), (xoff, yoff))
                i += 1

            return im

if __name__ == '__main__':
    # mt = MapTile(10, 152, 365, '/media/aux-drive 180G/mxmcc/tiles/merged/REGION_15/')
    # _has_transparency(mt._get_image())
    fill_all_in_region('region_15')