#!/usr/bin/env python

__author__ = "Will Kamp"
__copyright__ = "Copyright 2015, Matrix Mariner Inc."
__license__ = "BSD"
__email__ = "will@mxmariner.com"
__status__ = "Development"  # "Prototype", "Development", or "Production"

'''Store tiling process checkpoints, so successful steps don't have to be repeated
'''

import os

from enum import Enum

import config


class OrderedEnum(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self._value_ >= other._value_
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self._value_ > other._value_
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self._value_ <= other._value_
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self._value_ < other._value_
        return NotImplemented


class CheckPoint(OrderedEnum):
    CHECKPOINT_NOT_STARTED, CHECKPOINT_CATALOG, CHECKPOINT_TILE_VERIFY, CHECKPOINT_MERGE, CHECKPOINT_OPT, \
    CHECKPOINT_ENCRYPTED, CHECKPOINT_ARCHIVE, CHECKPOINT_METADATA = range(8)

    @classmethod
    def from_string(cls, str_value):
        str_value = str_value[str_value.find('.') + 1:]
        return getattr(cls, str_value, CheckPoint.CHECKPOINT_NOT_STARTED)


class CheckPointStore:
    def __init__(self):
        self._p_path = os.path.join(config.catalog_dir, 'checkpoint.txt')
        self.checkpoints = {}
        self._read()

    def _read(self):
        if not os.path.exists(self._p_path):
            return

        store = open(self._p_path, 'r')
        lines = store.readlines()
        if len(lines) > 0:
            for ea in lines:
                values = ea.strip().split('\t')
                if len(values) is 3:
                    r, p, c = values
                    self._set_checkpoint_internal(r, p, CheckPoint.from_string(c))

        store.close()
        self._commit()

    def _set_checkpoint_internal(self, region, profile, checkpoint):
        if region in self.checkpoints:
            self.checkpoints[region][profile] = checkpoint
        else:
            self.checkpoints[region] = {profile: checkpoint}

    def clear_checkpoint(self, region, profile, checkpoint):
        self._set_checkpoint_internal(region, profile, checkpoint)
        self._commit()

    def get_checkpoint(self, region, profile):
        if region in self.checkpoints:
            p = self.checkpoints[region]
            if profile in p:
                return p[profile]

        return CheckPoint.CHECKPOINT_NOT_STARTED

    def _commit(self):
        store = open(self._p_path, 'w+')
        for region in self.checkpoints:
            for profile in self.checkpoints[region]:
                store.write('%s\t%s\t%s\n' % (region, profile, self.checkpoints[region][profile]))
        store.close()


# if __name__ == '__main__':
#     store = CheckPointStore()
#     region = 'REGION_UK1'
#     profile = 'MX_REGION'
#     print store.get_checkpoint(region, profile)
#     store.clear_checkpoint(region, profile, CheckPoint.CHECKPOINT_CATALOG)
#     print store.get_checkpoint(region, profile)
#     store.clear_checkpoint(region, profile, CheckPoint.CHECKPOINT_ARCHIVE)
#     print store.get_checkpoint(region, profile)
