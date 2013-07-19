#!/usr/bin/python
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

import csv
import logging
import subprocess
import sys
import os

_LOG = logging.getLogger(__name__)


class SpacewalkClient(object):

    def __init__(self, host=None, ssh_key_path=None, local_dir=None):

        if not ssh_key_path and not local_dir:
            raise Exception("neither ssh key path or local dir were defined, aborting")
        self.host = host
        self.ssh_key_path = ssh_key_path
        self.local_dir = local_dir

    def _get_report(self, report_path):

        if self.host and self.ssh_key_path:
            # capture data from spacewalk
            process = subprocess.Popen(['/usr/bin/ssh', '-i', self.ssh_key_path, '-l', 'root', self.host, report_path],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ssh_stdout, ssh_stderr = process.communicate()

            if process.returncode != 0:
                _LOG.error("Error communicating with Satellite server at %s" %
                           self.host)
                _LOG.error(ssh_stderr)
                _LOG.error("Exiting.")
                sys.exit(process.returncode)

        elif self.local_dir:
            filepath = os.path.join(self.local_dir, report_path)
            # we do this so it matches the format of the ssh output
            ssh_stdout = open(filepath).read()

        # we need to re-encode so DictReader knows it's getting utf-8 data
        reader = csv.DictReader(ssh_stdout.decode('utf-8').encode('utf-8').splitlines())

        #XXX: suboptimal
        retval = []
        for r in reader:
            retval.append(r)

        return retval

    # TODO: these methods have a lot of duplicate code
    def get_system_list(self):
        return self._get_report('splice-export')

    def get_host_guest_list(self):
        return self._get_report('host-guests')

    def get_channel_list(self):
        return self._get_report('cloned-channels')

    def get_org_list(self):
        # we grab the full user list and then extract the orgs. This is not as
        # efficient as just getting the orgs from the db, but we may want to
        # create person consumers in the future.
        full_user_list = self._get_report('users')

        orgs = {}
        for u in full_user_list:
            orgs[u['organization_id']] = u['organization']

        return orgs

    def get_user_list(self):
        return self._get_report('users')
