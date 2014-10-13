#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2013, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Downloads brazilian BSB raster charts posted on http_base_url
'''

import urllib
import os.path
import re
from urlparse import urljoin
import subprocess
import shlex

import config


http_base_url = 'https://www.mar.mil.br/dhn/chm/box-cartas-raster'
http_index_html = http_base_url + '/raster_disponiveis.html'
http_zip_url = http_base_url + '/cartas/'

html_parse_map = {'/tmp/raster_disponiveis.html.html': http_index_html}

zip_dir = os.path.join(config.brazil_bsb_dir, 'zips')


def unzip():
    all_zip_files = os.listdir(zip_dir)
    os.chdir(zip_dir)
    count = 0
    for zip_file in all_zip_files:
        count += 1
        command = "unzip -j -n -d " + config.brazil_bsb_dir + " " + zip_file
        print 'unzipping', zip_file
        subprocess.Popen(shlex.split(command)).wait()

    print "%s zip files unzipped" % count


def wget():
    if not os.path.isdir(zip_dir):
        os.makedirs(zip_dir)

    for tmp_html_file in html_parse_map.keys():

        if not os.path.isfile(tmp_html_file):
            html_url = html_parse_map[tmp_html_file]
            print 'retrieving html from %s' % html_url
            urllib.urlretrieve(html_url, tmp_html_file)
        else:
            print 'using html file in tmp'

        dlcount = 0
        cachecount = 0
        fd = open(tmp_html_file)
        html_str = fd.read()
        fd.close()
        urls = re.findall(r'href=[\'"]?([^\'" >]+)', html_str)
        for url in urls:
            if url.endswith('.zip') and 'geotiff' in url:
                chart = url[9:len(url) - 11] + '.zip'
                # zipPath = our_dir + '/' + url.split('/')[-1]
                # zurl = urljoin(http_base_url, url)

                zip_path = os.path.join(zip_dir, chart)
                zurl = urljoin(http_zip_url, chart)
                print zurl
                if not os.path.isfile(zip_path):
                    urllib.urlretrieve(zurl, zip_path)
                    dlcount += 1
                else:
                    # print 'already have: ' + zurl
                    cachecount += 1

        print 'downloaded %s zip files and used %s cached zip files' % (dlcount, cachecount)


if __name__ == '__main__':
    wget()
    unzip()