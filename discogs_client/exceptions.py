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
        self.msg = '%d: %s' % (code, message)

    def __str__(self):
        return self.msg
