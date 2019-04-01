#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2014, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

import json
import hashlib
import os
from . import config
import time
from .zdata import get_zdat_epoch

BASE_URL = ''


def merge_manifest(json_path_old, json_path_new, json_path_result):
    json_old = json.load(open(json_path_old, 'r'))
    json_new = json.load(open(json_path_new, 'r'))
    for key in json_new['regions'].keys():
        json_old['regions'][key] = json_new['regions'][key]

    with open(json_path_result, 'w') as f:
        json.dump(json_old, f, indent=2)


def get_time_stamp(epoch=int(time.time()), local=False):
    if local:
        struct_time = time.localtime(epoch)
    else:
        struct_time = time.gmtime(epoch)
    return time.strftime('TS_%Y-%m-%d_T_%H_%M', struct_time)


def checksum(abs_path):
    m = hashlib.sha1()
    with open(abs_path, 'rb') as f:
        m.update(f.read())
    return m.hexdigest()


def generate(data=None, base_url=BASE_URL):
    if data is None:
        data = {'manifest_version': 1, 'regions': {}}
    elif data['manifest_version'] is not 1:
        raise Exception('Invalid data')

    for ea in os.listdir(config.compiled_dir):
        if ea.endswith('gemf'):
            region_ts = ea[:ea.find('.')]
            region = region_ts[region_ts.find('REGION'):]

            abs_path_data_org = os.path.join(config.compiled_dir, region_ts + '.zdat')
            abs_path_gemf_org = os.path.join(config.compiled_dir, ea)
            epoch = int(get_zdat_epoch(abs_path_data_org))
            ts = get_time_stamp(epoch, local=True)

            gemf_name = ts + '_' + ea
            data_name = ts + '_' + region_ts + '.zdat'
            abs_path_gemf = os.path.join(config.compiled_dir, gemf_name)
            abs_path_data = os.path.join(config.compiled_dir, data_name)

            os.rename(abs_path_gemf_org, abs_path_gemf)
            os.rename(abs_path_data_org, abs_path_data)
            print(region)
            data['regions'][region] = {'gemf_url': base_url + '/' + gemf_name,
                                       'data_url': base_url + '/' + data_name,
                                       'gemf_checksum': checksum(abs_path_gemf),
                                       'data_checksum': checksum(abs_path_data),
                                       'size_bytes': os.path.getsize(abs_path_gemf),
                                       'epoch': epoch}
    abs_path_json = os.path.join(config.compiled_dir, 'manifest.json')
    if os.path.exists(abs_path_json):
        os.remove(abs_path_json)
    with open(abs_path_json, 'w') as f:
        json.dump(data, f, indent=2)

    return data


def generate_chart_manifest(base_url=BASE_URL):
    data = {'manifest_version': 1, 'charts': []}

    for each in os.listdir(config.compiled_dir):
        if each.endswith('mbtiles'):
            chart_name = each[:each.find('.')]

            abs_path_org = os.path.join(config.compiled_dir, each)
            epoch = os.path.getmtime(abs_path_org)
            ts = get_time_stamp(epoch, local=True)

            chart_rename = ts + '_' + each
            abs_path_chart_rename = os.path.join(config.compiled_dir, chart_rename)

            os.rename(abs_path_org, abs_path_chart_rename)
            data['charts'].append({'name': chart_name,
                                   'url': base_url + '/' + chart_rename,
                                   'check_sum': checksum(abs_path_chart_rename),
                                   'size_bytes': os.path.getsize(abs_path_chart_rename),
                                   'epoch': epoch})
    abs_path_json = os.path.join(config.compiled_dir, 'chart_manifest.json')
    if os.path.exists(abs_path_json):
        os.remove(abs_path_json)
    with open(abs_path_json, 'w') as f:
        json.dump(data, f, indent=2)

    return data


def revert():
    for ea in os.listdir(os.path.join(config.compiled_dir)):
        if 'TS_' in ea and ea.endswith('gemf') or ea.endswith('zdat'):
            region_ts = ea[:ea.find('.')]
            region = region_ts[region_ts.find('REGION'):]
            ext = ea[ea.find('.'):]
            print(ext, region, ea)
            os.rename(os.path.join(config.compiled_dir, ea), os.path.join(config.compiled_dir, region + ext))


if __name__ == '__main__':
    # revert()
    # generate()
    o = os.path.join(config.compiled_dir, 'manifest_broke.json')
    n = os.path.join(config.compiled_dir, 'manifest.json')
    r = os.path.join(config.compiled_dir, 'manifest_result.json')
    merge_manifest(o, n, r)