#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

import os


class MapPathSearch:
    def __init__(self, directory, map_extensions=['kap', 'tif'], include_only=None):
        """Searches for files ending with <map_extensions> in <directory> and all subdirectories

           Optionally supply set of file names <include_only> to only return paths of files that
           are contained in the set eg. {file1.kap, file2.tif}

           file_paths is a list of all full paths found
        """
        self.file_paths = []

        extensions = set()
        for ext in map_extensions:
            extensions.add(ext.upper())

        if include_only is not None:
            include_only = set(include_only)

        if os.path.isdir(directory):
            for root, dirs, files in os.walk(directory):
                for f in files:
                    include = False
                    i = f.rfind(".")
                    if i > 0:
                        ext = f[i+1:].upper()
                        include = ext in extensions
                        if include and include_only is not None:
                            include = f in include_only
                    if include:
                        self.file_paths.append(os.path.join(root, f))
        else:
            print(directory, 'is not a directory.')

#    def __walker(self, args, p_dir, p_file):
#        map_extensions, include_only = args
#        if include_only is not None:
#            include_only = set(include_only)
#        for f in p_file:
#            if f.upper().endswith(map_extensions) and (include_only is None or f in include_only) and not f.startswith(
#                    "."):
#                self.file_paths.append(os.path.join(p_dir, f))


if __name__ == '__main__':
    print("foo")
