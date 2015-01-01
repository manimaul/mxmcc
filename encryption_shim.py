#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2015, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Interface to encryption
'''

import os
import subprocess
import shlex

import config


# Java source for region encryption
enc_src_dir = os.path.join(os.getenv('HOME'), 'code/mxmi/mx-mariner-encryption/src')
enc_src_pkg = 'com/mxmariner/crypto'


def _verify_java():
    files = ('FileTreeEncryptor$ProcessFile.class', 'Encryptor.class', 'TokenFactory.class')
    count = 0
    for ea in files:
        if os.path.isfile(os.path.join(enc_src_dir, enc_src_pkg, ea)):
            count += 1

    if len(files) == count:
        # nothing to do
        return True
    else:
        return False


def _make_java_if_needed():
    if _verify_java():
        return True

    commands = ('javac %s/FileTreeEncryptor.java' % enc_src_pkg, 'javac %s/TokenFactory.java' % enc_src_pkg)
    for cmd in commands:
        print 'running', cmd
        p = subprocess.Popen(shlex.split(cmd), cwd=enc_src_dir)
        p.wait()
        print 'complete'

    return _verify_java()


def encrypt_region(region):
    if _make_java_if_needed():
        in_dir = os.path.join(config.merged_tile_dir, region + '.opt')
        out_dir = os.path.join(config.merged_tile_dir, region + '.enc')
        cmd = 'java com.mxmariner.crypto.FileTreeEncryptor %s %s' % (in_dir, out_dir)
        print 'running', cmd
        p = subprocess.Popen(shlex.split(cmd), cwd=enc_src_dir)
        p.wait()
        print 'complete'
        return True
    else:
        return False


def generate_token(region):
    if _make_java_if_needed():
        cmd = 'java com.mxmariner.crypto.TokenFactory %s %s' % (config.compiled_dir, region)
        print 'running', cmd
        p = subprocess.Popen(shlex.split(cmd), cwd=enc_src_dir)
        p.wait()
        print 'complete'
        return True
    else:
        return False


if __name__ == '__main__':
    # encrypt_region('REGION_UK1')
    generate_token('REGION_UK1')