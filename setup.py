try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

#from statsd2prtg import __version__

config = {
    'description': 'Listen for statsd packets and send to PRTG.',
    'author': 'Jon Purdy',
    'url': 'n/a',
    'download_url': 'n/a',
    'author_email': 'jon@knowroaming.com',
    'version': 0.6,
    'install_requires': [
    'configparser',
    'requests',
    'docopt'
    ],
    # 'setup_requires': [
    # 'configparser',
    # 'requests'
    # ],
    'packages': ['statsd2prtg'],
    'scripts': [],
    'entry_points': {'console_scripts': ['statsd2prtg=statsd2prtg.__main__:main']},
    'name': 'statsd2prtg'
}

setup(**config)
