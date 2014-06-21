#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2014 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

import imp
import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
    # http://wiki.python.org/moin/Distutils/Cookbook/AutoPackageDiscovery
    import os

    def is_package(path):
        return (
            os.path.isdir(path) and
            os.path.isfile(os.path.join(path, '__init__.py'))
        )

    def find_packages(path='.', base=""):
        """ Find all packages in path """
        packages = {}
        for item in os.listdir(path):
            dir = os.path.join(path, item)
            if is_package(dir):
                if base:
                    module_name = "%(base)s.%(item)s" % vars()
                else:
                    module_name = item
                packages[module_name] = dir
                packages.update(find_packages(dir, module_name))
        return packages

mod = imp.load_module('version',
                      *imp.find_module('version', ['./simpleubjson/']))

_chunks = [
    open('README.rst').read().strip(),
    '''
Changes
=======
''',
    open('CHANGES.rst').read().strip()
]

if sys.version_info[0] == 3:
    long_description = ''.join(map(lambda c: c, _chunks))
else:
    long_description = ''.join(_chunks)

setup(
    name='simpleubjson',
    version=mod.__version__,
    description='Simple universal binary json decoder/encoder for Python.',
    long_description=long_description,

    author='Alexander Shorin',
    author_email='kxepal@gmail.com',
    license='BSD',
    url='http://code.google.com/p/simpleubjson/',

    install_requires=[],
    test_suite='simpleubjson.tests',
    zip_safe=True,

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    packages=find_packages(),
)
