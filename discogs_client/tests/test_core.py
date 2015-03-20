from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from discogs_client import Client
from discogs_client.tests import DiscogsClientTestCase
from discogs_client.exceptions import ConfigurationError, HTTPError
from datetime import datetime


class CoreTestCase(DiscogsClientTestCase):
    def test_user_agent(self):
        """User-Agent should be properly set"""
        self.d.artist(1).name

        bad_client = Client('')

        self.assertRaises(ConfigurationError, lambda: bad_client.artist(1).name)

        try:
            bad_client.artist(1).name
        except ConfigurationError as e:
            self.assertTrue('User-Agent' in str(e))

    def test_caching(self):
        """Only perform a fetch when requesting missing data"""
        a = self.d.artist(1)

        self.assertEqual(a.id, 1)
        self.assertTrue(self.d._fetcher.last_request is None)

        self.assertEqual(a.name, 'Persuader, The')
        self.assertGot('/artists/1')

        self.assertEqual(a.real_name, 'Jesper Dahlb\u00e4ck')
        self.assertEqual(len(self.d._fetcher.requests), 1)

        # Get a key that's not in our cache
        a.fetch('blorf')
        self.assertEqual(len(self.d._fetcher.requests), 2)
        self.assertTrue('blorf' in a._known_invalid_keys)

        # Now we know artists don't have blorves
        a.fetch('blorf')
        self.assertEqual(len(self.d._fetcher.requests), 2)

    def test_equality(self):
        """APIObjects of the same class are equal if their IDs are"""
        a1 = self.d.artist(1)
        a1_ = self.d.artist(1)
        self.d.artist(2)

        r1 = self.d.release(1)

        self.assertEqual(a1, a1_)
        self.assertEqual(a1, r1.artists[0])
        self.assertNotEqual(a1, r1)
        self.assertNotEqual(r1, ':D')

    def test_transform_datetime(self):
        """String timestamps are converted to datetimes"""
        registered = self.d.user('example').registered
        self.assertTrue(isinstance(registered, datetime))

    def test_object_field(self):
        """APIObjects can have APIObjects as properties"""
        self.assertEqual(self.d.master(4242).main_release, self.d.release(79))

    def test_read_only_simple_field(self):
        """Can't write to a SimpleField when writable=False"""
        u = self.d.user('example')

        def fail():
            u.rank = 9001
        self.assertRaises(AttributeError, fail)

    def test_read_only_object_field(self):
        """Can't write to an ObjectField"""
        m = self.d.master(4242)

        def fail():
            m.main_release = 'lol!'
        self.assertRaises(AttributeError, fail)

    def test_pagination(self):
        """PaginatedLists are parsed correctly, indexable, and iterable"""
        results = self.d.artist(1).releases

        self.assertEqual(results.per_page, 50)
        self.assertEqual(results.pages, 2)
        self.assertEqual(results.count, 57)

        self.assertEqual(len(results), 57)
        self.assertEqual(len(results.page(1)), 50)

        self.assertRaises(HTTPError, lambda: results.page(42))

        try:
            results.page(42)
        except HTTPError as e:
            self.assertEqual(e.status_code, 404)

        self.assertRaises(IndexError, lambda: results[3141592])

        self.assertEqual(results[0].id, 20209)
        self.assertTrue(self.d.release(20209) in results)

        # Changing pagination settings invalidates the cache
        results.per_page = 10
        self.assertTrue(results._num_pages is None)


def suite():
    suite = unittest.TestSuite()
    suite = unittest.TestLoader().loadTestsFromTestCase(CoreTestCase)
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
