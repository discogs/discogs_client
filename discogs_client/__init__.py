from __future__ import absolute_import, division, print_function, unicode_literals

__version_info__ = 2, 2, 2
__version__ = '2.2.2'

from discogs_client.client import Client
from discogs_client.models import Artist, Release, Master, Label, User, \
    Listing, Track, Price, Video
