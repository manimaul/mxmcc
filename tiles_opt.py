#!/usr/bin/env python

###############################################################################
# Copyright (c) 2010, Vadim Shlyakhov
#
# Permission is hereby granted, free of charge, to any person obtaining a
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

import re
import shutil
import logging
import itertools
import sys
import os
from .config import png_nq_binary
from subprocess import *
from .tilesystem import tile_size

from PIL import Image


tick_rate = 50
tick_count = 0

try:
    import multiprocessing  # available in python 2.6 and above

    class KeyboardInterruptError(Exception):
        pass
except:
    multiprocessing = None


def data_dir():
    return sys.path[0]


def set_nothreads():
    global multiprocessing
    multiprocessing = None


def parallel_map(func, iterable):
    if multiprocessing is None or len(iterable) < 2:
        return list(map(func, iterable))
    else:
        # map in parallel
        mp_pool = multiprocessing.Pool()  # multiprocessing pool
        res = mp_pool.map(func, iterable)
        # wait for threads to finish
        mp_pool.close()
        mp_pool.join()
    return res


def ld(*parms):
    logging.debug(' '.join(map(repr, parms)))


def ld_nothing(*parms):
    return


def pf(*parms, **kparms):
    end = kparms['end'] if 'end' in kparms else '\n'
    sys.stdout.write(' '.join(map(str, parms)) + end)
    sys.stdout.flush()


def pf_nothing(*parms, **kparms):
    return


def flatten(two_level_list):
    return list(itertools.chain(*two_level_list))

#try:
# import win32pipe
#except:
#    win32pipe=None
win32pipe = False


def if_set(x, default=None):
    return x if x is not None else default


def path2list(path):
    head, ext = os.path.splitext(path)
    split = [ext]
    while head:
        head, p = os.path.split(head)
        split.append(p)
    split.reverse()
    return split


def command(params, child_in=None):
    cmd_str = ' '.join(('"%s"' % i if ' ' in i else i for i in params))
    ld('>', cmd_str, child_in)
    process = Popen(params, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    (child_out, child_err) = process.communicate(child_in)
    if process.returncode != 0:
        raise Exception("*** External program failed: %s\n%s" % (cmd_str, child_err))
    ld('<', child_out, child_err)
    return child_out


def dest_path(src, dest_dir, ext='', template='%s'):
    src_dir, src_file = os.path.split(src)
    base, sext = os.path.splitext(src_file)
    dest = (template % base) + ext
    if not dest_dir:
        dest_dir = src_dir
    if dest_dir:
        dest = '%s/%s' % (dest_dir, dest)
    ld(base, dest)
    return dest


def re_sub_file(fname, subs_list):
    'stream edit file using reg exp substitution list'
    new = fname + '.new'
    with open(new, 'w') as out:
        for l in open(fname, 'rU'):
            for (pattern, repl) in subs_list:
                l = re.sub(pattern, repl, string=l)
            out.write(l)
    shutil.move(new, fname)


def counter():
    global tick_count
    tick_count += 1
    if tick_count % tick_rate == 0:
        pf('.', end='')
        return True
    else:
        return False


def optimize_png(src, dst, dpath):
    'optimize png using pngnq utility'
    png_tile = os.path.basename(src)
    if not png_tile.startswith('.'):
        command([png_nq_binary, '-s1', '-g2.2', '-n', str(tile_size), '-e', '.png', '-d', dpath, src])


def to_jpeg(src, dst, dpath):
    'convert to jpeg'
    dst_jpg = os.path.splitext(dst)[0] + '.jpg'
    img = Image.open(src)
    img.save(dst_jpg, optimize=True, quality=75)


class KeyboardInterruptError(Exception): pass


def proc_file(f):
    try:
        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f)
        dpath = os.path.split(dst)[0]
        if not os.path.exists(dpath):
            os.makedirs(dpath)
        if f.lower().endswith('.png'):
            optimize_png(src, dst, dpath)
        else:
            shutil.copy(src, dpath)
        counter()
    except KeyboardInterrupt:  # http://jessenoller.com/2009/01/08/multiprocessingpool-and-keyboardinterrupt/
        pf('got KeyboardInterrupt')
        raise KeyboardInterruptError()


def optimize_dir(directory):
    global src_dir
    global dst_dir
    src_dir = directory
    dst_dir = src_dir + '.opt'
    pf('%s -> %s ' % (src_dir, dst_dir), end='')

    if os.path.exists(dst_dir):
        raise Exception('Destination already exists: %s' % dst_dir)

    # find all source files
    try:
        cwd = os.getcwd()
        os.chdir(src_dir)
        src_lst = flatten([os.path.join(path, name) for name in files]
                          for path, dirs, files in os.walk('.'))
    finally:
        os.chdir(cwd)

    parallel_map(proc_file, src_lst)


if __name__ == '__main__':
    optimize_dir('/Volumes/USB-DATA/mxmcc/tiles/unmerged/region_08/4148_1')