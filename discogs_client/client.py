from __future__ import absolute_import, division, print_function, unicode_literals

import warnings
import json
try:
    # python2
    from urllib import urlencode
except ImportError:
    # python3
    from urllib.parse import urlencode

from discogs_client import models
from discogs_client.exceptions import ConfigurationError, HTTPError, AuthorizationError
from discogs_client.utils import update_qs
from discogs_client.fetchers import RequestsFetcher, OAuth2Fetcher, UserTokenRequestsFetcher


class Client(object):
    _base_url = 'https://api.discogs.com'
    _request_token_url = 'https://api.discogs.com/oauth/request_token'
    _authorize_url = 'https://www.discogs.com/oauth/authorize'
    _access_token_url = 'https://api.discogs.com/oauth/access_token'

    def __init__(self, user_agent, consumer_key=None, consumer_secret=None, token=None, secret=None, user_token=None):
        """An interface to the Discogs API."""
        self.user_agent = user_agent
        self.verbose = False
        self._fetcher = RequestsFetcher()

        if consumer_key and consumer_secret:
            self.set_consumer_key(consumer_key, consumer_secret)
            if token and secret:
                self.set_token(token, secret)
        elif user_token is not None:
            self._fetcher = UserTokenRequestsFetcher(user_token)

    def set_consumer_key(self, consumer_key, consumer_secret):
        self._fetcher = OAuth2Fetcher(consumer_key, consumer_secret)

    def set_token(self, token, secret):
        try:
            self._fetcher.store_token(token, secret)
        except AttributeError:
            raise ConfigurationError('You must first set the consumer key and secret.')

    def get_authorize_url(self, callback_url=None):
        """
        Returns a tuple of (<access_token>, <access_secret>, <authorize_url>).
        Send a Discogs user to the authorize URL to get the verifier for the access token.
        """
        # Forget existing tokens
        self._fetcher.forget_token()

        params = {}
        params['User-Agent'] = self.user_agent
        params['Content-Type'] = 'application/x-www-form-urlencoded'
        if callback_url:
            params['oauth_callback'] = callback_url
        postdata = urlencode(params)

        content, status_code = self._fetcher.fetch(self, 'POST', self._request_token_url, data=postdata, headers=params)
        if status_code != 200:
            raise AuthorizationError('Could not get request token.', status_code, content)

        token, secret = self._fetcher.store_token_from_qs(content)

        params = {'oauth_token': token}
        query_string = urlencode(params)

        return (token, secret, '?'.join((self._authorize_url, query_string)))

    def get_access_token(self, verifier):
        """
        Uses the verifier to exchange a request token for an access token.
        """
        if isinstance(verifier, bytes):
            verifier = verifier.decode('utf8')

        self._fetcher.set_verifier(verifier)

        params = {}
        params['User-Agent'] = self.user_agent

        content, status_code = self._fetcher.fetch(self, 'POST', self._access_token_url, headers=params)
        if status_code != 200:
            raise HTTPError('Invalid response from access token URL.', status_code)

        token, secret = self._fetcher.store_token_from_qs(content)

        return token, secret

    def _check_user_agent(self):
        if not self.user_agent:
            raise ConfigurationError('Invalid or no User-Agent set.')

    def _request(self, method, url, data=None):
        if self.verbose:
            print(' '.join((method, url)))

        self._check_user_agent()

        headers = {
            'Accept-Encoding': 'gzip',
            'User-Agent': self.user_agent,
        }

        if data:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        content, status_code = self._fetcher.fetch(self, method, url, data=data, headers=headers)

        if status_code == 204:
            return None

        body = json.loads(content.decode('utf8'))

        if 200 <= status_code < 300:
            return body
        else:
            raise HTTPError(body['message'], status_code)

    def _get(self, url):
        return self._request('GET', url)

    def _delete(self, url):
        return self._request('DELETE', url)

    def _post(self, url, data):
        return self._request('POST', url, data)

    def _patch(self, url, data):
        return self._request('PATCH', url, data)

    def _put(self, url, data):
        return self._request('PUT', url, data)

    def search(self, *query, **fields):
        """
        Search the Discogs database. Returns a paginated list of objects
        (Artists, Releases, Masters, and Labels). The keyword arguments to this
        function are serialized into the request's query string.
        """
        if query:
            unicode_query = []
            for q in query:
                try:
                    unicode_q = q.decode('utf8')
                except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
                    unicode_q = q
                unicode_query.append(unicode_q)
            fields['q'] = ' '.join(unicode_query)
        return models.MixedPaginatedList(
            self,
            update_qs(self._base_url + '/database/search', fields),
            'results'
        )

    def artist(self, id):
        """Fetch an Artist by ID."""
        return models.Artist(self, {'id': id})

    def release(self, id):
        """Fetch a Release by ID."""
        return models.Release(self, {'id': id})

    def master(self, id):
        """Fetch a Master by ID."""
        return models.Master(self, {'id': id})

    def label(self, id):
        """Fetch a Label by ID."""
        return models.Label(self, {'id': id})

    def user(self, username):
        """Fetch a User by username."""
        return models.User(self, {'username': username})

    def listing(self, id):
        """Fetch a Marketplace Listing by ID."""
        return models.Listing(self, {'id': id})

    def order(self, id):
        """Fetch an Order by ID."""
        return models.Order(self, {'id': id})

    def fee_for(self, price, currency='USD'):
        """Calculate the fee for selling an item on the Marketplace."""
        resp = self._get('{0}/marketplace/fee/{1:.4f}/{2}'.format(self._base_url, price, currency))
        return models.Price(self, {'value': resp['value'], 'currency': resp['currency']})

    def identity(self):
        """Return a User object representing the OAuth-authorized user."""
        resp = self._get(self._base_url + '/oauth/identity')
        return models.User(self, resp)
