#!/usr/bin/env python

from setuptools import setup

setup(
        name='discogs-client',
        version='2.0.1',
        description='Official Python API client for Discogs',
        url='https://github.com/discogs/discogs-python-client',
        author='Discogs',
        author_email='info@discogs.com',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
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
            'oauth2',
            ],
        packages=[
            'discogs_client',
            ],
        )

