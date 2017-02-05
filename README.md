MXMCC - MX Map/Chart Compiler
===

*Copyright (C) 2014 Will Kamp - manimaul@gmail.com*

*License: Your choice [Simplified BSD](http://opensource.org/licenses/BSD-3-Clause) or [MIT](http://opensource.org/licenses/mit-license.html)*

This program creates chart (region) archives in the gemf (See note) format with corresponding meta-data.
Charts in the BSB version 2 and 3 formats are supported as input as well as maps in the Geotiff format.

**Note: Generated gemf + meta data archives are compatible with [MX Mariner](http://mxmariner.com/).**

submodules:

https://github.com/mapbox/mbutil

* run $git submodule init

requirements:

* python

* pyproj

* [shapely](http://www.lfd.uci.edu/~gohlke/pythonlibs/#shapely)
Windows: `pip install C:/some-dir/some-file.whl`

* [gdal](http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal)
Version 1.x (2.x not currently compatible)

* pillow

* numpy

* pycrypto

* enum34

* xlrd

* pngnq (binary)


