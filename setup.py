#!/usr/bin/env python

from setuptools import setup

setup(
        name='discogs-client',
        version='0.1',
        description='Official Python API client for Discogs',
        url='https://github.com/discogs/discogs-python-api-client',
        author='Discogs',
        author_email='api@discogs.com',
        classifiers=[
            'Development Status :: 4 - Beta',
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
            ],
        py_modules=[
            'discogs_client',
            ],
        )

