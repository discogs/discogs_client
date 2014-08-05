import requests
import oauth2
import json
import urlparse
import os

class Fetcher(object):
    """
    Base class for Fetchers, which wrap and normalize the APIs of various HTTP
    libraries.

    (It's a slightly leaky abstraction designed to make testing easier.)
    """
    def fetch(self, client, method, url, data=None, headers=None, json=True):
        # Should return (content, status_code)
        raise NotImplemented


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
        consumer = oauth2.Consumer(consumer_key, consumer_secret)
        token_obj = None

        if token and secret:
            token_obj = oauth2.Token(token, secret)

        self.oauth_client = oauth2.Client(consumer, token_obj)

    def store_token_from_qs(self, query_string):
        token_dict = dict(urlparse.parse_qsl(query_string))
        token = token_dict['oauth_token']
        secret = token_dict['oauth_token_secret']
        self.store_token(token, secret)
        return token, secret

    def forget_token(self):
        self.oauth_client.token = None

    def store_token(self, token, secret):
        self.oauth_client.token = oauth2.Token(token, secret)

    def set_verifier(self, verifier):
        self.oauth_client.token.set_verifier(verifier)

    def fetch(self, client, method, url, data=None, headers=None, json_format=True):
        if data:
            body = json.dumps(data) if json_format else data
            resp, content = self.oauth_client.request(url, method, body, headers=headers)
        else:
            resp, content = self.oauth_client.request(url, method, headers=headers)
        return content, int(resp['status'])


class FilesystemFetcher(Fetcher):
    """Fetches from a directory of files."""
    default_response = json.dumps({'message': 'Resource not found.'}), 404

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
                content = f.read()
            return content, 200
        except:
            return self.default_response


class MemoryFetcher(Fetcher):
    """Fetches from a dict of URL -> (content, status_code)."""
    default_response = json.dumps({'message': 'Resource not found.'}), 404

    def __init__(self, responses):
        self.responses = responses

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        return self.responses.get(url, self.default_response)
