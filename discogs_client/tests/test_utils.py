import unittest
from datetime import datetime
from discogs_client.tests import DiscogsClientTestCase
from discogs_client import utils

class UtilsTestCase(DiscogsClientTestCase):
    def test_update_qs(self):
        """update_qs helper works as intended"""
        u = utils.update_qs
        self.assertEqual(u('http://example.com', {'foo': 'bar'}), 'http://example.com?foo=bar')
        self.assertEqual(u('http://example.com?foo=bar', {'foo': 'baz'}), 'http://example.com?foo=bar&foo=baz')
        self.assertEqual(u('http://example.com?c=3&a=yep', {'a': 1, 'b': '1'}), 'http://example.com?c=3&a=yep&a=1&b=1')

    def test_omit_none(self):
        o = utils.omit_none
        self.assertEqual(o({
            'foo': None,
            'baz': 'bat',
            'qux': None,
            'flan': 0,
        }), {
            'baz': 'bat',
            'flan': 0,
        })

        self.assertEqual(o(dict((k, None) for k in ('qux', 'quux', 'quuux'))), {})
        self.assertEqual(o({'nope': 'yep'}), {'nope': 'yep'})
        self.assertEqual(o({}), {})

    def test_parse_timestamp(self):
        p = utils.parse_timestamp
        self.assertEqual(p('2012-01-01T00:00:00'), datetime(2012, 1, 1, 0, 0, 0))
        self.assertEqual(p('2001-05-25T00:00:42'), datetime(2001, 5, 25, 0, 0, 42))

def suite():
    suite = unittest.TestSuite()
    suite = unittest.TestLoader().loadTestsFromTestCase(UtilsTestCase)
    return suite
