# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
from ConfigParser import SafeConfigParser

import re
import sys
import logging
from Queue import Queue
from threading import Thread

_LOG = logging.getLogger(__name__)


# Defaults are applied to each section in the config file.
DEFAULTS = {'num_threads': '1'}


def system_exit(errcode, message=None):
    if message:
        sys.stderr.write(str(message) + '\n')
    sys.exit(errcode)


def read_mapping_file(mappingfile):
    f = open(mappingfile)
    lines = f.readlines()
    dic_data = {}
    for line in lines:
        if re.match("^[a-zA-Z]", line):
            line = line.replace("\n", "")
            key, val = line.split(": ")
            dic_data[key] = val
    return dic_data


def cfg_init(config_file=None):
    CONFIG = SafeConfigParser(defaults=DEFAULTS)
    CONFIG.read(config_file)
    return CONFIG


def get_multi_sw_cfg(cfg):
    spacewalk_sections = filter(lambda x: x.startswith('spacewalk'),
                                cfg.sections())
    return spacewalk_sections

def create_org_name(name, prefix=""):
    """
    given a name, optionally add the prefix in a human-readable form.

    Ex: "Foo Org" from a satellite labelled "QA" would be "Foo Org (QA)"
    """
    if not prefix:
        return name

    return "%s (%s)" % (name, prefix)


def get_release():
    f = open('/etc/redhat-release')
    lines = f.readlines()
    f.close()
    # TODO: make this more robust
    try:
        # rhel
        release = "RHEL-" + str(lines).split(' ')[6].split('.')[0]
    except IndexError:
        # centos
        release = "RHEL-" + str(lines).split(' ')[2].split('.')[0]
    return release


def queued_work(worker_method, item_list, num_threads):
        def worker():
            while True:
                size = q.qsize()
                if (size % 10) == 0 and size != 0:
                    _LOG.info("%s items left to process" % size)

                # NB: when this throws the Empty exception, the thread
                # automatically dies.
                # http://docs.python.org/2/library/threading.html#thread-objects
                item = q.get()

                try:
                    return_list.append(worker_method(item))
                except Exception, e:
                    _LOG.error("Exception from worker: %s" % e)

                q.task_done()

        _LOG.debug("starting queue")
        q = Queue()
        return_list = []
        for i in range(num_threads):
            _LOG.debug("initializing worker #%i" % i)
            t = Thread(target=worker)
            t.daemon = True
            t.start()

        for item in item_list:
            q.put(item)
        _LOG.debug("starting workers")
        q.join()
        _LOG.debug("queue work is complete, returning %s items" % len(return_list))
        return return_list
