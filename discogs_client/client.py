import requests
import json
import oauth2
import urllib
import urlparse

from discogs_client import models
from discogs_client.exceptions import ConfigurationError, HTTPError
from discogs_client.helpers import update_qs

class Client(object):
    _base_url = 'http://api.discogs.com'
    _request_token_url = 'http://api.discogs.com/oauth/request_token'
    _authorize_url = 'http://www.discogs.com/oauth/authorize'
    _access_token_url = 'http://api.discogs.com/oauth/access_token'

    def __init__(self, user_agent, consumer_key=None, consumer_secret=None, access_token=None, access_secret=None):
        self.user_agent = user_agent
        self.verbose = False
        self.authenticated = False

        self._consumer = None
        self._oauth_client = None
        self._token = None

        if consumer_key and consumer_secret:
            self._consumer = oauth2.Consumer(consumer_key, consumer_secret)

            if access_token and access_secret:
                self._token = oauth2.Token(access_token, access_secret)
                self.authenticated = True

            self._oauth_client = oauth2.Client(self._consumer, self._token)

    def get_authorize_url(self, callback_url=None):
        # Forget existing tokens
        self._oauth_client = oauth2.Client(self._consumer)

        params = {}
        if callback_url:
            params['oauth_callback'] = callback_url
        postdata = urllib.urlencode(params)

        resp, content = self._oauth_client.request(self._request_token_url, 'POST', body=postdata)
        if resp['status'] != '200':
            raise HTTPError('Invalid response from request token URL.', int(resp['status']))
        self._token = dict(urlparse.parse_qsl(content))

        params = {'oauth_token': self._token['oauth_token']}
        query_string = urllib.urlencode(params)

        return '?'.join((self._authorize_url, query_string))

    def get_access_token(self, verifier):
        token = oauth2.Token(
            self._token['oauth_token'],
            self._token['oauth_token_secret'],
        )
        token.set_verifier(verifier)
        self._oauth_client = oauth2.Client(self._consumer, token)

        resp, content = self._oauth_client.request(self._access_token_url, 'POST')
        self._token = dict(urlparse.parse_qsl(content))

        token = oauth2.Token(
            self._token['oauth_token'],
            self._token['oauth_token_secret'],
        )
        self._oauth_client = oauth2.Client(self._consumer, token)
        self.authenticated = True

        return self._token['oauth_token'], self._token['oauth_token_secret']

    def _check_user_agent(self):
        if not self.user_agent:
            raise ConfigurationError('Invalid or no User-Agent set.')

    def _request(self, method, url, data=None):
        if self.verbose:
            print ' '.join((method, url))

        headers = {
            'Accept-Encoding': 'gzip',
            'User-Agent': self.user_agent,
        }

        if data:
            headers['Content-Type'] = 'application/json'

        if self.authenticated:
            if data:
                body = json.dumps(data)
                resp, content = self._oauth_client.request(url, method, body, headers=headers)
            else:
                resp, content = self._oauth_client.request(url, method, headers=headers)
            status_code = int(resp['status'])
        else:
            response = requests.request(method, url, data=data, headers=headers)
            content = response.content
            status_code = response.status_code

        if status_code == 204:
            return None

        body = json.loads(content)

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
        if query:
            fields['q'] = ' '.join(query)

        return models.MixedPaginatedList(
            self,
            update_qs(self._base_url + '/database/search', fields),
            'results'
        )

    def artist(self, id):
        return models.Artist(self, {'id': id})

    def release(self, id):
        return models.Release(self, {'id': id})

    def master(self, id):
        return models.Master(self, {'id': id})

    def label(self, id):
        return models.Label(self, {'id': id})

    def user(self, username):
        return models.User(self, {'username': username})

    def listing(self, id):
        return models.Listing(self, {'id': id})

    def order(self, id):
        return models.Order(self, {'id': id})

    def fee_for(self, price, currency='USD'):
        resp = self._get(self._base_url + '/marketplace/fee/%f/%s' % (float(price), currency))
        return models.Price(self, {'value': resp['value'], 'currency': resp['currency']})

    def identity(self):
        resp = self._get(self._base_url + '/oauth/identity')
        return models.User(self, resp)
