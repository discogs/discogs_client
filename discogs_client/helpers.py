from datetime import datetime

def parse_timestamp(timestamp):
    """Convert an ISO 8601 timestamp into a datetime."""
    return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')


def update_qs(url, params):
    """A not-very-intelligent function to glom parameters onto a query string."""
    joined_qs = '&'.join('='.join((str(k), str(v))) for k, v in params.iteritems())
    separator = '&' if '?' in url else '?'
    return url + separator + joined_qs


def omit_none(dict_):
    return dict((k, v) for k, v in dict_.iteritems() if v is not None)


class Fetched(object):
    """
    An attribute that determines its value using the object's fetch() method.

    Shorthand for:

        @property
        def foo(self):
            return self.fetch('foo')
    """
    def __init__(self, name, settable=False):
        self.name = name
        self.settable = settable

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.fetch(self.name)

    def __set__(self, obj, value):
        if self.settable:
            pass
        raise AttributeError("can't set attribute")


def fetches(names, settable=False):
    """Helper that adds a batch of Fetched properties to a class."""
    def f(cls):
        for name in names:
            setattr(cls, name, Fetched(name, settable=settable))
        return cls
    return f
