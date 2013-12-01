#!/usr/bin/env python

__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2013, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''This is a database of sorts for nautical chart regions, their providing hydro-graphic offices
   and additional information such as a listing of files or description.
'''

import os.path

import config
from noaaxml import NoaaXmlReader
import lookups


class MapPathSearch:
    def __init__(self, directory, map_extensions=['kap', 'tif'], include_only=None):
        """Searches for files ending with <map_extensions> in <directory> and all subdirectories

           Optionally supply set of file names <include_only> to only return paths of files that
           are contained in the set eg. {file1.kap, file2.tif}

           file_paths is a list of all full paths found
        """

        for i in range(len(map_extensions)):
            map_extensions[i] = map_extensions[i].upper()

        self.file_paths = []

        if os.path.isdir(directory):
            os.path.walk(directory, self.__walker, (tuple(map_extensions), include_only))
        else:
            print directory, 'is not a directory.'

    def __walker(self, args, p_dir, p_file):
        map_extensions, include_only = args
        for f in p_file:
            if f.upper().endswith(map_extensions) and (include_only is None or f in include_only) and not f.startswith(
                    "."):
                self.file_paths.append(os.path.join(p_dir, f))


class _RegionInfo:
    def __init__(self, desc, map_type):
        self.description = desc
        self.map_type = map_type


class _RegionDatabase:
    def __init__(self):
        self.db = {}
        self.rdb = {}
        self.provider_dirs = {}

    def add_provider(self, provider, map_dir):
        if not provider in self.db:
            self.db[provider] = {}
        self.provider_dirs[provider] = map_dir

    def add_region(self, provider, region, desc, map_type):
        if provider in self.db:
            self.db[provider][region] = _RegionInfo(desc, map_type)
            self.rdb[region] = provider

    def provider_for_region(self, region):
        region = region.upper()
        if region in self.rdb:
            return self.rdb[region]

        return None

    def get_description(self, provider, region):
        if provider in self.db and region in self.db[provider]:
            return self.db[provider][region].description

    def get_map_type(self, provider, region):
        if provider in self.db and region in self.db[provider]:
            return self.db[provider][region].map_type

    def get_directory_for_provider(self, provider):
        if provider in self.provider_dirs:
            return self.provider_dirs[provider]

    def provider_has_region(self, provider, region):
        return provider in self.db and region in self.db[provider]

    def is_valid_region(self, region):
        return region in self.rdb.keys()

#Chart format types
map_type_bsb = 'kap'
map_type_geotiff = 'tif'

#Providers
privider_noaa = 'noaa'
provider_brazil = 'brazil'
provider_linz = 'linz'
provider_ukho = 'ukho'
provider_wavey_lines = 'wavey-lines'

#Build the database
_db = _RegionDatabase()

#US - NOAA
_db.add_provider(privider_noaa, config.noaa_bsb_dir)
_db.add_region(privider_noaa, 'REGION_02', 'Block Island RI to the Canadian Border', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_02', 'Block Island RI to the Canadian Border', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_03', 'New York to Nantucket and Cape May NJ', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_04', 'Chesapeake and Delaware Bays', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_06', 'Norfolk VA to Florida including the ICW', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_07', 'Florida East Coast and the Keys', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_08', 'Florida West Coast and the Keys', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_10', 'Puerto Rico and the U.S. Virgin Islands', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_12', 'Southern California, Point Arena to the Mexican Border', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_13', 'Lake Michigan', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_14', 'San Francisco to Cape Flattery', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_15', 'Pacific Northwest, Puget Sound to the Canadian Border', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_17', 'Mobile AL to the Mexican Border', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_22', 'Lake Superior and Lake Huron (U.S. Waters)', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_24', 'Lake Erie (U.S. Waters)', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_26', 'Lake Ontario (U.S. Waters)', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_30', 'Southeast Alaska', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_32', 'South Central Alaska, Yakutat to Kodiak', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_34', 'Alaska, The Aleutians and Bristol Bay', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_36', 'Alaska, Norton Sound to Beaufort Sea', map_type_bsb)
_db.add_region(privider_noaa, 'REGION_40', 'Hawaiian Islands and U.S. Territories', map_type_bsb)

#BRAZIL NAVY
_db.add_provider(provider_brazil, config.brazil_bsb_dir)
_db.add_region(provider_brazil, 'REGION_BR', 'Brazil: Guyana to Uruguay', map_type_bsb)

#New Zealand - LINZ
_db.add_provider(provider_linz, config.linz_bsb_dir)
_db.add_region(provider_linz, 'REGION_NZ', 'New Zealand and South Pacific: Samoa to Ross Sea', map_type_bsb)

#United Kingdom - UKHO
_db.add_provider(provider_ukho, config.ukho_geotiff_dir)
_db.add_region(provider_ukho, 'REGION_UK1', 'United Kingdom North East Coast to Shetland Islands', map_type_geotiff)
_db.add_region(provider_ukho, 'REGION_UK2', 'United Kingdom South East Coast and Channel Islands', map_type_geotiff)
_db.add_region(provider_ukho, 'REGION_UK3', 'United Kingdom North West Coast and Ireland West Coast', map_type_geotiff)
_db.add_region(provider_ukho, 'REGION_UK4', 'United Kingdom South West Coast and Ireland East Coast - Irish Sea',
               map_type_geotiff)


def description_for_region(region):
    """returns the description for region defined in regions.py"""
    provider = _db.provider_for_region(region)
    region = region.upper()
    return _db.get_description(provider, region)


def map_type_for_region(region):
    """returns the regions map type file extension eg. tif or kap"""
    provider = _db.provider_for_region(region)
    region = region.upper()
    return _db.get_map_type(provider, region)


def map_list_for_region(region):
    """returns a list of absolute paths to chart files for queried region"""
    provider = _db.provider_for_region(region)
    region = region.upper()
    if _db.provider_has_region(provider, region):
        if provider is privider_noaa:
            reader = NoaaXmlReader(region)
            mps = MapPathSearch(config.noaa_bsb_dir, [map_type_for_region(region)], reader.get_map_files())
            return mps.file_paths
        elif provider is provider_ukho:
            return None  # TODO:
        else:
            mps = MapPathSearch(config.noaa_bsb_dir, [map_type_for_region(region)])
            return mps.file_paths


def lookup_for_region(region):
    """returns the lookup class for queried region
       see lookups.py which are used to build the region's catalog
    """
    provider = _db.provider_for_region(region)
    if provider is provider_ukho:
        return lookups.UKHOLookup()
    else:
        return lookups.BsbLookup()


def provider_for_region(region):
    """returns the provider eg. noaa for queried region"""
    return _db.provider_for_region(region)


def directory_for_provider(provider):
    """returns the directory where chart files live for queried region"""
    provider = provider.lower()
    return _db.get_directory_for_provider(provider)


def is_valid_region(region):
    """returns True or False"""
    return _db.is_valid_region(region.upper())


def find_custom_region_path(region):
    """look for a custom regions' directory if this is not a known (invalid) region"""
    for root, dirs, files in os.walk(config.map_dir):
        if region in dirs:
            return os.path.join(root, region)

    return None