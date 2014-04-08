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

import logging
import os
import tempfile
from spacewalk_splice_tool import utils
from spacewalk_splice_tool import transforms

_LOG = logging.getLogger(__name__)

SAT_OWNER_PREFIX = 'satellite-'


class KatelloPushSync:
    """
    a class for writing data to katello
    """

    def __init__(self, katello_client, num_threads):
        self.katello_client = katello_client
        self.num_threads = num_threads

    def _mpu_enrich_worker(self, mpu):
        """
        worker for queue (see enrich_mpu below)
        """
        dt = transforms.DataTransforms()
        # TODO: this is difficult to understand
        mpu.update({'product_info':
                    dt.transform_entitlements_to_rcs(self.katello_client.get_entitlements(mpu['instance_identifier']))})
        return mpu

    def enrich_mpu(self, marketing_product_usage):
        enriched_mpu = utils.queued_work(self._mpu_enrich_worker, marketing_product_usage, self.num_threads)
        return enriched_mpu

    def update_owners(self, orgs, prefix):
        """
        ensure that the katello owner set matches what's in spacewalk
        """

        owners = self.katello_client.get_owners()
        # we need to iterate over a sorted list, to ensure org #1
        # is created before others
        org_ids = sorted(orgs.keys())
        owner_label_map = {}
        for owner in owners:
            owner_label_map[owner['label']] = owner
        owner_labels = owner_label_map.keys()
        _LOG.debug("owner label list from katello: %s" % owner_labels)

        # TODO: string needs a dash for readability
        root_org = "satellite-%s1" % prefix

        for org_id in org_ids:
            katello_label = SAT_OWNER_PREFIX + org_id
            if katello_label not in owner_labels:
                _LOG.info("creating owner %s (%s), owner is in spacewalk but not katello" %
                          (katello_label, orgs[org_id]))
                self.katello_client.create_owner(label=katello_label, name=orgs[org_id])
                self.katello_client.create_org_admin_role_permission(kt_org_label=orgs[org_id])
                # if we are not the first org, create a
                # distributor for us in the first org
                if org_id is not "1":
                    _LOG.info("creating distributor for %s (org id: %s)" %
                              (orgs[org_id], org_id))
                    distributor = self.katello_client.create_distributor(
                        name="Distributor for %s" % orgs[org_id],
                        root_org=root_org)
                    manifest_data = self.katello_client.export_manifest(
                        dist_uuid=distributor['uuid'])
                    # katello-cli does some magic that
                    # requires an actual file here
                    manifest_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
                    manifest_filename = manifest_file.name
                    _LOG.info("manifest temp file is %s" % manifest_filename)
                    manifest_file.write(manifest_data)
                    manifest_file.close()
                    manifest_file = open(manifest_filename, 'r')

                    # this uses the org name, not label
                    provider = self.katello_client.get_redhat_provider(
                        org=orgs[org_id])
                    self.katello_client.import_manifest(prov_id=provider['id'], file=manifest_file)
                    manifest_file.close()
                    os.unlink(manifest_file.name)
            # Check that the org names are also equal, as the name can be
            # modified in Satellite at any time.
            elif orgs[org_id] != owner_label_map[katello_label]['name']:
                self.katello_client.update_owner(owner_label_map[katello_label]['name'], {'name': orgs[org_id]})
                self.katello_client.update_distributor('Distributor for %s' % owner_label_map[katello_label]['name'],
                                                       root_org,
                                                       {'name': 'Distributor for %s' % orgs[org_id]})
                self.katello_client.update_role('Org Admin Role for %s' % owner_label_map[katello_label]['name'],
                                                'Org Admin Role for %s' % orgs[org_id])

        # get the owner list again
        owners = self.katello_client.get_owners()
        # build up a label->name mapping this time
        owner_labels_names = {}
        for owner in owners:
            owner_labels_names[owner['label']] = owner['name']

        # perform deletions
        for owner_label in owner_labels_names.keys():
            # bail out if this isn't an owner we are managing
            _LOG.debug("comparing %s to %s" % (owner_label, SAT_OWNER_PREFIX + prefix))
            if not owner_label.startswith(SAT_OWNER_PREFIX + prefix):
                continue

            # get the org ID from the katello name
            kt_org_id = owner_label[len(SAT_OWNER_PREFIX):]
            if kt_org_id not in org_ids:
                _LOG.info("removing owner %s (name: %s) and associated distributor, owner is no longer in spacewalk"
                          % (owner_label, owner_labels_names[owner_label]))
                self.katello_client.delete_distributor(
                    name="Distributor for %s" % owner_labels_names[owner_label], root_org=root_org)
                self.katello_client.delete_owner(name=owner_labels_names[owner_label])

    def update_users(self, sw_userlist):
        """
        ensure that the katello user set matches what's in spacewalk
        """
        sw_users = {}
        for sw_user in sw_userlist:
            sw_users[sw_user['username']] = sw_user
        kt_users = {}
        for kt_user in self.katello_client.get_users():
            kt_users[kt_user['username']] = kt_user

        for sw_username in sw_users.keys():
            if sw_username not in kt_users.keys():
                _LOG.info("adding new user %s to katello" % sw_username)
                self.katello_client.create_user(username=sw_username, email=sw_users[sw_username]['email'])

    def update_roles(self, sw_userlist):
        sw_users = {}
        for sw_user in sw_userlist:
            sw_users[sw_user['username']] = sw_user
        kt_users = {}
        for kt_user in self.katello_client.get_users():
            kt_users[kt_user['username']] = kt_user

        for kt_username in kt_users.keys():
            # if the user isn't also in SW, bail out
            # NB: we assume kt_users is always be a superset of sw_users
            if kt_username not in sw_users.keys():
                _LOG.info("skipping role sync for %s, user is not in spacewalk" % kt_username)
                continue

            # get a flat list of role names, for comparison with sw
            kt_roles = map(lambda x: x['name'], self.katello_client.get_roles(user_id=kt_users[kt_username]['id']))
            sw_roles = sw_users[kt_username]['role'].split(';')
            sw_user_org = sw_users[kt_username]['organization']

            # add any new roles
            for sw_role in sw_roles:
                _LOG.debug("examining sw role %s for org %s against kt role set %s" % (sw_role, sw_user_org, kt_roles))

                if sw_role == 'Organization Administrator' and "Org Admin Role for %s" % sw_user_org not in kt_roles:
                        _LOG.info("adding %s to %s org admin role in katello" % (kt_username, sw_user_org))
                        self.katello_client.grant_org_admin(kt_user=kt_users[kt_username], kt_org_label=sw_user_org)

                elif sw_role == 'Satellite Administrator' and 'Administrator' not in kt_roles:
                        _LOG.info("adding %s to full admin role in katello" % kt_username)
                        self.katello_client.grant_full_admin(kt_user=kt_users[kt_username])

            # delete any roles in kt but not sw
            for kt_role in kt_roles:
                # TODO: handle sat admin
                _LOG.debug("examining kt role %s against sw role set %s for org %s" % (kt_role, sw_roles, sw_user_org))

                if kt_role == "Org Admin Role for satellite-%s" % sw_users[kt_username]['organization_id'] and \
                        "Organization Administrator" not in sw_roles:
                    _LOG.info("removing %s from %s org admin role in katello" % (kt_username, sw_user_org))
                    self.katello_client.ungrant_org_admin(kt_user=kt_users[kt_username], kt_org_label=sw_user_org)

                elif kt_role == 'Administrator' and 'Satellite Administrator' not in sw_roles:
                        _LOG.info("removing %s from full admin role in katello" % kt_username)
                        self.katello_client.ungrant_full_admin(kt_user=kt_users[kt_username])

    def delete_stale_consumers(self, consumer_list, system_list):
        """
        removes consumers that are in katello and not spacewalk. This is to clean
        up any systems that were deleted in spacewalk.
        """

        system_id_list = map(lambda x: x['server_id'], system_list)

        _LOG.debug("system id list from sw: %s" % system_id_list)
        consumers_to_delete = []

        for consumer in consumer_list:
            if 'systemid' not in consumer['facts'] or consumer['facts']['systemid'] is None:
                    _LOG.debug("consumer %s has no systemid, skipping" % consumer['name'])
                    continue
            # don't delete consumers that are not in orgs we manage!
            if not consumer['owner']['key'].startswith(SAT_OWNER_PREFIX):
                _LOG.debug("consumer %s is not in a satellite-managed owner, skipping" % consumer['name'])
                continue
            if consumer['facts']['systemid'] not in system_id_list:
                _LOG.debug("adding consumer %s to deletion list" % consumer['name'])
                consumers_to_delete.append(consumer)

        _LOG.info("removing %s consumers that are no longer in spacewalk" % len(consumers_to_delete))
        for consumer in consumers_to_delete:
            _LOG.info("removed consumer %s" % consumer['name'])
            self.katello_client.delete_consumer(consumer['uuid'])

    def upload_host_guest_mapping(self, host_guests, katello_consumer_list):
        """
        updates katello consumers that have guests. This has to happen after an
        initial update, so we have UUIDs for all systems
        """
        sysid_consumer_map = {}
        for consumer in katello_consumer_list:
            sysid = self.katello_client.get_spacewalk_id(consumer['id'])
            # katello requires both uuid and name
            sysid_consumer_map[sysid] = (consumer['uuid'], consumer['name'])

        for host_guest in host_guests:
            host_consumer_id_name = sysid_consumer_map[host_guest['server_id']]

            guest_consumer_ids = []
            for sw_guest in host_guest['guests'].split(';'):
                # we only want the first piece of the tuple here
                guest_consumer_ids.append(sysid_consumer_map[sw_guest][0])

            _LOG.debug("detected guest IDs %s for host %s" % (guest_consumer_ids, host_consumer_id_name))

            self.katello_client.update_consumer(name=host_consumer_id_name[1], cp_uuid=host_consumer_id_name[0], guest_uuids=guest_consumer_ids)

    def _upload_consumer_to_katello(self, consumer):
        kt_consumer = self.katello_client.find_by_spacewalk_id("satellite-%s" % consumer['owner'], consumer['id'])
        if kt_consumer:
            # use the existing kt/cp uuid when updating
            self.katello_client.update_consumer(cp_uuid=kt_consumer['uuid'],
                                                name=consumer['name'],
                                                facts=consumer['facts'],
                                                installed_products=consumer['installed_products'],
                                                owner=consumer['owner'],
                                                last_checkin=consumer['last_checkin'])
            _LOG.debug("updated consumer %s" % kt_consumer['uuid'])
        else:
            uuid = self.katello_client.create_consumer(name=consumer['name'],
                                                       sw_uuid=consumer['id'],
                                                       facts=consumer['facts'],
                                                       installed_products=consumer['installed_products'],
                                                       last_checkin=consumer['last_checkin'],
                                                       owner=consumer['owner'])
            _LOG.debug("created consumer %s" % uuid)

    def upload_to_katello(self, consumers):
        """
        Uploads consumer data to katello
        """
        utils.queued_work(self._upload_consumer_to_katello, consumers, self.num_threads)

    def autoentitle_satellite_orgs(self):
        """
        performs an autoentitle on all orgs that map to satellite orgs
        """
        owner_list = self.katello_client.get_owners()
        for owner in owner_list:
            # only do this for satellite orgs
            if owner['label'].count(SAT_OWNER_PREFIX) == 1:
                self.katello_client.refresh_subs(org_label=owner['label'])
