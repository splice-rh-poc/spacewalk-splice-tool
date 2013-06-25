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

from mock import Mock, call

from spacewalk_splice_tool.checkin import KatelloPushSync

from base import SpliceToolTest


class TestObjectSync(SpliceToolTest):
    class Matcher(object):
        def __init__(self, compare, some_obj):
            self.compare = compare
            self.some_obj = some_obj
        def __eq__(self, other):
            return self.compare(self.some_obj, other)

    def user_compare(self, obj1, obj2):
        if obj1['username'] == obj2['username']:
            return True
        return False

    def true_compare(self, obj1, obj2):
        return True

    def setUp(self):
        super(TestObjectSync, self).setUp()

        cp_orgs = [
                   {'name': 'bar org', 'label': 'satellite-2',   'id': '9',   'description': 'no description'},
                   {'name': 'foo org', 'label': 'satellite-1',   'id': '7',   'description': 'no description'},
                   {'name': 'foo org', 'label': 'NOT-A-SAT-ORG', 'id': '100', 'description': 'no description'},
                  ]

        kt_userlist = [{'username': 'admin', 'id': 1, 'email': 'admin@foo.com'},
                        {'username': 'bazbaz', 'id': 3, 'email': 'bazbaz@foo.com'},
                        {'username': 'foo', 'id': 2, 'email': 'bazbaz@foo.com'}]

        kt_roles_for_org_admin = [{ 'id': 5, 'name': 'Org Admin Role for satellite-1'}]
        kt_roles_for_full_admin = [{ 'id': 5, 'name': 'Org Admin Role for satellite-1'},
                                   { 'id': 6, 'name': 'Administrator'}]

        def return_role(*args, **kwargs):
            # user id 2 in the katello test data set is foo
            if kwargs['user_id'] == 2:
                return []
            # user id 3 in the katello test data set is bazbaz
            if kwargs['user_id'] == 3:
                return kt_roles_for_full_admin
            return kt_roles_for_org_admin

        self.cp_client = Mock()
        self.cp_client.createOwner = Mock()
        self.cp_client.deleteOwner = Mock()
        # careful! this always returns the same mock username
        self.cp_client.createUser = Mock(return_value={'username': 'mockuser', 'id':'999'})
        self.cp_client.deleteConsumer = Mock()
        self.cp_client.getOwners = Mock(return_value=cp_orgs)
        self.cp_client.getUsers = Mock(return_value=kt_userlist)
        self.cp_client.createOrgAdminRolePermission = Mock()
        self.cp_client.getRoles = Mock(side_effect=return_role)
        self.cp_client.getRoles = Mock(side_effect=return_role)
        self.cp_client.createDistributor = Mock(return_value={'uuid':'100100'})
        self.cp_client.getRedhatProvider = Mock(return_value={'id':'99999'})
        self.cp_client.exportManifest = Mock(return_value="FILECONTENT")
        self.kps = KatelloPushSync(katello_client = self.cp_client)

    def test_owner_add(self):
        sw_orgs = {'1': 'foo', '2': 'bar', '3': 'baz'}
        self.kps.update_owners(sw_orgs)
        self.cp_client.createOwner.assert_called_once_with(name='baz', label='satellite-3')
        self.cp_client.createDistributor.assert_called_once_with(name="Distributor for baz", root_org='satellite-1')
        self.cp_client.exportManifest.assert_called_once_with(dist_uuid='100100')
        # TODO: actually check the file contents
        true_matcher = TestObjectSync.Matcher(self.true_compare, "x")
        self.cp_client.importManifest.assert_called_once_with(prov_id='99999', file=true_matcher)
        # TODO: this says label but it's really "name"
        self.cp_client.createOrgAdminRolePermission.assert_called_once_with(kt_org_label='baz')

    def test_owner_delete(self):
        # owner #2 is missing and should get zapped 
        sw_orgs = {'1': 'foo', '3': 'baz'}
        self.kps.update_owners(sw_orgs)
        self.cp_client.deleteOwner.assert_called_once_with(name='bar org')

    def test_owner_noop(self):
        sw_orgs = {'1': 'foo', '2': 'bar'}
        self.kps.update_owners(sw_orgs)
        assert not self.cp_client.deleteOwner.called
        assert not self.cp_client.createOwner.called

    def test_system_remove(self):
        sw_system_list = [
                            { 'server_id': '100',
                              'name': '100' },
                            { 'server_id': '101',
                              'name': '101' },
                         ]

        kt_consumer_list = [
                            { 'name': '100', 'uuid': '1-1-1', 'owner': {'key': 'satellite-2'}, 'facts': {'systemid': '100'}},
                            { 'name': '101', 'uuid': '1-1-2', 'owner': {'key': 'satellite-1'}, 'facts': {'systemid': '101'}},
                            { 'name': '102', 'uuid': '1-1-3', 'owner': {'key': 'satellite-2'}, 'facts': {'systemid': '102'}},
                            { 'name': '102', 'uuid': '1-1-4', 'owner': {'key': 'NOT-A-SAT-ORG'}, 'facts': {'systemid': '103'}},
                            { 'name': '107', 'uuid': '1-1-5', 'owner': {'key': 'satellite-1'}, 'facts': {'systemid': '107'}}
                         ]
        self.kps.delete_stale_consumers(kt_consumer_list, sw_system_list)
        expected = [call('1-1-3'), call('1-1-5')]
        result = self.cp_client.deleteConsumer.call_args_list
        assert result == expected, "%s does not match expected call set %s" % (result, expected)

    def test_user_add(self):
        sw_userlist = [{'username': 'foo', 'user_id': '1',
                        'organization_id': '1', 'role': 'Organization Administrator;Satellite Administrator',
                        'organization': 'Awesome Org', 'email': 'foo@bar.com'},
                        {'username': 'barbar', 'user_id': '2',
                        'organization_id': '2', 'role': 'Organization Administrator', 'organization': 'foo org',
                        'email': 'bar@foo.com'}]

        self.kps.update_users(sw_userlist)
        expected = [call(username='barbar', email='bar@foo.com')]
        result = self.cp_client.createUser.call_args_list
        assert result == expected, "%s does not match expected call set %s" % (result, expected)

    def test_role_update(self):
        sw_userlist = [{'username': 'foo', 'user_id': '1', 'organization_id': '1',
                        'role': 'Organization Administrator;Satellite Administrator',
                        'organization': 'Awesome Org', 'email': 'foo@bar.com'},
                        {'username': 'barbar', 'user_id': '2', 'organization_id': '2',
                        'role': 'Organization Administrator', 'organization': 'foo org',
                        'email': 'bar@foo.com'},
                        {'username': 'bazbaz', 'user_id': '3', 'organization_id': '1',
                        'role': '', 'organization': 'foo org', 'email': 'baz@foo.com'}]
        self.kps.update_roles(sw_userlist)

        # user "foo" is an org admin on sat org 1, and needs to get added to
        # satellite-1 in katello
        user_matcher = TestObjectSync.Matcher(self.user_compare, {'username': 'foo'})
        # TODO: this is an org name, not an org label
        expected = [call(kt_user=user_matcher, kt_org_label='Awesome Org')]
        result = self.cp_client.grantOrgAdmin.call_args_list
        assert result == expected, "%s does not match expected call set %s" % (result, expected)

        # ensure user "foo" became a full admin
        self.cp_client.grantFullAdmin.assert_called_once_with(kt_user=user_matcher)

        # user "bazbaz" is not an org admin on sat org 1, and needs to get removed from
        # satellite-1 in katello
        user_matcher = TestObjectSync.Matcher(self.user_compare, {'username': 'bazbaz'})
        # TODO: this is an org name, not an org label
        expected = [call(kt_user=user_matcher, kt_org_label='foo org')]
        result = self.cp_client.ungrantOrgAdmin.call_args_list
        assert result == expected, "%s does not match expected call set %s" % (result, expected)

        # ensure user "bazbaz" had full admin rights revoked 
        self.cp_client.ungrantFullAdmin.assert_called_once_with(kt_user=user_matcher)

#    def test_host_guests(self):
#        host_guest_list = [{'server_id': '1000010111', 'guests': '1000010112'},
#                            {'server_id': '1000010126', 'guests': '1000010127;1000010130;1000010128;1000010129'}
#                            ]
#        kt_consumer_list = [
#                            { 'id': 1},
#                            { 'id': 2},
#                            { 'id': 3}
#                         ]
#        checkin.upload_host_guest_mapping(host_guest_list, kt_consumer_list, self.cp_client)
#        
