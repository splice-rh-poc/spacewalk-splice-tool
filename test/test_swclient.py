# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


from mock import Mock, patch
import socket
import sys

from base import SpliceToolTest

from spacewalk_splice_tool import checkin, katello_sync
from spacewalk_splice_tool import sw_client

class SwclientTest(SpliceToolTest):

    @patch('spacewalk_splice_tool.sw_client.SpacewalkClient._get_report')
    def test_flatten_orgs(self, mock_get_report):

        fake_system_list = [{'server_id': '123', 'organization': 'foo org', 'org_id': '1'},
                            {'server_id': '456', 'organization': 'bar org', 'org_id': '2'}, 
                            {'server_id': '789', 'organization': 'baz org', 'org_id': '3'}] 
        mock_get_report.return_value = fake_system_list
        swc = sw_client.SpacewalkClient(ssh_key_path='/not/used')
        sys_list = swc.get_system_list(flatten = True)
        for system in sys_list:
            self.assertEquals(system['organization'], 'flattened org') 
            self.assertEquals(system['org_id'], '1') 

        # org list is based on user list
        fake_user_list = [{'organization_id': '1', 'organization': 'foo org', 'user_id': 'user1'},
                          {'organization_id': '2', 'organization': 'bar org', 'user_id': 'user2'},
                          {'organization_id': '3', 'organization': 'baz org', 'user_id': 'user3'}]

        mock_get_report.return_value = fake_user_list
        org_list = swc.get_org_list(flatten = True)
        for org in org_list:
            self.assertEquals(system['organization'], 'flattened org') 
            self.assertEquals(system['org_id'], '1') 

