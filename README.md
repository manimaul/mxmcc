MXMCC - MX Map/Chart Compiler
===

*Copyright (C) 2014 Will Kamp - manimaul@gmail.com*

*License: Your choice [Simplified BSD](http://opensource.org/licenses/BSD-3-Clause) or [MIT](http://opensource.org/licenses/mit-license.html)*

This program creates chart (region) archives in the gemf (See note) format with corresponding meta-data.
Charts in the BSB version 2 and 3 formats are supported as input as well as maps in the Geotiff format.

**Note: Generated gemf + meta data archives are compatible with [MX Mariner](http://mxmariner.com/).**

### Setup [VirtualEnvWrapper](https://virtualenvwrapper.readthedocs.io/en/latest/index.html)
```bash
mkvirtualenv -p python3 mxmcc
pip install -r requirements.txt
```
