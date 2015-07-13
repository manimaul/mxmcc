template = '''<?xml version="1.0" encoding="utf-8" ?>
<gpx version="1.1" creator="MTCW" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" xmlns:MTCW="http://www.mxmariner.com">
    <rte>
        <name>override</name>
        %s
    </rte>
</gpx>
'''

point = '<rtept lat="%s" lon="%s"></rtept>\n'


# def _lat_lng_dmm_to_ddd(lat_dmm, lng_dmm):
#     """converts lat,lng in degree-decimal minutes
#        to decimal degrees.
#
#     ex. latDmm, lngDmm = ('-28 59.803', '048 06.998')
#         latDmm, lngDmm = ('28.204', -000 34.086') """
#
#     lat_deg, lat_min = lat_dmm.split(" ")
#     lng_deg, lng_min = lng_dmm.split(" ")
#
#     if lat_deg.startswith('-'):
#         lat = float(lat_deg) - (float(lat_min) / 60)
#     else:
#         lat = float(lat_deg) + (float(lat_min) / 60)
#
#     if lng_deg.startswith('-'):
#         lng = float(lng_deg) - (float(lng_min) / 60)
#     else:
#         lng = float(lng_deg) + (float(lng_min) / 60)
#
#     return lat, lng
#
#
# name = '2552-0'
# inner = ''
#
# with open(name, 'r') as ovr:
#     for line in ovr.readlines():
#         print line
#         lat_dmm, lng_dmm = line.strip().split(',')
#         lat, lng = _lat_lng_dmm_to_ddd(lat_dmm, lng_dmm)
#         inner += point % (lat, lng)
#
# with open(name+'.gpx', 'w') as gpx:
#     gpx.write(template % inner)

if __name__ == '__main__':
    name = '17325_1'
    with open(name, 'rb') as f:
        inner = ''
        for ea in f.readlines():
            print ea
            _, lat, lng = ea.split(',')
            inner += point % (lat, lng)

    with open(name + '.gpx', 'w') as gpx:
        gpx.write(template % inner)
