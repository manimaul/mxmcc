#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2014, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Burns (removes images) previously indexed with computer vision from charts.
   This is useful for removing images / logos that the original chart producer requires us to remove
'''

import os
import shlex
import subprocess
from osgeo import gdal
from PIL import Image

from . import config


match_f_name = "%s:%s:%s:%s:%s.png"  # chart#crest#score#xoff#yoff
matched_crest_dir = os.path.join(config.ukho_meta_dir, 'CRESTS', 'MATCHED')
gdal.AllRegister()


def burn(chart_f_name, burn_coord_list):
    # chart png to create
    png_path = os.path.join(config.ukho_png_dir, chart_f_name + ".png")

    if os.path.isfile(png_path):
        print('done')
        return

    # chart png to open
    tif_path = os.path.join(config.ukho_geotiff_dir, chart_f_name + ".tif")

    if not os.path.isfile(tif_path):
        print('WARNING: not tif for: ' + chart_f_name)
        return

    if not os.path.isfile(png_path):
        print("creating png with gdal")
        # -----create a png
        command = "gdal_translate -of PNG -expand rgba \"%s\" \"%s\"" % (
        os.path.normpath(tif_path), os.path.normpath(png_path))
        subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE).wait()
        # -----

    if not os.path.isfile(png_path):
        raise Exception('failed to create png: ' + chart_f_name)

    # open png with PIL
    img = Image.open(png_path)

    for dicTuple in burn_coord_list:
        crest, score, xoff, yoff = dicTuple
        print("burning away crest %s" % crest)
        cst = match_f_name % (chart_f_name, crest, score, xoff, yoff)
        cst_path = os.path.join(matched_crest_dir, cst)

        # get width height and bg color of crest
        im = Image.open(cst_path)
        im = im.convert("RGB")
        px = im.getpixel((0, 0))

        # burn away rectangle
        rec = Image.new('RGB', im.size, px)
        img.paste(rec, (int(xoff), int(yoff)))

    # save chart png
    img.save(png_path)


def build_dictionary():
    """list files in matched directory
       build dictionary with chart name as key containing list of tuples of data to burn
       tuples are (crest,x_offset,y_offset) """
    dictionary = {}
    for f in os.listdir(matched_crest_dir):
        tif, crest, score, xoff, yoff = f.rstrip(".png").split(":")
        if tif in dictionary:
            dictionary[tif].append((crest, score, xoff, yoff))
        else:
            lst = [(crest, score, xoff, yoff)]
            dictionary[tif] = lst

    return dictionary


if __name__ == "__main__":
    d = build_dictionary()

    total = len(d.keys())
    num = 1
    for ea in d.keys():
        print("%s of %s" % (num, total))
        burn(ea, d[ea])
        num += 1