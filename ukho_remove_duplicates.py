import os
import shutil

import config
from ukho_xlrd_lookup import stamp


__author__ = 'Will Kamp'
__copyright__ = 'Copyright 2014, Matrix Mariner Inc.'
__license__ = 'BSD'
__email__ = 'will@mxmariner.com'
__status__ = 'Development'  # 'Prototype', 'Development', or 'Production'

'''Removes duplicate geotiff charts from the ukho collection
'''


def cmp_val(o1, o2):
    """
    :param o1: object 1 to compare
    :param o2: object 2 to compare
    :return: if o1 is less than o2
    """

    if '_' in o1 and '_' not in o2:
        return False

    if '_UD' in o1 and '_W' in o2:
        return False

    return True


def make_comparator(less_than):
    def compare(x, y):
        if less_than(x, y):
            return -1
        elif less_than(y, x):
            return 1
        else:
            return 0

    return compare


def inspect_lst(the_list):
    if len(the_list) > 1:
        the_list.sort(cmp=make_comparator(cmp_val))

        # print the_list
        while len(the_list) > 1:
            t = the_list.pop()
            print 'moving:', t

            if t is not None:
                t = os.path.join(config.ukho_geotiff_dir, t + '.tif')
                shutil.move(t, config.ukho_dup_dir)


def get_dictionary():
    # inspect_lst(['2706-2_W', '2706-2_UD'])
    # inspect_lst(['2706-2_UD', '2706-2_W'])
    # inspect_lst(['2706-2', '2706-2_UD'])
    # inspect_lst(['2706-2_W', '2706-2'])

    charts = {}

    for ea in os.listdir(config.ukho_geotiff_dir):
        f = ea.rstrip('.tif')
        key = stamp(ea)
        if key not in charts:
            charts[key] = [f]
        else:
            charts[key].append(f)

    return charts


def remove_duplicates():
    if not os.path.isdir(config.ukho_dup_dir):
        raise Exception('config not setup!, did you run config?')

    charts = get_dictionary()
    for k in charts.keys():
        inspect_lst(charts[k])


def has_duplicates():
    charts = get_dictionary()
    for k in charts.keys():
        if len(charts[k]) > 1:
            return True

    return False


if __name__ == '__main__':
    remove_duplicates()
