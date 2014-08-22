# !/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2014, Matrix Mariner Inc."
#google and openlayers view code taken from tilers-tools by Vadim Shlyakhov
__credits__ = "http://code.google.com/p/tilers-tools/"
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"


import inspect
import os

OFF = False
ON = True

stack = True  # False to silence stack info


def log(debug=OFF, *msg):
    if debug:
        if stack:
            frame = inspect.stack()[1]
            script = os.path.basename(str(frame[1]))
            lineno = str(frame[2])
            func = str(frame[3])
            m = script + ' ' + func + ' ' + lineno + ' '
        else:
            m = ''
        for ea in msg:
            m = m + ' ' + str(ea)
        print m