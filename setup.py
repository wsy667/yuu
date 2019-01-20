import setuptools
from yuu.common import __version__

with open('README.md', 'r') as f:
    desc = f.read()

setuptools.setup(name = 'yuu',
version = __version__,
description = 'Yuu - A simple AbemaTV video ripper',
long_description = desc,
long_description_content_type = "text/markdown",
author = 'noaione',
author_email = 'noaione0809@gmail.com',
keywords = ['ripping', 'downloader', 'parser'],
license = 'GNU GPLv3',
url = 'https://github.com/noaione/yuu',
packages = setuptools.find_packages(),
install_requires = ['requests[socks]', 'm3u8', 'tqdm', 'pycryptodome', 'beautifulsoup4'],
classifiers = ['Development Status :: 5 - Production/Stable', 'Programming Language :: Python :: 3', 'Programming Language :: Python :: 3.5', 'Programming Language :: Python :: 3.6', 'Programming Language :: Python :: 3.7'],
entry_points = {
    'console_scripts': ['yuu=yuu.command:main']
})