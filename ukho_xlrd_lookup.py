#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2014, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

import os
import re

import xlrd

import config


def file_name_decoder(file_name):
    """returns tuple(chart_number, suffix, panel_number)"""
    file_name = file_name[:file_name.rfind('.')]
    fn = os.path.basename(file_name)
    non_digit = re.search('\D', fn).start()
    chart_number = fn[0:non_digit].lstrip('0')
    hyphen = fn.find('-')
    suffix = fn[non_digit:hyphen]
    if suffix == '':
        suffix = '-'

    last_index = fn.find('_')
    if last_index is -1:
        last_index = len(fn)

    panel_number = fn[hyphen+1:last_index]

    # sometimes there is an additional dash if the chart is broken up into multiple files
    last_index = panel_number.find('-')
    if last_index is not -1:
        panel_number = panel_number[0:last_index]

    # print 'fileNameDecoded', (chart_number, suffix, panel_number)
    return chart_number, suffix, panel_number


def stamp(file_name):
    return stamp_from_detail(*file_name_decoder(file_name))


def stamp_from_detail(chart_number, suffix, panel_number):
    return str(chart_number) + '_' + str(suffix) + '_' + str(panel_number)


def _lat_lng_dmm_to_ddd(lat_dmm, lng_dmm):
    """converts lat,lng in degree-decimal minutes
       to decimal degrees.

    ex. latDmm, lngDmm = ('-28 59.803', '048 06.998')
        latDmm, lngDmm = ('28.204', -000 34.086') """

    lat_deg, lat_min = lat_dmm.split(' ')
    lng_deg, lng_min = lng_dmm.split(' ')

    if lat_deg.startswith('-'):
        lat = float(lat_deg) - (float(lat_min) / 60)
    else:
        lat = float(lat_deg) + (float(lat_min) / 60)

    if lng_deg.startswith('-'):
        lng = float(lng_deg) - (float(lng_min) / 60)
    else:
        lng = float(lng_deg) + (float(lng_min) / 60)

    return lat, lng


# noinspection PyMethodMayBeStatic
class Data:
    def __init__(self, chart_number, suffix, panel_number, name, scale, depth_units):
        self.chart_number = chart_number
        self.suffix = suffix
        self.panel_number = panel_number
        self.name = name
        self.scale = int(scale)
        self.depth_units = depth_units
        self.updated = None
        self.coords = []
        or_name = str(self.chart_number) + '-' + str(self.panel_number)
        override_path = os.path.join(os.path.dirname(__file__), 'ukho_overrides', or_name)
        if os.path.isfile(override_path):
            # print 'using ply override coordinates'
            self.coords = self._get_override_coords(override_path)

    def _get_override_coords(self, path_to_override):
        coords = []
        with open(path_to_override, 'r') as override:
            for line in override.readlines():
                lat, lng = line.strip().split(',')
                coords.append(_lat_lng_dmm_to_ddd(lat, lng))
        coords.append(coords[0])
        return coords

    def get_center(self):
        lats = []
        lngs = []
        for lat, lng in self.coords:
            lats.append(lat)
            lngs.append(lng)

        if len(lats) is 0:
            centerlat = 0
        else:
            centerlat = min(lats) + (max(lats) - min(lats)) / 2

        if len(lngs) is 0:
            centerlng = 0
        else:
            centerlng = min(lngs) + (max(lngs) - min(lngs)) / 2

        return centerlng, centerlat

    def set_updated(self, updated):
        self.updated = updated

    def get_name(self):
        return self.name

    def get_zoom(self):
        # we don't know the path to the data set at this point to be able to calculate the zoom from true scale
        raise NotImplementedError('handle get_zoom in lookups.UKHOLookup')

    # def get_zoom(self):
    # if self.scale is None:
    #         return 0
    #
    #     return findzoom.get_zoom(int(self.scale), self.get_center()[1])

    def get_scale(self):
        return self.scale

    def get_updated(self):
        return self.updated

    def get_depth_units(self):
        return self.depth_units

    def get_outline(self):
        outline = ''
        for ea in self.coords:
            outline += str(ea[0]) + ',' + str(ea[1]) + ':'
        return outline.rstrip(':')

    def get_is_valid(self):
        return True


# noinspection PyBroadException
class MetaLookup:
    def __init__(self):
        xls_path = config.ukho_quarterly_extract
        self.xls = xlrd.open_workbook(xls_path)
        self.charts = {}
        self.depth_codes = self._read_depth_codes()
        self._read_charts()
        self._read_panels()
        self._read_editions()
        self._read_coords()

    def _read_depth_codes(self):
        dcodes = []
        sheet = self.xls.sheet_by_name('Depth Units')
        for n in range(sheet.nrows):
            try:
                code = str(int(sheet.row(n)[0].value))
                dunit = str(sheet.row(n)[1].value)
                dcodes.append((code, dunit))
            except ValueError:  # sometimes UKHO adds a header :\
                pass
        return dict(dcodes)

    def _read_charts(self):
        sheet = self.xls.sheet_by_name('Charts & Titles')
        for n in range(sheet.nrows):
            if n > 0:
                chart_number = str(int(sheet.row(n)[1].value))
                suffix = sheet.row(n)[2].value
                panel_number = '0'
                name = re.sub(r'\s+', ' ', sheet.row(n)[4].value).replace('\'', '')
                scale = str(int(sheet.row(n)[6].value))
                depth_code = str(int(sheet.row(n)[8].value))
                try:
                    depth_unit = self.depth_codes[depth_code].upper().replace('/', ' AND ')
                except:
                    # print 'error finding depth unit for', chart_number, depth_code
                    depth_unit = 'UNKNOWN'
                d = Data(chart_number, suffix, panel_number, name, scale, depth_unit)
                s = stamp_from_detail(chart_number, suffix, panel_number)
                self.charts[s] = d

    def _read_panels(self):
        sheet = self.xls.sheet_by_name('Panels')
        for n in range(sheet.nrows):
            if n > 0:
                chart_number = str(int(sheet.row(n)[1].value))
                suffix = sheet.row(n)[2].value
                panel_number = str(int(sheet.row(n)[3].value))
                name = re.sub(r'\s+', ' ', sheet.row(n)[4].value).replace('\'', '')
                scale = str(int(sheet.row(n)[5].value))
                depth_code = str(int(sheet.row(n)[7].value))
                try:
                    depth_unit = self.depth_codes[depth_code].upper().replace('/', ' AND ')
                except:
                    # print 'error finding depth unit for', chart_number, depth_code
                    depth_unit = 'UNKNOWN'
                d = Data(chart_number, suffix, panel_number, name, scale, depth_unit)
                s = stamp_from_detail(chart_number, suffix, panel_number)
                self.charts[s] = d

    def _read_editions(self):
        sheet = self.xls.sheet_by_name('Edition date & latest NM')
        for n in range(sheet.nrows):
            if n > 0:
                chart_number = str(int(sheet.row(n)[1].value))
                try:
                    year, month, day, _, __, ___ = xlrd.xldate_as_tuple(sheet.row(n)[3].value, self.xls.datemode)
                    # edition = datetime.datetime(*xlrd.xldate_as_tuple(edi, self.xls.datemode))
                    edition = '%s/%s/%s' % (month, day, year)
                    for data in self.charts.values():
                        if data.chart_number == chart_number:
                            data.set_updated(edition)
                except:
                    pass

    def _read_coords(self):
        xls_path = config.ukho_chart_data
        xls = xlrd.open_workbook(xls_path)
        sheet = xls.sheet_by_name('Chart Vertices')

        data_to_close_coords = set()

        for n in range(sheet.nrows):
            if n > 0:
                try:
                    chart_number = str(int(sheet.row(n)[1].value))
                    suffix = str(sheet.row(n)[2].value).strip()
                    panel_number = str(int(sheet.row(n)[3].value))

                    lat_cell = str(sheet.row(n)[5].value)
                    i = max(0, lat_cell.find('.') - 2)
                    lat_deg = lat_cell[:i]
                    if lat_deg == '-' or lat_deg == '':
                        lat_deg += '0'
                    lat_min = lat_cell[i:]

                    lng_cell = str(sheet.row(n)[6].value)
                    i = max(0, lng_cell.find('.') - 2)
                    lng_deg = lng_cell[:i]
                    if lng_deg == '-' or lng_deg == '':
                        lng_deg += '0'

                    lng_min = lng_cell[i:]

                    lat_dmm = lat_deg + ' ' + lat_min
                    lng_dmm = lng_deg + ' ' + lng_min

                    s = stamp_from_detail(chart_number, suffix, panel_number)
                    self.charts[s].coords.append(_lat_lng_dmm_to_ddd(lat_dmm, lng_dmm))
                    data_to_close_coords.add(self.charts[s])
                except:
                    pass

        # close polygons
        for ea in data_to_close_coords:
            ea.coords.append(ea.coords[0])

    def get_data(self, tif_path):
        s = stamp(tif_path)
        return self.charts[s]


# if __name__ == '__main__':
        #     ml = MetaLookup()
#     tp = os.path.join(config.ukho_geotiff_dir, '2182A-0.png')
#     print file_name_decoder(tp)
#     print stamp(tp)
#     data = ml.get_data(tp)
#     print 'chart number:', data.chart_number
#     print 'panel number:', data.panel_number
#     print 'suffix:', data.suffix
#     print 'name:', data.name
#     print 'scale:', data.scale
#     print 'depths:', data.depth_units
#     print 'updated:', data.updated
#     # print 'zoom', data.get_zoom()
        #     print 'outline', data.get_outline()
#     print 'coords', data.coords