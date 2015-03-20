from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from discogs_client.tests import DiscogsClientTestCase
from discogs_client.exceptions import HTTPError


class FetcherTestCase(DiscogsClientTestCase):
    def test_memory_fetcher(self):
        """Client can fetch responses with MemoryFetcher"""
        self.m.artist(1)

        self.assertRaises(HTTPError, lambda: self.m._get('/500'))

        try:
            self.m._get('/500')
        except HTTPError as e:
            self.assertEqual(e.status_code, 500)

        self.assertRaises(HTTPError, lambda: self.m.release(1).title)
        self.assertTrue(self.m._get('/204') is None)


def suite():
    suite = unittest.TestSuite()
    suite = unittest.TestLoader().loadTestsFromTestCase(FetcherTestCase)
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
