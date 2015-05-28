from __future__ import absolute_import, division, print_function, unicode_literals
import requests
from requests.api import request
from oauthlib import oauth1
import json
import os
import re
try:
    # python2
    from urlparse import parse_qsl
except ImportError:
    # python3
    from urllib.parse import parse_qsl


class Fetcher(object):
    """
    Base class for Fetchers, which wrap and normalize the APIs of various HTTP
    libraries.

    (It's a slightly leaky abstraction designed to make testing easier.)
    """
    def fetch(self, client, method, url, data=None, headers=None, json=True):
        """Fetch the given request

        Returns
        -------
        content : str (python2) or bytes (python3)
        status_code : int
        """
        raise NotImplementedError()


class LoggingDelegator(object):
    """Wraps a fetcher and logs all requests."""
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.requests = []

    @property
    def last_request(self):
        return self.requests[-1] if self.requests else None

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        self.requests.append((method, url, data, headers))
        return self.fetcher.fetch(client, method, url, data, headers, json)


class RequestsFetcher(Fetcher):
    """Fetches via HTTP from the Discogs API."""
    def fetch(self, client, method, url, data=None, headers=None, json=True):
        resp = requests.request(method, url, data=data, headers=headers)
        return resp.content, resp.status_code


class UserTokenRequestsFetcher(Fetcher):
    """Fetches via HTTP from the Discogs API using user_token authentication"""
    def __init__(self, user_token):
        self.user_token = user_token

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        resp = requests.request(method, url, params={'token':self.user_token},
                                data=data, headers=headers)
        return resp.content, resp.status_code


class OAuth2Fetcher(Fetcher):
    """Fetches via HTTP + OAuth 1.0a from the Discogs API."""
    def __init__(self, consumer_key, consumer_secret, token=None, secret=None):
        self.client = oauth1.Client(consumer_key, client_secret=consumer_secret)
        self.store_token(token, secret)

    def store_token_from_qs(self, query_string):
        token_dict = dict(parse_qsl(query_string))
        token = token_dict[b'oauth_token'].decode('utf8')
        secret = token_dict[b'oauth_token_secret'].decode('utf8')
        self.store_token(token, secret)
        return token, secret

    def forget_token(self):
        self.store_token(None, None)

    def store_token(self, token, secret):
        self.client.resource_owner_key = token
        self.client.resource_owner_secret = secret

    def set_verifier(self, verifier):
        self.client.verifier = verifier

    def fetch(self, client, method, url, data=None, headers=None, json_format=True):
        body = json.dumps(data) if json_format and data else data
        uri, headers, body = self.client.sign(url, http_method=method,
                                              body=data, headers=headers)

        resp = request(method, uri, headers=headers, data=body)
        return resp.content, resp.status_code


class FilesystemFetcher(Fetcher):
    """Fetches from a directory of files."""
    default_response = json.dumps({'message': 'Resource not found.'}).encode('utf8'), 404
    path_with_params = re.compile('(?P<dir>(\w+/)+)(?P<query>\w+)\?(?P<params>.*)')

    def __init__(self, base_path):
        self.base_path = base_path

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        url = url.replace(client._base_url, '')

        if json:
            base_name = ''.join((url[1:], '.json'))
        else:
            base_name = url[1:]

        path = os.path.join(self.base_path, base_name)

        # The exact path might not exist, but check for files with different
        # permutations of query parameters.
        if not os.path.exists(path):
            base_name = self.check_alternate_params(base_name, json)
            path = os.path.join(self.base_path, base_name)

        try:
            path = path.replace('?', '_')  # '?' is illegal in file names on Windows
            with open(path, 'r') as f:
                content = f.read().encode('utf8')  # return bytes not unicode
            return content, 200
        except:
            return self.default_response

    def check_alternate_params(self, base_name, json):
        """
        parse_qs() result is non-deterministic - a different file might be
        requested, making the tests fail randomly, depending on the order of parameters in the query.
        This fixes it by checking for matching file names with a different permutations of the parameters.
        """
        match = self.path_with_params.match(base_name)

        # No parameters in query - no match. Nothing to do.
        if not match:
            return base_name

        ext = '.json' if json else ''

        # The base name consists of one or more path elements (directories),
        # a query (discogs.com endpoint), query parameters, and possibly an extension like 'json'.
        # Extract these.
        base_dir = os.path.join(self.base_path, match.group('dir'))
        query = match.group('query')  # we'll need this to only check relevant filenames
        params_str = match.group('params')[:-len(ext)]  # strip extension if any
        params = set(params_str.split('&'))

        # List files that match the same query, possibly with different parameters
        filenames = [f for f in os.listdir(base_dir) if f.startswith(query)]
        for f in filenames:
            # Strip the query, the '?' sign (or its replacement) and the extension, if any
            params2_str = f[len(query) + 1:-len(ext)]
            params2 = set(params2_str.split('&'))
            if params == params2:
                return base_name.replace(params_str, params2_str)

        # No matching alternatives found - revert to original.
        return base_name


class MemoryFetcher(Fetcher):
    """Fetches from a dict of URL -> (content, status_code)."""
    default_response = json.dumps({'message': 'Resource not found.'}).encode('utf8'), 404

    def __init__(self, responses):
        self.responses = responses

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        return self.responses.get(url, self.default_response)
