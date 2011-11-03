import requests
import json

from discogs_client import models, BASE_URL
from discogs_client.exceptions import ConfigurationError, HTTPError

class Client(object):
    def __init__(self, user_agent, consumer_key=None, consumer_secret=None, access_key=None):
        self.user_agent = user_agent
        self.verbose = False

    def _check_user_agent(self):
        if self.user_agent:
            self._headers['user-agent'] = user_agent
        else:
            raise ConfigurationError('Invalid or no User-Agent set.')

    def _request(self, method, url, data=None):
        if self.verbose:
            print ' '.join((method, url))

        response = requests.request(method, url, data=data)

        if response.status_code == 204:
            return None

        body = json.loads(response.content)

        if 200 <= response.status_code < 300:
            return body
        else:
            raise HTTPError(body['message'], response.status_code)

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

        return models.MixedObjectList(
            self,
            _update_qs(BASE_URL + '/database/search', fields),
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

