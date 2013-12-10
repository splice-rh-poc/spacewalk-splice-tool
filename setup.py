#!/usr/bin/env python
#
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from setuptools import setup, find_packages, Extension

setup(
    name="spacewalk_splice_tool",
    version='0.46',
    description='A utility to feed data from spacewalk into katello',
    author='Chris Duryee',
    author_email='cduryee@redhat.com',
    url='http://github.com/splice/spacewalk-splice-tool',
    license='GPLv2',

    test_suite = 'nose.collector',

    packages    = ["spacewalk_splice_tool"],
    package_dir = {"spacewalk_splice_tool" : "src/spacewalk_splice_tool" },

    classifiers = [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Programming Language :: Python'
    ],
)

