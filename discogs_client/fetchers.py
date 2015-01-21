from __future__ import absolute_import, division, print_function, unicode_literals

import requests
from requests.api import request
from oauthlib import oauth1
import json
import os
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

    def __init__(self, base_path):
        self.base_path = base_path

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        url = url.replace(client._base_url, '')

        if json:
            base_name = ''.join((url[1:], '.json'))
        else:
            base_name = url[1:]

        path = os.path.join(self.base_path, base_name)
        try:
            with open(path, 'r') as f:
                content = f.read().encode('utf8')  # return bytes not unicode
            return content, 200
        except:
            return self.default_response


class MemoryFetcher(Fetcher):
    """Fetches from a dict of URL -> (content, status_code)."""
    default_response = json.dumps({'message': 'Resource not found.'}).encode('utf8'), 404

    def __init__(self, responses):
        self.responses = responses

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        return self.responses.get(url, self.default_response)
