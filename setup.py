#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name = 'simpleubjson',
    version = '0.2',
    description = 'Simple universal binary json decoder/encoder for Python.',

    author = 'Alexander Shorin',
    author_email = 'kxepal@gmail.com',
    license = 'BSD',
    url = 'http://code.google.com/p/simpleubjson/',

    install_requires = [],
    test_suite = 'simpleubjson.tests',
    zip_safe = True,

    packages = ['simpleubjson', 'simpleubjson.tests'],
)
