import os
import re

import config


pattern = '[^._a-zA-Z\d:]'


def sanitize():
    for root, dirs, files in os.walk(config.wavey_line_geotiff_dir):

        for i, name in enumerate(dirs):
            new_name = name.replace(' ', '_')
            new_name = new_name.replace('&', 'And')
            new_name = re.sub(pattern, '', new_name)
            if name != new_name:
                print name, new_name
                os.rename(os.path.join(root, name), os.path.join(root, new_name))
                dirs[i] = new_name

        for i, name in enumerate(files):
            new_name = name.replace(' ', '_')
            new_name = new_name.replace('&', 'And')
            new_name = re.sub(pattern, '', new_name)
            if name != new_name:
                print name, new_name
                os.rename(os.path.join(root, name), os.path.join(root, new_name))
                files[i] = new_name


if __name__ == '__main__':
    sanitize()