#!/usr/bin/env python

__author__ = 'Will Kamp'
__email__ = 'will@mxmariner.com'
__license__ = 'BSD'
# most of the credit belongs to:
__credits__ = ['http://www.cgtk.co.uk/gemf',
               'A. Budden']
__copyright__ = 'Copyright (c) 2015, Matrix Mariner Inc.\n' + \
                'A. Budden'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''This parses through a given ZXY tiled map directory and generates a gemf file.'''

import os
from Crypto import Random
import config
from tilesystem import tile_size


file_size_limit = 2000000000L


def _valto_n_bytes(value, n):
    result = []
    for _ in range(n):
        result.append(value & 0xFF)
        value >>= 8
    result.reverse()
    return result


def _valto_4_bytes(value):
    return _valto_n_bytes(value, 4)


def _valto_8_bytes(value):
    return _valto_n_bytes(value, 8)


def generate_gemf(name, add_uid=False):
    """generates a (s)gemf archive for tiles in mapdir
       name - name of the (s)gemf archive to be created in the config.compiled_dir directory
       add_uid - set to true if the tiles are encrypted and have a 16 byte initial vector
    """

    if not os.path.isdir(os.path.join(config.merged_tile_dir, name)):
        raise Exception(name + ' not a directory')
    
    options = {}
    if add_uid:
        options['add-uid'] = True
    
    if add_uid:
        ext = '.sgemf'
    else:
        ext = '.gemf'

    base_name = name[:name.rfind('.')].upper()  # remove .enc or .opt
    output_file = os.path.join(config.compiled_dir, base_name + ext)
    tilesize = tile_size

    extensions = ('.png.tile', '.jpg.tile', '.png', '.jpg')

    all_sources = {}
    source_order = []
    source_index = 0
    source_indices = {}
    count = {}
    
    mapdir = config.merged_tile_dir
    
    source_list = [name]

    for source in source_list:
        results = {}
        source_mapdir = os.path.join(mapdir, source)
        if not os.path.isdir(source_mapdir):
            print 'Skipping ' + source_mapdir
            continue

        source_indices[source] = source_index

        # Generate results[zoom][x] = [y1,y2,...]
        for zoom_level_str in os.listdir(source_mapdir):
            zoom_level = int(zoom_level_str)
            results[zoom_level] = {}

            zoom_dir = os.path.join(source_mapdir, zoom_level_str)
            if not os.path.isdir(zoom_dir):
                print 'Skipping ' + zoom_dir
                continue

            for x_str in os.listdir(zoom_dir):
                x_set = []
                x_val = int(x_str)

                x_dir = os.path.join(zoom_dir, x_str)
                if not os.path.isdir(x_dir):
                    print 'Skipping ' + x_dir
                    continue

                for y_str in os.listdir(x_dir):
                    y_val = int(y_str.split('.')[0])
                    x_set.append(y_val)

                results[zoom_level][x_val] = x_set[:]

        if 'allow-empty' in options:
            full_sets = {}
            for zoom_level in results.keys():
                full_sets[zoom_level] = []
                xmax = max(results[zoom_level].keys())
                xmin = min(results[zoom_level].keys())
                y_vals = []
                for x_val in results[zoom_level].keys():
                    y_vals += results[zoom_level][x_val]
                ymax = max(y_vals)
                ymin = min(y_vals)
                full_sets[zoom_level].append({'xmin': xmin, 'xmax': xmax,
                                              'ymin': ymin, 'ymax': ymax,
                                              'source_index': source_index})

        else:
            # A record representing a square of 1-5 tiles at zoom 10
            # unique_sets[zoom][Y values key] = [X values array]
            # unique_sets[10]['1-2-3-4-5'] = [1,2,3,4,5]
            unique_sets = {}
            for zoom_level in results.keys():
                unique_sets[zoom_level] = {}
                for x_val in results[zoom_level].keys():

                    # strkey: Sorted list of Y values for a zoom/X, eg: '1-2-3-4'
                    strkey = '-'.join(['%d' % i for i in sorted(results[zoom_level][x_val])])
                    if strkey in unique_sets[zoom_level].keys():
                        unique_sets[zoom_level][strkey].append(x_val)
                    else:
                        unique_sets[zoom_level][strkey] = [x_val, ]

            # Find missing X rows in each unique_set record
            split_xsets = {}
            for zoom_level in results.keys():
                split_xsets[zoom_level] = []
                for xset in unique_sets[zoom_level].values():
                    setxmin = min(xset)
                    setxmax = max(xset)
                    last_valid = None
                    for xv in xrange(setxmin, setxmax+2):
                        if xv not in xset and last_valid is not None:
                            split_xsets[zoom_level].append({'xmin': last_valid, 'xmax': xv-1})
                            last_valid = None
                        elif xv in xset and last_valid is None:
                            last_valid = xv

            # Find missing Y rows in each unique_set chunk, create full_sets records for each complete chunk

            full_sets = {}
            for zoom_level in split_xsets.keys():
                full_sets[zoom_level] = []
                for xr in split_xsets[zoom_level]:
                    yset = results[zoom_level][xr['xmax']]
                    setymin = min(yset)
                    setymax = max(yset)
                    last_valid = None
                    for yv in xrange(setymin, setymax+2):
                        if yv not in yset and last_valid is not None:
                            full_sets[zoom_level].append({'xmin': xr['xmin'], 'xmax': xr['xmax'],
                                                          'ymin': last_valid, 'ymax': yv-1,
                                                          'source_index': source_index})
                            last_valid = None
                        elif yv in yset and last_valid is None:
                            last_valid = yv

        count[source] = {}
        for zoom_level in full_sets.keys():
            count[source][zoom_level] = 0
            for rangeset in full_sets[zoom_level]:
                for xv in xrange(rangeset['xmin'], rangeset['xmax']+1):
                    for yv in xrange(rangeset['ymin'], rangeset['ymax']+1):
                        found = False
                        for extension in extensions:
                            fpath = os.path.join(source_mapdir, '%d/%d/%d%s' % (zoom_level, xv, yv, extension))
                            if os.path.exists(fpath):
                                found = True
                                break
                        if not found and 'allow-empty' not in options:
                            raise IOError('Could not find file (%s, %d, %d, %d)' % (source, zoom_level, xv, yv))

                        count[source][zoom_level] += 1
            print source_mapdir, zoom_level, count[source][zoom_level]

        all_sources[source] = full_sets
        source_order.append(source)
        source_index += 1

    u32_size = 4
    u64_size = 8
    range_size = (u32_size * 6) + (u64_size * 1)  # xmin, xmax, ymin, ymax, zoom, source, offset
    file_info_size = u64_size + u32_size
    number_of_ranges = 0
    number_of_files = 0
    for source in source_order:
        full_sets = all_sources[source]
        number_of_ranges += sum([len(full_sets[i]) for i in full_sets.keys()])
        number_of_files += sum(count[source].values())
    source_count = 0

    source_list = []
    for source in source_order:
        source_list += _valto_4_bytes(source_indices[source])
        source_list += _valto_4_bytes(len(source))
        source_list += [ord(i) for i in source.encode('ascii', 'ignore')]
        source_count += 1

    source_list_size = len(source_list)

    gemf_version = 4

    uid_size = 0
    if 'add-uid' in options:
        uid_size = 16

    pre_info_size = (uid_size +  # Random 16 byte uid
                     u32_size +  # GEMF Version
                     u32_size +  # Tile size
                     u32_size +  # Number of ranges
                     u32_size +  # Number of sources
                     source_list_size +  # Size of source list
                     number_of_ranges * range_size)  # Ranges
    header_size = (pre_info_size + (number_of_files * file_info_size))  # File header info

    image_offset = header_size

    print 'Source Count:', source_count
    print 'Source List Size:', source_list_size
    print 'Source List:', repr(source_list)
    print 'Pre Info Size:', pre_info_size
    print 'Number of Ranges:', number_of_ranges
    print 'Number of files:', number_of_files
    print 'Header Size (first image location): 0x%08X' % header_size

    header = []

    header += _valto_4_bytes(gemf_version)
    header += _valto_4_bytes(tilesize)
    header += _valto_4_bytes(source_count)
    header += source_list

    header += _valto_4_bytes(number_of_ranges)

    data_locations = []
    data_location_address = 0

    file_list = []

    first_range = True
    first_tile = True

    tile_count = 0
    for tile_source in source_order:
        full_source_set = all_sources[tile_source]

        for zoom_level in full_source_set.keys():
            for rangeset in full_source_set[zoom_level]:
                if first_range:
                    h = len(header)
                    print 'First range at 0x%08X' % len(header)
                header += _valto_4_bytes(zoom_level)
                header += _valto_4_bytes(rangeset['xmin'])
                header += _valto_4_bytes(rangeset['xmax'])
                header += _valto_4_bytes(rangeset['ymin'])
                header += _valto_4_bytes(rangeset['ymax'])
                header += _valto_4_bytes(rangeset['source_index'])
                header += _valto_8_bytes(data_location_address + pre_info_size)

                if first_range:
                    hb = header[h:]
                    print 'Range Data: [' + ','.join(['%02X' % i for i in hb]) + ']'
                    print 'First Data Location: 0x%08X' % (data_location_address + pre_info_size)
                    first_range = False

                for xv in xrange(rangeset['xmin'], rangeset['xmax']+1):
                    for yv in xrange(rangeset['ymin'], rangeset['ymax']+1):
                        found = False
                        for extension in extensions:
                            fpath = os.path.join(mapdir, '%s/%d/%d/%d%s' % (tile_source, zoom_level, xv, yv, extension))
                            if os.path.exists(fpath):
                                found = True
                                break

                        if not found:
                            if 'allow-empty' in options:
                                file_size = 0
                            else:
                                raise IOError('Could not find file (%s, %d, %d, %d)' 
                                              % (tile_source, zoom_level, xv, yv))
                        else:
                            file_size = os.path.getsize(fpath)
                        file_list.append(fpath)

                        # This file is at image_offset, length file_size
                        data_locations += _valto_8_bytes(image_offset)
                        data_locations += _valto_4_bytes(file_size)
                        tile_count += 1

                        if first_tile:
                            print 'First Tile Info: [' + ','.join(['%02X' % i for i in data_locations]) + ']'
                            print '(0x%016X, 0x%08X)' % (image_offset, file_size)
                            first_tile = False

                        data_location_address += u64_size + u32_size

                        # Update the image_offset
                        image_offset += file_size

    print 'Header Length is 0x%08X' % len(header)
    print 'First tile expected at 0x%08X' % (len(header) + len(data_locations))
    print 'Tile Count is %d (c.f. %d)' % (tile_count, number_of_files)
    print ''

    gemf_f = open(output_file, 'wb')
    if 'add-uid' in options:
        gemf_f.write(Random.get_random_bytes(16))
    gemf_f.write(''.join([chr(i) for i in header]))
    gemf_f.write(''.join([chr(i) for i in data_locations]))

    file_size = len(header) + len(data_locations)
    index = 0
    for fn in file_list:
        if os.path.exists(fn):
            this_file_size = os.path.getsize(fn)
        else:
            if 'allow-empty' in options:
                this_file_size = 0
            else:
                raise IOError('Could not find file %s' % fn)
        if (file_size + this_file_size) > file_size_limit:
            gemf_f.close()
            index += 1
            gemf_f = open(output_file + '-%d' % index, 'wb')
            file_size = 0L

        if os.path.exists(fn):
            tile_f = open(fn, 'rb')
            gemf_f.write(tile_f.read())
            tile_f.close()
        file_size += this_file_size

    gemf_f.close()