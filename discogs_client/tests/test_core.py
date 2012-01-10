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
        with self.assertRaises(ConfigurationError) as cm:
            bad_client.artist(1).name

        self.assertIn('User-Agent', str(cm.exception))

    def test_caching(self):
        """Only perform a fetch when requesting missing data"""
        a = self.d.artist(1)

        self.assertEqual(a.id, 1)
        self.assertIsNone(self.d._fetcher.last_request)

        self.assertEqual(a.name, 'Persuader, The')
        self.assertGot('/artists/1')

        self.assertEqual(a.real_name, u'Jesper Dahlb\u00e4ck')
        self.assertEqual(len(self.d._fetcher.requests), 1)

        # Get a key that's not in our cache
        a.fetch('blorf')
        self.assertEqual(len(self.d._fetcher.requests), 2)
        self.assertIn('blorf', a._known_invalid_keys)

        # Now we know artists don't have blorves
        a.fetch('blorf')
        self.assertEqual(len(self.d._fetcher.requests), 2)

    def test_equality(self):
        """APIObjects of the same class are equal if their IDs are"""
        a1 = self.d.artist(1)
        a1_ = self.d.artist(1)
        a2 = self.d.artist(2)

        r1 = self.d.release(1)

        self.assertEqual(a1, a1_)
        self.assertEqual(a1, r1.artists[0])
        self.assertNotEqual(a1, r1)
        self.assertNotEqual(r1, ':D')

    def test_transform_datetime(self):
        """String timestamps are converted to datetimes"""
        registered = self.d.user('example').registered
        self.assertIsInstance(registered, datetime)

    def test_object_field(self):
        """APIObjects can have APIObjects as properties"""
        self.assertEqual(self.d.master(4242).main_release, self.d.release(79))

    def test_read_only_simple_field(self):
        """Can't write to a SimpleField when writable=False"""
        u = self.d.user('example')
        with self.assertRaises(AttributeError):
            u.rank = 9001

    def test_read_only_object_field(self):
        """Can't write to an ObjectField"""
        m = self.d.master(4242)
        with self.assertRaises(AttributeError):
            m.main_release = 'lol!'

    def test_pagination(self):
        """PaginatedLists are parsed correctly, indexable, and iterable"""
        results = self.d.artist(1).releases

        self.assertEqual(results.per_page, 50)
        self.assertEqual(results.pages, 2)
        self.assertEqual(results.count, 57)

        self.assertEqual(len(results), 57)
        self.assertEqual(len(results.page(1)), 50)

        with self.assertRaises(HTTPError) as cm:
            results.page(42)
        self.assertEqual(cm.exception.status_code, 404)

        with self.assertRaises(IndexError):
            results[3141592]

        self.assertEqual(results[0].id, 20209)
        self.assertIn(self.d.release(20209), results)

        # Changing pagination settings invalidates the cache
        results.per_page = 10
        self.assertIsNone(results._num_pages)

def suite():
    suite = unittest.TestSuite()
    suite = unittest.TestLoader().loadTestsFromTestCase(CoreTestCase)
    return suite
