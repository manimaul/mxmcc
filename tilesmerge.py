#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Modified for mxmcc: Will Kamp
# Original source: https://code.google.com/p/tilers-tools/

###############################################################################
# Copyright (c) 2010, Vadim Shlyakhov
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
#******************************************************************************

from PIL import Image
import glob
import catalog
import config
import os
import pickle
import re
import shutil
import sys
import multiprocessing
from tilesystem import tile_size


def set_nothreads():
    global multiprocessing
    multiprocessing = None


def parallel_map(func, iterable):
    if multiprocessing is None or len(iterable) < 2:
        return map(func, iterable)
    else:
        # map in parallel
        mp_pool = multiprocessing.Pool()  # multiprocessing pool
        res = mp_pool.map(func, iterable)
        # wait for threads to finish
        mp_pool.close()
        mp_pool.join()
    return res


def re_sub_file(fname, subs_list):
    """stream edit file using reg exp substitution list"""
    new = fname + '.new'
    with open(new, 'w') as out:
        for l in open(fname, 'rU'):
            for (pattern, repl) in subs_list:
                l = re.sub(pattern, repl, string=l)
            out.write(l)
    shutil.move(new, fname)


class KeyboardInterruptError(Exception):
    pass


def transparency(img):
    """estimate transparency of an image"""
    (r, g, b, a) = img.split()
    (a_min, a_max) = a.getextrema()  # get min/max values for alpha channel
    return 1 if a_min == 255 else 0 if a_max == 0 else -1


class MergeSet:
    def __init__(self, src_dir, dst_dir):
        (self.src, self.dest) = (src_dir, dst_dir)
        self.tile_sz = (tile_size, tile_size) #tuple(map(int, options.tile_size.split(',')))

        #if options.strip_src_ext:
        #    self.src = os.path.splitext(self.src)[0]
        #if options.add_src_ext is not None:
        #    self.src += options.add_src_ext
        try:
            cwd = os.getcwd()
            os.chdir(self.src)
            self.src_lst = glob.glob('[0-9]*/*/*.png')
            try:
                self.max_zoom = max([int(i) for i in glob.glob('[0-9]*')])
            except:
                print "there is a problem"
                print self.src
                sys.exit()
        finally:
            os.chdir(cwd)
            #ld(self.src_lst)

        # load cached tile transparency data if any
        self.src_transp = dict.fromkeys(self.src_lst, None)
        self.src_cache_path = os.path.join(self.src, 'merge-cache')
        try:
            self.src_transp.update(pickle.load(open(self.src_cache_path, 'r')))
        except:
            pass
            #ld("cache load failed")
        #ld(repr(self.src_transp))

        # define crop map for underlay function
        tsx, tsy = self.tile_sz
        self.underlay_map = [#    lf    up    rt    lw
                             (   0, 0, tsx / 2, tsy / 2), (tsx / 2, 0, tsx, tsy / 2),
                             (   0, tsy / 2, tsx / 2, tsy), (tsx / 2, tsy / 2, tsx, tsy),
        ]

        # do the thing
        self.merge_dirs()

    def __call__(self, tile):
        """called by map() to merge a source tile into the destination tile set"""
        try:
            src_path = os.path.join(self.src, tile)
            dst_tile = os.path.join(self.dest, tile)
            dpath = os.path.dirname(dst_tile)
            src_raster = None
            transp = self.src_transp[tile]
            if transp == None:  # transparency value not cached yet
                src_raster = Image.open(src_path).convert("RGBA")
                transp = transparency(src_raster)
            if transp != 0:  # fully transparent
                if not os.path.exists(dpath):
                    try:  # thread race safety
                        os.makedirs(dpath)
                    except os.error:
                        pass
                if transp == 1 or not os.path.exists(dst_tile):
                    # fully opaque or no destination tile exists yet
                    shutil.copy(src_path, dst_tile)
                else:  # semitransparent, combine with destination (exists! see above)
                    if not src_raster:
                        src_raster = Image.open(src_path).convert("RGBA")
                    dst_raster = Image.composite(src_raster, Image.open(dst_tile).convert("RGBA"), src_raster)
                    dst_raster.save(dst_tile)
                #if options.underlay and transp != 0:
                #    self.underlay(tile, src_path, src_raster, options.underlay)
        except KeyboardInterrupt: # http://jessenoller.com/2009/01/08/multiprocessingpool-and-keyboardinterrupt/
            print 'got KeyboardInterrupt'
            raise KeyboardInterruptError()
        return (tile, transp) # send back transparency values for caching

    def upd_stat(self, transparency_data):
        self.src_transp.update(dict(transparency_data))
        try:
            pickle.dump(self.src_transp, open(self.src_cache_path, 'w'))
        except:
            pass
            #ld("cache save failed")
            #pf('')

    def merge_dirs(self):
        src_transparency = parallel_map(self, self.src_lst)
        self.upd_stat(src_transparency)

# MergeSet end


def merge_list(name, tile_dir_list, nothreads=False):
    """merge a list of XZY tiled map directories into a single directory
       name - output directory will be the directory defined in config.py + name
       tile_dir_list - list of input ZXY tiled map directories
       nothreads - set to true if you don't want multiprocessing

       note: tile_dir_list should be sorted by map scale descending so that larger scale
       map tiles (that are close in scale and the same zoom level as another intersecting
       map) get priority

       note: tiles with transparency will be combined if possible with data from another tile
    """
    if nothreads:
        set_nothreads()

    merge_dir = os.path.join(config.merged_tile_dir, name)

    if not os.path.isdir(merge_dir):
        os.makedirs(merge_dir)
    else:
        shutil.rmtree(merge_dir, ignore_errors=True)

    for tile_dir in tile_dir_list:
        if os.path.isdir(tile_dir):
            MergeSet(tile_dir, merge_dir)
        else:
            raise Exception('map %s is missing from tiles list', os.path.basename(tile_dir))


def merge_catalog(catalog_name, nothreads=False):
    """merge a catalog of XZY tiled map directories into a single directory
       catalog_name - name of catalog to merge, also the name of the ouput directory
       to be created in congig.merged_tile_dir
       nothreads - set to true if you don't want multiprocessing
    """

    if nothreads:
        set_nothreads()

    reader = catalog.get_reader_for_region(catalog_name)
    merge_dir = os.path.join(config.merged_tile_dir, catalog_name)

    if not os.path.isdir(merge_dir):
        os.makedirs(merge_dir)
    else:
        shutil.rmtree(merge_dir, ignore_errors=True)

    unmerged_tile_dir = None

    #find unmerged dir
    for ea in os.listdir(config.unmerged_tile_dir):
        if ea.upper() == catalog_name.upper():
            unmerged_tile_dir = os.path.join(config.unmerged_tile_dir, ea)
            break

    if unmerged_tile_dir is None:
        raise Exception('%s is not in unmerged tiles directory' % catalog_name)

    for entry in reader:
        map_name = os.path.basename(entry['path'])
        map_name = map_name[0:map_name.find('.')]
        tile_dir = os.path.join(unmerged_tile_dir, map_name)
        if os.path.isdir(tile_dir):
            MergeSet(tile_dir, merge_dir)
        else:
            raise Exception('map %s missing from tiles' % map_name)