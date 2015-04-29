#!/usr/bin/env python2

from setuptools import setup
from src import __version__
setup(
    name = "TincInfo",
    version = __version__,
    packages = ['tinctools'],
    package_dir = {'tinctools': './src/'}
    )
