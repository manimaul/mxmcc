#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Builds a vrt with expanded rgba if needed and cropped cut line for a given map and cutline'''

from osgeo import gdal
import subprocess
import os.path
import shlex
import lookups

#http://www.gdal.org/formats_list.html
geotiff = 'Gtiff'
bsb = 'BSB'
png = 'PNG'
supported_formats = {geotiff, bsb, png}


def build_vrt_for_map(map_path, cutline=None):
    dataset = gdal.Open(map_path, gdal.GA_ReadOnly)

    if dataset is None:
        raise Exception('could not open map file: ' + map_path)

    map_type = dataset.GetDriver().ShortName

    if not map_type in supported_formats:
        raise Exception(map_type + ' is not a supported format')

    #-----paths and file names
    base_dir = os.path.dirname(map_path)
    map_fname = os.path.basename(map_path)
    map_name = map_fname[0:map_fname.find('.')]  # remove file extension

    vrt_path = os.path.join(base_dir, map_name + '.vrt')
    if os.path.isfile(vrt_path):
        os.remove(vrt_path)

    c_vrt_path = os.path.join(base_dir, map_name + '_c.vrt')
    if os.path.isfile(c_vrt_path):
        os.remove(c_vrt_path)

    log = open(os.devnull, 'w')

    #-----create a cutline
    if cutline is not None:
        kml_path = os.path.join(base_dir, map_name+"_cutline.kml")
        if os.path.isfile(kml_path):
            os.remove(kml_path)

        kml = open(kml_path, "w")
        kml.write(lookups.get_cutline_kml(cutline))
        kml.close()

        #-----create cutline vrt
        if map_type is png:
            command = "gdalwarp -of vrt -cutline %s -crop_to_cutline -overwrite %s %s" \
                      % (kml_path, map_path, vrt_path)
        else:
            command = "gdalwarp -of vrt -cutline %s -crop_to_cutline -overwrite -dstnodata 0 -dstalpha %s %s" \
                      % (kml_path, map_path, vrt_path)

        subprocess.Popen(shlex.split(command), stdout=log).wait()

    if os.path.isfile(c_vrt_path):
            map_src = vrt_path
    else:
        map_src = map_path

    #-----expand rgba if map has a palette
    if dataset.GetRasterBand(1).GetRasterColorTable() is not None:
        command = "gdal_translate -of vrt -expand rgba %s %s" % (map_src, c_vrt_path)
        subprocess.Popen(shlex.split(command), stdout=log).wait()
        print command
        return c_vrt_path

    return map_src


#def vrt_make(map_path):
#    dataset = gdal.Open(map_path, gdal.GA_ReadOnly)
#    vrt_drv = gdal.GetDriverByName('VRT')
#    vrt_drv.CreateCopy('test.vrt', dataset)

if __name__ == "__main__":
    import config
    import catalog
    config.noaa_bsb_dir
    reader = catalog.get_reader_for_region('region_15')
    my_chart = reader[67]
    #map_path = os.path.join(config.noaa_bsb_dir, 'BSB_ROOT/18453/18453_1.KAP')
    print build_vrt_for_map(my_chart['path'], my_chart['outline'])