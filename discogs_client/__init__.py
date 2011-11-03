__version_info__ = (2,0,0)
__version__ = '2.0.0'

BASE_URL = 'http://appdev1.prod.discogs.com:8086'

from discogs_client.client import Client
from discogs_client.models import Artist, Release, Master, Label, User, \
    Listing, Track, Price, Video
