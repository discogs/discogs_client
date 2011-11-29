from discogs_client.exceptions import HTTPError
from discogs_client.helpers import parse_timestamp, update_qs, omit_none, fetches

class BaseAPIObject(object):
    """A first-order API object that has a canonical endpoint of its own."""
    def __init__(self, client, dict_):
        self.data = dict_
        self.client = client
        self._known_invalid_keys = []
        self.changes = {}

    def refresh(self):
        if self.data.get('resource_url'):
            data = self.client._get(self.data['resource_url'])
            self.data.update(data)
            self.changes = {}

    def save(self):
        if self.data.get('resource_url'):
            # TODO: This should be PATCH
            self.client._post(self.data['resource_url'], self.changes)

            # Refresh the object, in case there were side-effects
            self.refresh()

    def delete(self):
        if self.data.get('resource_url'):
            self.client._delete(self.data['resource_url'])

    def fetch(self, key, default=None):
        if key in self._known_invalid_keys:
            return default

        try:
            # First, look in the cache of pending changes
            return self.changes[key]
        except KeyError:
            try:
                # Next, look in the potentially incomplete local cache
                return self.data[key]
            except KeyError:
                # Now refresh the object from its resource_url.
                # The key might exist but not be in our cache.
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


class Wantlist(PaginatedList):
    def add(self, release, notes=None, notes_public=None, rating=None):
        release_id = release.id if isinstance(release, Release) else release
        data = {
            'release_id': release_id,
            'notes': notes,
            'notes_public': notes_public,
            'rating': rating,
        }
        self.client._put(self.url + '/' + str(release_id), omit_none(data))

    def remove(self, release):
        release_id = release.id if isinstance(release, Release) else release
        self.client._delete(self.url + '/' + str(release_id))


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


@fetches(['id', 'name', 'real_name', 'profile', 'data_quality', 'name_variations', 'urls'])
class Artist(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Artist, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/artists/%d' % dict_['id']

    @property
    def aliases(self):
        return [Artist(self.client, d) for d in self.fetch('aliases', [])]

    @property
    def members(self):
        return [Artist(self.client, d) for d in self.fetch('members', [])]

    @property
    def groups(self):
        return [Artist(self.client, d) for d in self.fetch('groups', [])]

    @property
    def releases(self):
        return MixedPaginatedList(self.client, self.fetch('releases_url'), 'releases')

    def __repr__(self):
        return '<Artist %r %r>' % (self.id, self.name)


@fetches([
    'id', 'title', 'year', 'thumb', 'data_quality', 'status', 'genres',
    'country', 'notes', 'formats',
])
class Release(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Release, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/releases/%d' % dict_['id']

    @property
    def videos(self):
        return [Video(self.client, d) for d in self.fetch('videos', [])]

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


@fetches(['id', 'title', 'data_quality', 'styles', 'genres', 'images'])
class Master(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Master, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/masters/%d' % dict_['id']

    @property
    def versions(self):
        return PaginatedList(self.client, self.fetch('versions_url'), 'versions', Release)

    @property
    def videos(self):
        return [Video(self.client, d) for d in self.fetch('videos', [])]

    @property
    def main_release(self):
        return Release(self.client, {'id': self.fetch('main_release')})

    @property
    def tracklist(self):
        return [Track(self.client, d) for d in self.fetch('tracklist', [])]

    def __repr__(self):
        return '<Master %r %r>' % (self.id, self.title)


@fetches([
    'id', 'name', 'profile', 'urls', 'images', 'contact_info', 'data_quality',
])
class Label(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Label, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/labels/%d' % dict_['id']

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


@fetches([
    'id', 'username', 'releases_contributed', 'num_collection', 'num_wantlist',
    'num_lists', 'rank', 'rating_avg'
])
@fetches(['name', 'profile', 'location', 'home_page'], settable=True)
class User(BaseAPIObject):
    def __init__(self, client, dict_):
        super(User, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/users/%s' % dict_['username']

    @property
    def registered(self):
        return parse_timestamp(self.fetch('registered'))

    @property
    def inventory(self):
        return PaginatedList(self.client, self.fetch('inventory_url'), 'listings', Listing)

    @property
    def wantlist(self):
        return Wantlist(self.client, self.fetch('wantlist_url'), 'wants', WantlistItem)

    @property
    def collection_folders(self):
        resp = self.client._get(self.fetch('collection_folders_url'))
        return [CollectionFolder(self.client, d) for d in resp['folders']]

    def __repr__(self):
        return '<User %r %r>' % (self.id, self.username)


@fetches(['id', 'rating', 'notes', 'notes_public'])
class WantlistItem(BaseAPIObject):
    def __init__(self, client, dict_):
        super(WantlistItem, self).__init__(client, dict_)

    @property
    def release(self):
        return Release(self.client, self.fetch('basic_information'))

    def __repr__(self):
        return '<WantlistItem %r %r>' % (self.id, self.release.title)


# TODO: folder_id should be a Folder object; needs folder_url
# TODO: notes should be first-order (somehow); needs resource_url
@fetches(['id', 'rating', 'folder_id', 'notes'])
class CollectionItemInstance(BaseAPIObject):
    def __init__(self, client, dict_):
        super(CollectionItemInstance, self).__init__(client, dict_)

    @property
    def release(self):
        return Release(self.client, self.fetch('basic_information'))

    def __repr__(self):
        return '<CollectionItemInstance %r %r>' % (self.id, self.release.title)


@fetches(['id', 'name', 'count'])
class CollectionFolder(BaseAPIObject):
    def __init__(self, client, dict_):
        super(CollectionFolder, self).__init__(client, dict_)

    @property
    def releases(self):
        # TODO: Needs releases_url
        return PaginatedList(self.client, self.fetch('resource_url') + '/releases', 'releases', CollectionItemInstance)

    def __repr__(self):
        return '<CollectionFolder %r %r>' % (self.id, self.name)


@fetches([
    'id', 'status', 'allow_offers', 'condition', 'sleeve_condition',
    'ships_from', 'comments', 'audio',
])
class Listing(BaseAPIObject):
    def __init__(self, client, dict_):
        super(Listing, self).__init__(client, dict_)
        self.data['resource_url'] = client._base_url + '/marketplace/listings/%d' % dict_['id']

    @property
    def price(self):
        return Price(self.client, self.fetch('price', {}))

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


@fetches(['duration', 'position', 'title'])
class Track(SecondaryAPIObject):
    @property
    def artists(self):
        return [Artist(self.client, d) for d in self.fetch('artists', [])]

    @property
    def credits(self):
        return [Artist(self.client, d) for d in self.fetch('extraartists', [])]

    def __repr__(self):
        return '<Track %r %r>' % (self.position, self.title)


@fetches(['currency', 'value'])
class Price(SecondaryAPIObject):
    def __repr__(self):
        return '<Price %r %r>' % (self.value, self.currency)


@fetches(['duration', 'embed', 'title', 'description'])
class Video(SecondaryAPIObject):
    # The API returns this as 'uri' :\
    @property
    def url(self):
        return self.fetch('uri')

    def __repr__(self):
        return '<Video %r>' % (self.title)


# Only things that can show up in a MixedPaginatedList need to go here
CLASS_MAP = {
    'artist': Artist,
    'release': Release,
    'master': Master,
    'label': Label,
}
