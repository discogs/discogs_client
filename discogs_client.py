__version_info__ = (1,1,1)
__version__ = '1.1.1'

import requests
import json
import urllib
import httplib
from collections import defaultdict

api_uri = 'http://api.discogs.com'
user_agent = None

class DiscogsAPIError(Exception):
    """Root Exception class for Discogs API errors."""
    pass


class UserAgentError(DiscogsAPIError):
    """Exception class for User-Agent problems."""
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class HTTPError(DiscogsAPIError):
    """Exception class for HTTP(lib) errors."""
    def __init__(self, code):
        self.code = code
        self.msg = httplib.responses[self.code]

    def __str__(self):
        return "HTTP status %i: %s." % (self.code, self.msg)


class PaginationError(DiscogsAPIError):
    """Exception class for issues with paginated requests."""
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class APIBase(object):
    def __init__(self):
        self._cached_response = None
        self._params = {}
        self._headers = { 'accept-encoding': 'gzip, deflate' }

    def __str__(self):
        return '<%s "%s">' % (self.__class__.__name__, self._id)

    def __repr__(self):
        return self.__str__().encode('utf-8')

    def _check_user_agent(self):
        if 'user_agent' in globals() and user_agent is not None:
            self._headers['user-agent'] = user_agent
        return 'user-agent' in self._headers and self._headers.get('user-agent')

    def _clear_cache(self):
        self._cached_response = None

    @property
    def _response(self):
        if not self._cached_response:
            if not self._check_user_agent():
                raise UserAgentError("Invalid or no User-Agent set.")
            self._cached_response = requests.get(self._uri, params=self._params, headers=self._headers)

        return self._cached_response

    @property
    def _uri_name(self):
        return self.__class__.__name__.lower()

    @property
    def _uri(self):
        return '%s/%s/%s' % (api_uri, self._uri_name, urllib.quote_plus(unicode(self._id).encode('utf-8')))

    @property
    def data(self):
        if self._response.content and self._response.status_code == 200:
            release_json = json.loads(self._response.content)
            return release_json.get('resp').get(self._uri_name)
        else:
            status_code = self._response.status_code
            raise HTTPError(status_code)

def _parse_credits(extraartists):
    """
    Parse release and track level credits
    """
    _credits = defaultdict(list)
    for artist in extraartists:
        role = artist.get('role')
        tracks = artist.get('tracks')

        artist_dict = {'artists': Artist(artist['name'], anv=artist.get('anv'))}

        if tracks:
            artist_dict['tracks'] = tracks

        _credits[role].append(artist_dict)
    return _credits

def _class_from_string(api_string):
    class_map = {
            'master': MasterRelease,
            'release': Release,
            'artist': Artist,
            'label': Label
    }

    return class_map[api_string]

class Artist(APIBase):
    def __init__(self, name, anv=None):
        self._id = name
        self._aliases = []
        self._namevariations = []
        self._releases = []
        self._anv = anv or None
        APIBase.__init__(self)

    def __str__(self):
        return '<%s "%s">' % (self.__class__.__name__, self._anv + '*' if self._anv else self._id)

    @property
    def name(self):
        return self._id

    @property
    def anv(self):
        return self._anv

    @property
    def aliases(self):
        if not self._aliases:
            for alias in self.data.get('aliases', []):
                self._aliases.append(Artist(alias))
        return self._aliases

    @property
    def releases(self):
        # TODO: Implement fetch many release IDs
        #return [Release(r.get('id') for r in self.data.get('releases')]
        if not self._releases:
            self._params.update({'releases': '1'})
            self._clear_cache()

            for r in self.data.get('releases', []):
                self._releases.append(_class_from_string(r['type'])(r['id']))
        return self._releases

class Release(APIBase):
    def __init__(self, id):
        self._id = id
        self._artists = []
        self._master = None
        self._labels = []
        self._credits = None
        self._tracklist = []
        APIBase.__init__(self)

    @property
    def artists(self):
        if not self._artists:
            self._artists = [Artist(a['name']) for a in self.data.get('artists', [])]
        return self._artists

    @property
    def master(self):
        if not self._master and self.data.get('master_id'):
            self._master = MasterRelease(self.data.get('master_id'))
        return self._master

    @property
    def labels(self):
        if not self._labels:
            self._labels =  [Label(l['name']) for l in self.data.get('labels', [])]
        return self._labels

    @property
    def credits(self):
        if not self._credits:
            self._credits = _parse_credits(self.data.get('extraartists', []))
        return self._credits

    @property
    def tracklist(self):
        if not self._tracklist:
            for track in self.data.get('tracklist', []):
                artists = []
                track['extraartists'] = _parse_credits(track.get('extraartists', []))

                for artist in track.get('artists', []):
                    artists.append(Artist(artist['name'], anv=artist.get('anv')))

                    if artist['join']:
                        artists.append(artist['join'])
                track['artists'] = artists
                track['type'] = 'Track' if track['position'] else 'Index Track'

                self._tracklist.append(track)
        return self._tracklist

    @property
    def title(self):
        return self.data.get('title')

class MasterRelease(APIBase):
    def __init__(self, id):
        self._id = id
        self._key_release = None
        self._versions = []
        self._artists = []
        APIBase.__init__(self)

    # Override class name introspection in BaseAPI since it would otherwise return "masterrelease"
    @property
    def _uri_name(self):
        return 'master'

    @property
    def key_release(self):
        if not self._key_release:
            self._key_release = Release(self.data.get('main_release'))
        return self._key_release

    @property
    def title(self):
        return self.key_release.data.get('title')

    @property
    def versions(self):
        if not self._versions:
            for version in self.data.get('versions', []):
                self._versions.append(Release(version.get('id')))
        return self._versions

    @property
    def artists(self):
        if not self._artists:
            for artist in self.data.get('artists', []):
                self._artists.append(Artist(artist.get('name')))
        return self._artists

    @property
    def tracklist(self):
        return self.key_release.tracklist

class Label(APIBase):
    def __init__(self, name):
        self._id = name
        self._sublabels = []
        self._parent_label = None
        APIBase.__init__(self)

    @property
    def sublabels(self):
        if not self._sublabels:
            for sublabel in self.data.get('sublabels', []):
                self._sublabels.append(Label(sublabel))
        return self._sublabels

    @property
    def parent_label(self):
        if not self._parent_label and self.data.get('parentLabel'):
            self._parent_label = Label(self.data.get('parentLabel'))
        return self._parent_label

    @property
    def releases(self):
        self._params.update({'releases': '1'})
        self._clear_cache()
        return self.data.get('releases')

class Search(APIBase):
    def __init__(self, query, page=1):
        self._id = query
        self._results = {}
        self._exactresults = []
        self._page = page
        APIBase.__init__(self)
        self._params['q'] = self._id
        self._params['page'] = self._page

    def _to_object(self, result):
        id = result['title']
        if result['type'] in ('master', 'release'):
            id = result['uri'].split('/')[-1]
        elif result['type'] == 'anv':
            return Artist(id, anv=result.get('anv'))
        return _class_from_string(result['type'])(id)

    @property
    def _uri(self):
        return '%s/%s' % (api_uri, self._uri_name)

    @property
    def exactresults(self):
        if not self.data:
            return []

        if not self._exactresults:
            for result in self.data.get('exactresults', []):
                self._exactresults.append(self._to_object(result))
        return self._exactresults

    def results(self, page=1):
        page_key = 'page%s' % page

        if page != self._page:
            if page > self.pages:
                raise PaginationError('Page number exceeds maximum number of pages returned.')
            self._params['page'] = page
            self._clear_cache()

        if not self.data:
            return []

        if page_key not in self._results:
            self._results[page_key] = []
            for result in self.data['searchresults']['results']:
                self._results[page_key].append(self._to_object(result))

        return self._results[page_key]

    @property
    def numresults(self):
        if not self.data:
            return 0
        return int(self.data['searchresults'].get('numResults', 0))

    @property
    def pages(self):
        if not self.data:
            return 0
        return (self.numresults / 20) + 1
