from datetime import datetime
from urllib2 import quote

def parse_timestamp(timestamp):
    """Convert an ISO 8601 timestamp into a datetime."""
    return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')


def update_qs(url, params):
    """A not-very-intelligent function to glom parameters onto a query string."""
    joined_qs = '&'.join('='.join((str(k), quote(str(v)))) for k, v in params.iteritems())
    separator = '&' if '?' in url else '?'
    return url + separator + joined_qs


def omit_none(dict_):
    """Removes any key from a dict that has a value of None."""
    return dict((k, v) for k, v in dict_.iteritems() if v is not None)
