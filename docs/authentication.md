## Authentication

There are two forms of authentication the Discogs API allows: OAuth and
Discogs Auth

OAuth is useful if you want to create an application where a user uses your app
as a proxy to make requests and change information about their Discogs account.
This includes profile information, collection and wantlist information, and
marketplace changes.

Discogs Auth is great as a simple solution for scripts that just want to use
endpoint that require authentication, or for users who are writing apps that
only represent a single user (e.g., writing a store-front for your Discogs
seller account).

We will cover both forms of authentication below.

### Discogs Authentication

This is the more simple of the two methods of authenticating. Assuming you have generated a Discogs User Token in your Discogs developer settings, you can simply supply your token to the `Client` class:

```python
import discogs_client as dc
ds = dc.Client('my_user_agent/1.0', user_token='my_user_token')
```

That's it! You are now free to make authenticated requests.

### OAuth Authentication

OAuth is an open protocol commonly used for authorization (and in this case, authentication as well). For more information on the OAuth specification, please visit the OAuth website: http://oauth.net/

A Discogs consumer key and consumer secret are required for OAuth, and we can supply these credentials in two ways:

Begin by importing the client library:
```python
import discogs_client as dc
```

1. Instantiating the `Client` class with the consumer key and secret:

    ```python
    ds = dc.Client(
        'my_user_agent/1.0',
        consumer_key='my_consumer_key',
        consumer_secret='my_consumer_secret'
    )
    ```

    You can also supply your OAuth token and token secret if you already have them saved, as so:

    ```python
    ds = dc.Client(
        'my_user_agent/1.0',
        consumer_key='my_consumer_key',
        consumer_secret='my_consumer_secret',
        token=u'my_token',
        secret=u'my_token_secret'
    )
    ```

2. Calling the `set_consumer_key()` method

    ```python
    ds = dc.Client('my_user_agent/1.0')
    ds.set_consumer_key('my_consumer_key', 'my_consumer_secret')
    ```

These two methods do the same thing; their use is up to your preference. 

From here, we need to finish the OAuth process.

* Get authorization URL

    ```python
    ds.get_authorize_url()
    ```

    This will return a tuple with the request token, request secret, and the authorization URL that your user needs to visit to accept your app's request to sign in on their behalf.

    If you are writing a web application, you can specify a `callback_url` string to this method to receive the request token and request secret in the HTTP response.

* Get OAuth access token

    Pass the OAuth verifier that you received after the user authorizes your app into this method. This will return a tuple with the access token and access token secret that finalizes the OAuth process.

    ```python
    d.get_access_token('verifier-here')
    ```

From here, you are free to make OAuth-based requests. A smoke-test to verify everything is working is to call the `identity()` method:

```python
me = ds.identity()
```

This will return a `User` object if everything is okay.
