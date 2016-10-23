#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2016, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Fetches FAA Raster VFR Charts
'''

import os
import urllib
from region_constants import *
from urlparse import urlsplit
import config
import zipfile
from bs4 import BeautifulSoup
import requests
import re

faa_regions = {
  REGION_FAA_PLANNING: {
    "http": "http://aeronav.faa.gov/content/aeronav/Grand_Canyon_files/",
    "sources": []
  },
  REGION_FAA_SECTIONAL: {
    "http": "http://aeronav.faa.gov/content/aeronav/sectional_files/",
    "sources": []
  },
  REGION_FAA_TERMINAL: {
    "http": "http://aeronav.faa.gov/content/aeronav/tac_files/",
    "sources": []
  },
  REGION_FAA_HELICOPTER: {
    "http": "http://aeronav.faa.gov/content/aeronav/heli_files/",
    "sources": []
  },
  REGION_FAA_CARIBBEAN: {
    "http": "http://aeronav.faa.gov/content/aeronav/Caribbean/",
    "sources": []
  }
}


def name_and_number(name):
    n = re.sub('[\d]', '', name)
    try:
        i = int(re.sub('[\D]', '', name))
    except ValueError:
        i = 0
    return n, i


def list_links(url, ext=''):
    page = requests.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    return [url + '/' + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]


def directory_data(region):
    http_dir = faa_regions[region]['http']
    data = dict()
    for each in list_links(url=http_dir, ext='.zip'):
        name = each.split('/')[-1]
        name, number = name_and_number(name)
        if name in data:
            if data[name]['number'] < number:
                data[name] = {'number': number, 'link': each}
        else:
            data[name] = {'number': number, 'link': each}
    return data

for r in faa_regions:
    d = directory_data(r)
    for e in d:
        faa_regions[r]['sources'].append(d[e]['link'])


def unzip(source_filename, dest_dir):
    try:
        with zipfile.ZipFile(source_filename) as zf:
            for member in zf.infolist():
                words = member.filename.split('/')
                path = dest_dir
                for word in words[:-1]:
                    drive, word = os.path.splitdrive(word)
                    head, word = os.path.split(word)
                    if word in (os.curdir, os.pardir, ''):
                        continue
                    path = os.path.join(path, word)
                zf.extract(member, path)
        return True
    except:
        return False


def fetch_region(region):
    if region in faa_regions:
        http_dir = faa_regions[region]['http']
        for name in faa_regions[region]['sources']:
            link = http_dir + name
            p = urlsplit(link)
            file_name = os.path.split(p.path)[1]
            dest = os.path.join(config.faa_geotiff_dir, file_name)
            if not os.path.isfile(dest):
                print 'retrieving {}'.format(link)
                urllib.urlretrieve(link, dest)
                print 'unzipping {}'.format(dest)
                unzip(dest, config.faa_geotiff_dir)


def fetch_all():
    for r in faa_regions:
        fetch_region(r)

if __name__ == '__main__':
    print 'downloading regions'
    fetch_all()
