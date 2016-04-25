try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Listen for statsd packets and send to PRTG.',
    'author': 'Jon Purdy',
    'url': 'n/a',
    'download_url': 'n/a',
    'author_email': 'jon@knowroaming.com',
    'version': '0.1',
    'install_requires': ['nose'],
    'packages': ['NAME'],
    'scripts': [],
    'name': 'statsd2prtg'
}

setup(**config)
