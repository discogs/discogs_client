#!/usr/bin/env python

from setuptools import setup

setup(
        name='discogs-client',
        version='2.3.0',
        description='Official Python API client for Discogs',
        url='https://github.com/discogs/discogs_client',
        author='Discogs',
        author_email='api@discogsinc.com',
        test_suite='discogs_client.tests',
        classifiers=[
            'Development Status :: 7 - Inactive',
            'Environment :: Console',
            'License :: OSI Approved :: BSD License',
            'Natural Language :: English',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Communications',
            'Topic :: Utilities',
            ],
        install_requires=[
            'requests',
            'six',
            'oauthlib',
            ],
        packages=[
            'discogs_client',
            ],
        )
