import unittest
import json
import os
from discogs_client import Client
from discogs_client.fetchers import LoggingDelegator, FilesystemFetcher, \
    MemoryFetcher


class DiscogsClientTestCase(unittest.TestCase):
    def setUp(self):

        # Filesystem client
        self.d = Client('test_client/0.1 +http://example.org')
        self.d._base_url = ''
        self.d._fetcher = LoggingDelegator(
            FilesystemFetcher(os.path.dirname(os.path.abspath(__file__)) + '/res')
        )
        self.d._verbose = True

        # Memory client
        responses = {
            '/artists/1': (b'{"id": 1, "name": "Badger"}', 200),
            '/500': (b'{"message": "mushroom"}', 500),
            '/204': (b'', 204),
        }
        self.m = Client('ua')
        self.m._base_url = ''
        self.m._fetcher = LoggingDelegator(MemoryFetcher(responses))

    def tearDown(self):
        pass

    def assertGot(self, assert_url):
        method, url, data, headers = self.d._fetcher.last_request
        self.assertEqual(method, 'GET')
        self.assertEqual(url, assert_url)

    def assertPosted(self, assert_url, assert_data):
        method, url, data, headers = self.d._fetcher.last_request
        self.assertEqual(method, 'POST')
        self.assertEqual(url, assert_url)
        self.assertEqual(data, json.dumps(assert_data))


def suite():
    from discogs_client.tests import test_core, test_models, test_fetchers
    suite = unittest.TestSuite(test_core.suite())
    suite = unittest.TestSuite(test_models.suite())
    suite = unittest.TestSuite(test_fetchers.suite())
    return suite
