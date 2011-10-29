__version_info__ = (2,0,0)
__version__ = '2.0.0'

import requests
import json
import urllib
import httplib
import urlparse
from datetime import datetime
from collections import defaultdict

BASE_URL = 'http://api.discogs.com'


def _parse_timestamp(timestamp):
    """Convert an ISO 8601 timestamp into a datetime."""
    return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')


def _update_qs(url, params):
    """A not-very-intelligent function to glom parameters onto a query string."""
    joined_qs = '&'.join('='.join((str(k), str(v))) for k, v in params.iteritems())
    separator = '&' if '?' in url else '?'
    return url + separator + joined_qs


class DiscogsAPIError(Exception):
    """Root Exception class for Discogs API errors."""
    pass


class ConfigurationError(DiscogsAPIError):
    """Exception class for problems with the configuration of this client."""
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class HTTPError(DiscogsAPIError):
    """Exception class for HTTP errors."""
    def __init__(self, message, code):
        self.status_code = code
        self.msg = '{} {}: {}'.format(code, httplib.responses[code], message)

    def __str__(self):
        return self.msg


class Client(object):
    def __init__(self, user_agent, consumer_key=None, consumer_secret=None, access_key=None):
        self.user_agent = user_agent
        self.verbose = False

    def _check_user_agent(self):
        if self.user_agent:
            self._headers['user-agent'] = user_agent
        else:
            raise ConfigurationError("Invalid or no User-Agent set.")

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

    def search(self, query):
        # TODO: Other filtering parameters
        # TODO: Alias q to ql on the server side
        return MixedObjectList(
            self,
            _update_qs(BASE_URL + '/database/search', {'ql': query}),
            'results'
        )

    def artist(self, id):
        return Artist(self, {'id': id})

    def release(self, id):
        return Release(self, {'id': id})

    def master(self, id):
        return Master(self, {'id': id})

    def label(self, id):
        return Label(self, {'id': id})

    def user(self, username):
        return User(self, {'username': username})


class BaseAPIObject(object):
    def __init__(self, client, dict_):
        self.data = dict_
        self.client = client
        self._known_invalid_keys = []

    def refresh(self):
        if self.data.get('resource_url'):
            data = self.client._get(self.data['resource_url'])
            self.data.update(data)

    def fetch(self, key, default=None):
        if key in self._known_invalid_keys:
            return default

        try:
            return self.data[key]
        except KeyError:
            # Fetch the object if we don't know about this key.
            # It might exist but not be in our cache.
            self.refresh()
            try:
                return self.data[key]
            except:
                self._known_invalid_keys.append(key)
                return default


class PaginatedList(object):
    def __init__(self, client, url):
        self.client = client
        self.url = url
        self._num_pages = None
        self._num_items = None
        self._pages = {}
        self._per_page = 50
        self._list_key = 'items'

    @property
    def per_page(self):
        return self._per_page

    @per_page.setter
    def per_page(self, value):
        self._per_page = value
        self._invalidate()

    def _invalidate(self):
        self._pages = {}
        self._num_pages = None
        self._num_items = None

    def _load_pagination_info(self):
        data = self.client._get(_update_qs(self.url, {'page': 1, 'per_page': self._per_page}))
        self._num_pages = data['pagination']['pages']
        self._num_items = data['pagination']['items']

    @property
    def pages(self):
        if self._num_pages is None:
            self._load_pagination_info()
        return self._num_pages

    @property
    def count(self):
        if self._num_items is None:
            self._load_pagination_info()
        return self._num_items

    def page(self, index):
        if not index in self._pages:
            data = self.client._get(_update_qs(self.url, {'page': index, 'per_page': self._per_page}))
            self._pages[index] = [self._transform(item) for item in data[self._list_key]]
        return self._pages[index]

    def _transform(self, item):
        return item

    def __getitem__(self, index):
        page_index = index / self.per_page + 1
        offset = index % self.per_page

        try:
            page = self.page(page_index)
        except HTTPError, e:
            if e.status_code == 404:
                raise IndexError(e.msg)
            else:
                raise

        return page[offset]

    def __len__(self):
        return self.count

    def __iter__(self):
        for i in xrange(1, self.pages + 1):
            page = self.page(i)
            for item in page:
                yield item


class Artist(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Artist, self).__init__(client, dict_)
        self.data['resource_url'] = BASE_URL + '/artists/%d' % dict_['id']

    @property
    def id(self):
        return self.fetch('id')

    @property
    def name(self):
        return self.fetch('name')

    @property
    def real_name(self):
        return self.fetch('realname')

    @property
    def profile(self):
        return self.fetch('profile')

    @property
    def data_quality(self):
        return self.fetch('data_quality')

    @property
    def name_variations(self):
        return self.fetch('namevariations')

    @property
    def aliases(self):
        return [Artist(self.client, d) for d in self.fetch('aliases', [])]

    @property
    def members(self):
        return [Artist(self.client, d) for d in self.fetch('members', [])]

    @property
    def urls(self):
        return self.fetch('urls')

    @property
    def releases(self):
        return MixedObjectList(self.client, self.fetch('releases_url'), 'releases')

    def __repr__(self):
        return '<Artist %r %r>' % (self.id, self.name)


class Release(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Release, self).__init__(client, dict_)
        self.data['resource_url'] = BASE_URL + '/releases/%d' % dict_['id']

    @property
    def id(self):
        return self.fetch('id')

    @property
    def title(self):
        return self.fetch('title')

    @property
    def year(self):
        return self.fetch('year')

    @property
    def thumb(self):
        return self.fetch('thumb')

    @property
    def data_quality(self):
        return self.fetch('data_quality')

    @property
    def status(self):
        return self.fetch('status')

    @property
    def videos(self):
        return self.fetch('videos')

    @property
    def artists(self):
        return [Artist(self.client, d) for d in self.fetch('artists', [])]

    @property
    def credits(self):
        return [Artist(self.client, d) for d in self.fetch('extraartists', [])]

    @property
    def labels(self):
        return [Label(self.client, d) for d in self.fetch('labels', [])]

    def __repr__(self):
        return '<Release %r %r>' % (self.id, self.title)


class Master(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Master, self).__init__(client, dict_)
        self.data['resource_url'] = BASE_URL + '/masters/%d' % dict_['id']

    @property
    def id(self):
        return self.fetch('id')

    @property
    def title(self):
        return self.fetch('title')

    @property
    def data_quality(self):
        return self.fetch('data_quality')

    @property
    def versions(self):
        return ObjectList(self.client, self.fetch('versions_url'), 'versions', Release)

    def __repr__(self):
        return '<Master %r %r>' % (self.id, self.title)


class Label(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Label, self).__init__(client, dict_)
        self.data['resource_url'] = BASE_URL + '/labels/%d' % dict_['id']

    @property
    def id(self):
        return self.fetch('id')

    @property
    def name(self):
        return self.fetch('name')

    def __repr__(self):
        return '<Label %r %r>' % (self.id, self.name)


class User(BaseAPIObject):
    def __init__(self, client, dict_):
        super(User, self).__init__(client, dict_)
        self.data['resource_url'] = BASE_URL + '/users/%s' % dict_['username']

    @property
    def id(self):
        return self.fetch('id')

    @property
    def username(self):
        return self.fetch('username')

    @property
    def name(self):
        return self.fetch('name')

    @property
    def profile(self):
        return self.fetch('profile')

    @property
    def location(self):
        return self.fetch('location')

    @property
    def home_page(self):
        return self.fetch('home_page')

    @property
    def releases_contributed(self):
        return self.fetch('releases_contributed')

    @property
    def registered(self):
        return _parse_timestamp(self.fetch('registered'))

    @property
    def rating_average(self):
        return self.fetch('rating_avg')

    @property
    def num_collection(self):
        return self.fetch('num_collection')

    @property
    def num_wantlist(self):
        return self.fetch('num_wantlist')

    @property
    def num_lists(self):
        return self.fetch('num_lists')

    @property
    def rank(self):
        return self.fetch('rank')

    def __repr__(self):
        return '<User %r %r>' % (self.id, self.username)


class ObjectList(PaginatedList):
    """A paginated list of objects of a particular class."""
    def __init__(self, client, url, key, class_):
        super(ObjectList, self).__init__(client, url)
        self._list_key = key
        self.class_ = class_

    def _transform(self, item):
        return self.class_(self.client, item)


class MixedObjectList(PaginatedList):
    """A paginated list of objects identified by their type parameter."""
    def __init__(self, client, url, key):
        super(MixedObjectList, self).__init__(client, url)
        self._list_key = key

    def _transform(self, item):
        return CLASS_MAP[item['type']](self.client, item)


CLASS_MAP = {
    'artist': Artist,
    'release': Release,
    'master': Master,
    'label': Label,
}
