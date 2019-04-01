__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2015, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Sanitizes chart file names 
   (allows alpha/numeric, last '.' for file extension, replaces whitespace with  '_' and replaces '&' with 'And')
'''

import os
import re

_PATTERN = '[^_a-zA-Z\d\.]|\.(?=[^.]*\.)'


def _touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def sanitize(root_path):
    if not os.path.isdir(root_path):
        raise Exception(root_path + 'is not a directory')

    if os.path.isfile(os.path.join(root_path, "sane")):
        print('sanitized already complete')
        return

    for root, dirs, files in os.walk(root_path):

        for i, name in enumerate(dirs):
            new_name = name.replace(' ', '_')
            new_name = new_name.replace('&', 'And')
            new_name = re.sub(_PATTERN, '', new_name)
            if name != new_name:
                os.rename(os.path.join(root, name), os.path.join(root, new_name))
                dirs[i] = new_name

        for i, name in enumerate(files):
            new_name = name.replace(' ', '_')
            new_name = new_name.replace('&', 'And')
            new_name = re.sub(_PATTERN, '', new_name)
            if name != new_name:
                os.rename(os.path.join(root, name), os.path.join(root, new_name))
                files[i] = new_name

    _touch(os.path.join(root_path, "sane"))