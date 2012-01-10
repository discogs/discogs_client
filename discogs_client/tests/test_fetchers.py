import unittest
from discogs_client.tests import DiscogsClientTestCase
from discogs_client.exceptions import HTTPError

class FetcherTestCase(DiscogsClientTestCase):
    def test_memory_fetcher(self):
        """Client can fetch responses with MemoryFetcher"""
        self.m.artist(1)

        with self.assertRaises(HTTPError) as cm:
            self.m._get('/500')

        self.assertEqual(cm.exception.status_code, 500)

        with self.assertRaises(HTTPError):
            self.m.release(1).title

        self.assertIsNone(self.m._get('/204'))


def suite():
    suite = unittest.TestSuite()
    suite = unittest.TestLoader().loadTestsFromTestCase(FetcherTestCase)
    return suite

