#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''MX Mariner zdata generator for regions / catalogs'''

import codecs
import os.path
import zipfile

import config
import catalog
import regions


upd_fmt = U'UPDATE regions SET installeddate=\'%s\' WHERE name=\'%s\';\n'

custom_fmt0 = u'DELETE from regions WHERE name=\'%s\';\n'
custom_fmt1 = u'INSERT into [regions] ([name], [description], [image], [size], [installeddate] ) ' \
              u'VALUES (\'%s\', \'%s\', \'%s\', \'%s\', \'%s\');\n'

fmt0 = u'DELETE from charts where region=\'%s\';\n'
fmt1 = u'INSERT INTO [charts] ([region], [file], [name], [updated], [scale], [outline], [depths], [zoom]) ' \
       u'VALUES (\'%s\', \'%s\', \'%s\', \'%s\', %s, \'%s\', \'%s\', \'%s\');\n'


def get_zdat_epoch(zdat_path):
    """
    :param zdat_path: path to the <region>.zdat file
    :return: the installeddate value to be set
    """
    zdat_file = zipfile.ZipFile(zdat_path, 'r', zipfile.ZIP_DEFLATED)
    line = zdat_file.open(zdat_file.namelist()[0], 'r').readlines()[1]
    l = line.find('\'') + 1
    r = line.find('\'', l)
    return line[l:r]


def generate_update():
    """generates and UPDATE.zdat file for all of the new (s)gemf regions rendered
    """
    sql_fname = 'UPDATE.sql'
    sql_path = os.path.join(config.compiled_dir, sql_fname)
    zdat_path = os.path.join(config.compiled_dir, 'UPDATE.zdat')
    print zdat_path
    zdat = zipfile.ZipFile(zdat_path, 'w', zipfile.ZIP_DEFLATED)
    sqlf = open(sql_path, 'w')
    gemf_lst = []
    for ea in os.listdir(config.compiled_dir):
        if ea.endswith('gemf'):
            gemf_lst.append(os.path.join(config.compiled_dir, ea))
    gemf_lst.sort()

    if len(gemf_lst) is 0:
        return

    sqlstr = u'update regions set latestdate=\'%s\', size=\'%s\' where name=\'%s\';'
    sqlf.write(u'--MXMARINER-DBVERSION:1\n')
    for p in gemf_lst:
        size = str(os.path.getsize(p))
        region = os.path.basename(p)
        region = region[:region.rfind('.')]
        z_path = os.path.join(config.compiled_dir, region + '.zdat')
        sqlf.write(sqlstr % (get_zdat_epoch(z_path), size, region)+'\n')

    sqlf.close()
    zdat.write(sql_path, sql_fname)
    os.remove(sql_path)
    zdat.close()
    print 'update written to: ' + zdat_path


def generate_zdat_for_catalog(catalog_name, description=None):
    """generates a zdat file for a region
       catalog_name - the name of the catalog / region to generate data for
       description - if this is a custom catalog / region... set the description here
    """
    region = catalog_name.upper()
    reader = catalog.get_reader_for_region(catalog_name)

    sql_fname = region + '.sql'
    sql_path = os.path.join(config.compiled_dir, sql_fname)
    zdat_path = os.path.join(config.compiled_dir, region + '.zdat')
    sql_file = codecs.open(sql_path, 'w', 'utf-8')
    zdat_file = zipfile.ZipFile(zdat_path, 'w', zipfile.ZIP_DEFLATED)

    sql_file.write('--MXMARINER-DBVERSION:3\n')

    if regions.is_valid_region(region):
        sql_file.write(upd_fmt % (config.epoch, region))
        sql_file.write(fmt0 % region)
    else:
        num_bytes = os.path.getsize(os.path.join(config.compiled_dir, region + '.gemf'))
        sql_file.write(custom_fmt0 % region)
        sql_file.write(custom_fmt1 % (region, description, region.lower().replace('_', ''), num_bytes, config.epoch))

    for entry in reader:
            sql_file.write(fmt1 % (region, os.path.basename(entry['path']), entry['name'], entry['date'],
                                                            entry['scale'], entry['outline'], entry['depths'],
                                                            entry['zoom']))

    sql_file.close()
    zdat_file.write(sql_path, sql_fname)
    os.remove(sql_path)
    zdat_file.close()

if __name__ == '__main__':
    generate_update()
