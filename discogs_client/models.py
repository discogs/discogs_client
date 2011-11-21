from discogs_client.exceptions import HTTPError
from discogs_client.helpers import parse_timestamp, update_qs

class BaseAPIObject(object):
    """A first-order API object that has a canonical endpoint of its own."""
    def __init__(self, client, dict_):
        self.data = dict_
        self.client = client
        self._known_invalid_keys = []

    def refresh(self):
        if self.data.get('resource_url'):
            data = self.client._get(self.data['resource_url'])
            self.data.update(data)

    # TODO: This needs to use the oauth2 client
    def delete(self):
        if self.data.get('resource_url'):
            self.client._delete(self.data['resource_url'])

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


# This is terribly cheesy, but makes the client API more consistent
class SecondaryAPIObject(object):
    """
    An object that wraps parts of a response and doesn't have its own
    endpoint.
    """
    def __init__(self, client, dict_):
        self.client = client
        self.data = dict_

    def fetch(self, key, default=None):
        return self.data.get(key, default)


class BasePaginatedResponse(object):
    """Base class for lists of objects spread across many URLs."""
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
        data = self.client._get(
            update_qs(self.url, {'page': 1, 'per_page': self._per_page})
        )
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
            data = self.client._get(
                update_qs(self.url, {'page': index, 'per_page': self._per_page})
            )
            self._pages[index] = [
                self._transform(item) for item in data[self._list_key]
            ]
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


class PaginatedList(BasePaginatedResponse):
    """A paginated list of objects of a particular class."""
    def __init__(self, client, url, key, class_):
        super(PaginatedList, self).__init__(client, url)
        self._list_key = key
        self.class_ = class_

    def _transform(self, item):
        return self.class_(self.client, item)


class MixedPaginatedList(BasePaginatedResponse):
    """A paginated list of objects identified by their type parameter."""
    def __init__(self, client, url, key):
        super(MixedPaginatedList, self).__init__(client, url)
        self._list_key = key

    def _transform(self, item):
        # In some cases, we want to map the 'title' key we get back in search
        # results to 'name'. This way, you can repr() a page of search results
        # without making 50 requests.
        if item['type'] in ('label', 'artist'):
            item['name'] = item['title']

        return CLASS_MAP[item['type']](self.client, item)


class Artist(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Artist, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/artists/%d' % dict_['id']

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
        return MixedPaginatedList(self.client, self.fetch('releases_url'), 'releases')

    def __repr__(self):
        return '<Artist %r %r>' % (self.id, self.name)


class Release(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Release, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/releases/%d' % dict_['id']

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
        return [Video(self.client, d) for d in self.fetch('videos', [])]

    @property
    def genres(self):
        return self.fetch('genres')

    @property
    def country(self):
        return self.fetch('country')

    @property
    def notes(self):
        return self.fetch('notes')

    @property
    def formats(self):
        return self.fetch('formats')

    @property
    def tracklist(self):
        return [Track(self.client, d) for d in self.fetch('tracklist', [])]

    @property
    def artists(self):
        return [Artist(self.client, d) for d in self.fetch('artists', [])]

    @property
    def credits(self):
        return [Artist(self.client, d) for d in self.fetch('extraartists', [])]

    @property
    def labels(self):
        return [Label(self.client, d) for d in self.fetch('labels', [])]

    @property
    def companies(self):
        return [Label(self.client, d) for d in self.fetch('companies', [])]

    @property
    def master(self):
        master_id = self.fetch('master_id')
        if master_id:
            return Master(self.client, {'id': master_id})
        else:
            return None

    def __repr__(self):
        return '<Release %r %r>' % (self.id, self.title)


class Master(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Master, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/masters/%d' % dict_['id']

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
        return PaginatedList(self.client, self.fetch('versions_url'), 'versions', Release)

    @property
    def styles(self):
        return self.fetch('styles')

    @property
    def genres(self):
        return self.fetch('genres')

    @property
    def videos(self):
        return [Video(self.client, d) for d in self.fetch('videos', [])]

    @property
    def main_release(self):
        return Release(self.client, {'id': self.fetch('main_release')})

    @property
    def tracklist(self):
        return [Track(self.client, d) for d in self.fetch('tracklist', [])]

    @property
    def images(self):
        return self.fetch('images')

    def __repr__(self):
        return '<Master %r %r>' % (self.id, self.title)


class Label(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Label, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/labels/%d' % dict_['id']

    @property
    def id(self):
        return self.fetch('id')

    @property
    def name(self):
        return self.fetch('name')

    @property
    def profile(self):
        return self.fetch('profile')

    @property
    def urls(self):
        return self.fetch('urls')

    @property
    def images(self):
        return self.fetch('images')

    @property
    def contact_info(self):
        return self.fetch('contact_info')

    @property
    def data_quality(self):
        return self.fetch('data_quality')

    @property
    def releases(self):
        return PaginatedList(self.client, self.fetch('releases_url'), 'releases', Release)

    @property
    def sublabels(self):
        return [Label(self.client, d) for d in self.fetch('sublabels', [])]

    @property
    def parent_label(self):
        parent_label_dict = self.fetch('parent_label')
        if parent_label_dict:
            return Label(self.client, parent_label_dict)
        else:
            return None

    def __repr__(self):
        return '<Label %r %r>' % (self.id, self.name)


class User(BaseAPIObject):
    def __init__(self, client, dict_):
        super(User, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/users/%s' % dict_['username']

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
        return parse_timestamp(self.fetch('registered'))

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
    def inventory(self):
        return PaginatedList(self.client, self.fetch('inventory_url'), 'listings', Listing)

    @property
    def wantlist(self):
        return Wantlist(self.client, self.fetch('wantlist_url'), 'wants', WantlistItem)

    @property
    def rank(self):
        return self.fetch('rank')

    def __repr__(self):
        return '<User %r %r>' % (self.id, self.username)


class WantlistItem(BaseAPIObject):
    def __init__(self, client, dict_):
        super(WantlistItem, self).__init__(client, dict_)

    @property
    def id(self):
        return self.fetch('id')

    @property
    def rating(self):
        return self.fetch('rating')

    @property
    def notes(self):
        return self.fetch('notes')

    @property
    def notes_public(self):
        return self.fetch('notes_public')

    @property
    def release(self):
        return Release(self.client, self.fetch('basic_information'))

    def __repr__(self):
        return '<WantlistItem %r %r>' % (self.id, self.release.title)


class Listing(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Listing, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/marketplace/listings/%d' % dict_['id']

    @property
    def id(self):
        return self.fetch('id')

    @property
    def status(self):
        return self.fetch('status')

    @property
    def price(self):
        return Price(self.client, self.fetch('price', {}))

    @property
    def allow_offers(self):
        return self.fetch('allow_offers')

    @property
    def condition(self):
        return self.fetch('condition')

    @property
    def sleeve_condition(self):
        return self.fetch('sleeve_condition')

    @property
    def ships_from(self):
        return self.fetch('ships_from')

    @property
    def comments(self):
        return self.fetch('comments')

    @property
    def audio(self):
        return self.fetch('audio')

    @property
    def posted(self):
        return parse_timestamp(self.fetch('posted'))

    @property
    def release(self):
        return Release(self.client, self.fetch('release'))

    @property
    def seller(self):
        return User(self.client, self.fetch('seller'))

    def __repr__(self):
        return '<Listing %r %r>' % (self.id, self.release.data['description'])


class Track(SecondaryAPIObject):
    @property
    def duration(self):
        return self.fetch('duration')

    @property
    def position(self):
        return self.fetch('position')

    @property
    def title(self):
        return self.fetch('title')

    @property
    def artists(self):
        return [Artist(self.client, d) for d in self.fetch('artists', [])]

    @property
    def credits(self):
        return [Artist(self.client, d) for d in self.fetch('extraartists', [])]

    def __repr__(self):
        return '<Track %r %r>' % (self.position, self.title)


class Price(SecondaryAPIObject):
    @property
    def currency(self):
        return self.fetch('currency')

    @property
    def value(self):
        return self.fetch('value')

    def __repr__(self):
        return '<Price %r %r>' % (self.value, self.currency)


class Video(SecondaryAPIObject):
    @property
    def duration(self):
        return self.fetch('duration')

    @property
    def embed(self):
        return self.fetch('embed')

    @property
    def title(self):
        return self.fetch('title')

    # The API returns this as 'uri' :\
    @property
    def url(self):
        return self.fetch('uri')

    @property
    def description(self):
        return self.fetch('description')

    def __repr__(self):
        return '<Video %r>' % (self.title)


# Only things that can show up in a MixedPaginatedList need to go here
CLASS_MAP = {
    'artist': Artist,
    'release': Release,
    'master': Master,
    'label': Label,
}
