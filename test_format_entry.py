from unittest import TestCase
from . import zdata


class Test_zdata(TestCase):
    def test_format_entry(self):
        entry = {
            "path": "/foo/bar/18476_1.KAP",
            "name": "PUGET SOUND SHILSHOLE BAY TO COMMENCEMENT BAY\n",
            "date": "today\n",
            "scale": 10000,
            "outline": "today\n",
            "depths": "FEET\r\n",
            "max_zoom": "1\n"
        }
        sql = zdata.format_entry("REGION_15", entry)
        self.assertEquals(len(sql) - 1, sql.rfind("\n"), "new line should be at the end")
        self.assertEquals(sql.find("\n"), sql.rfind("\n"), "there should only be one new line")

