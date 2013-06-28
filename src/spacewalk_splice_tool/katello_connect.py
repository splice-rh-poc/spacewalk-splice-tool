#!/usr/bin/python
import logging
import itertools
from datetime import datetime

from katello.client.api.organization import OrganizationAPI
from katello.client.api.environment import EnvironmentAPI
from katello.client.api.system import SystemAPI
from katello.client.api.permission import PermissionAPI
from katello.client.api.provider import ProviderAPI
from katello.client.api.user import UserAPI
from katello.client.api.distributor import DistributorAPI
from katello.client.api.user_role import UserRoleAPI
from katello.client.api.custom_info import CustomInfoAPI
from katello.client import server
from katello.client.server import BasicAuthentication
import logging
from spacewalk_splice_tool import utils, constants

_LOG = logging.getLogger(__name__)
CONFIG = utils.cfg_init(config_file=constants.SPLICE_CHECKIN_CONFIG)


class NotFoundException():
    pass


class KatelloConnection():

    def __init__(self):
        self.orgapi = OrganizationAPI()
        self.systemapi = SystemAPI()
        self.userapi = UserAPI()
        self.envapi = EnvironmentAPI()
        self.rolesapi = UserRoleAPI()
        self.permissionapi = PermissionAPI()
        self.distributorapi = DistributorAPI()
        self.provapi = ProviderAPI()
        self.infoapi = CustomInfoAPI()
        s = server.KatelloServer(CONFIG.get("katello", "hostname"),
                                 CONFIG.get("katello", "port"),
                                 CONFIG.get("katello", "proto"),
                                 CONFIG.get("katello", "api_url"))
        s.set_auth_method(BasicAuthentication(CONFIG.get("katello", "admin_user"), CONFIG.get("katello", "admin_pass")))
        server.set_active_server(s)

    def get_owners(self):
        return self.orgapi.organizations()

    def create_distributor(self, name, root_org):
        return self.distributorapi.create(name=name, org=root_org, environment_id=None)

    def delete_distributor(self, name, root_org):
        dist_uuid = self.distributorapi.distributor_by_name(distName=name, orgName=root_org)['uuid']
        return self.distributorapi.delete(distributor_uuid=dist_uuid)

    def update_distributor(self, name, root_org, params):
        dist_uuid = self.distributorapi.distributor_by_name(
            distName=name, orgName=root_org)['uuid']
        return self.distributorapi.update(dist_uuid, params)

    def export_manifest(self, dist_uuid):
        return self.distributorapi.export_manifest(distributor_uuid=dist_uuid)

    def import_manifest(self, prov_id, file):
        return self.provapi.import_manifest(provId=prov_id, manifestFile=file)

    def get_redhat_provider(self, org):
        return self.provapi.provider_by_name(orgName=org, provName="Red Hat")

    def get_entitlements(self, system_id):
        return self.systemapi.subscriptions(system_id=system_id)['entitlements']

    def get_subscription_status(self, system_uuid):
        return self.systemapi.subscription_status(system_id=system_uuid)

    def create_owner(self, label, name):
        return self.orgapi.create(name, label, "no description")

    def delete_owner(self, name):
        # todo: error handling, not sure if orgapi will handle it
        self.orgapi.delete(name)

    def update_owner(self, name, params):
        return self.orgapi.update(name, params)

    def get_users(self):
        return self.userapi.users()

    def create_user(self, username, email):
        return self.userapi.create(name=username, pw="CHANGEME", email=email, disabled=False, default_environment=None)

    def delete_user(self, user_id):
        return self.userapi.delete(user_id=user_id)

    def get_spacewalk_id(self, object_id):
        # this wants an object ID
        info_list = self.infoapi.get_custom_info(informable_type='system', informable_id=object_id)
        for info in info_list:
            if info['keyname'] == 'spacewalk-id':
                return info['value']

    def find_by_spacewalk_id(self, org, spacewalk_id):
        result = self.systemapi.find_by_custom_info(org, 'spacewalk-id', spacewalk_id)
        if len(result) > 1:
            raise Exception("more than one record found for spacewalk ID %s in org %s!" % (spacewalk_id, org))

        # we're guaranteed at this point to have zero or one records
        if result:
            return result[0]
        return

    def create_consumer(self, name, facts, installed_products, last_checkin, sw_uuid=None, owner=None):
        # there are four calls here! we need to work with katello to send all this stuff up at once
        consumer = self.systemapi.register(name=name, org='satellite-' + owner, environment_id=None,
                                           facts=facts, activation_keys=None, cp_type='system',
                                           installed_products=installed_products)

        #TODO: get rid of this extra call!
        facts = consumer['facts']
        if 'virt.is_guest' in facts:
            facts['virt.uuid'] = consumer['uuid']
            self.updateConsumer(name=consumer['name'], cp_uuid=consumer['uuid'], facts=facts)

        self.systemapi.checkin(consumer['uuid'], self._convert_date(last_checkin))
        self.systemapi.refresh_subscriptions(consumer['uuid'])

        self.infoapi.add_custom_info(informable_type='system', informable_id=consumer['id'],
                                     keyname='spacewalk-id', value=sw_uuid)

        return consumer['uuid']

    # katello demands a name here
    def update_consumer(self, cp_uuid, name, facts=None, installed_products=None,
                       last_checkin=None, owner=None, guest_uuids=None,
                       release=None, service_level=None):
        params = {}
        params['name'] = name
        if installed_products is not None:
            params['installedProducts'] = installed_products
        if guest_uuids is not None:
            params['guestIds'] = guest_uuids
        if facts is not None:
            # this logic should be moved elsewhere
            if 'virt.is_guest' in facts:
                facts['virt.uuid'] = cp_uuid
            params['facts'] = facts
        if release is not None:
            params['releaseVer'] = release
        if service_level is not None:
            params['serviceLevel'] = service_level

        # three rest calls, just one would be better
        self.systemapi.update(cp_uuid, params)
        if last_checkin is not None:
            self.systemapi.checkin(cp_uuid, self._convert_date(last_checkin))
        self.systemapi.refresh_subscriptions(cp_uuid)

    def get_consumers(self, owner=None, with_details=True):
        # TODO: this has a lot of logic and could be refactored

        # the API wants "orgId" but they mean "label"
        org_ids = map(lambda x: x['label'], self.orgapi.organizations())
        consumer_list = []
        for org_id in org_ids:
            consumer_list.append(self.systemapi.systems_by_org(orgId=org_id))

        # flatten the list
        consumer_list = list(itertools.chain.from_iterable(consumer_list))
        # return what we have, if we don't need the detailed list
        if not with_details:
            return consumer_list

        full_consumers_list = []
        # unfortunately, we need to call again to get the "full" consumer with facts
        for consumer in consumer_list:
            full_consumer = self._get_consumer(consumer['uuid'])
            full_consumer['entitlement_status'] = self.get_subscription_status(consumer['uuid'])
            full_consumers_list.append(full_consumer)

        return full_consumers_list

    def _get_consumer(self, consumer_uuid):
        return self.systemapi.system(system_id=consumer_uuid)

    def delete_consumer(self, consumer_uuid):
        self.systemapi.unregister(consumer_uuid)
        # XXX: only for dev use
        self.systemapi.remove_consumer_deletion_record(consumer_uuid)

    def get_roles(self, user_id=None):
        if user_id:
            return self.userapi.roles(user_id=user_id)
        else:
            return self.rolesapi.roles()

    def update_role(self, name, new_name):
        role = self.rolesapi.role_by_name(name=name)
        return self.rolesapi.update(role['id'], new_name, role['description'])

    # TODO: this is using kt_org_label but is really kt_org_name
    def create_org_admin_role_permission(self, kt_org_label):
        role = self.rolesapi.create(name="Org Admin Role for %s" % kt_org_label, description="generated from spacewalk")
        self.permissionapi.create(roleId=role['id'], name="Org Admin Permission for %s" % kt_org_label,
                                  description="generated from spacewalk", type_in="organizations", verbs=None,
                                  tagIds=None, orgId=kt_org_label, all_tags=True, all_verbs=True)

    def grant_org_admin(self, kt_user, kt_org_label):
        oa_role = self.rolesapi.role_by_name(name="Org Admin Role for %s" % kt_org_label)
        if not oa_role:
            _LOG.error("could not obtain org admin role from katello for org %s!" % kt_org_label)
        self.userapi.assign_role(user_id=kt_user['id'], role_id=oa_role['id'])

    def ungrant_org_admin(self, kt_user, kt_org_label):
        oa_role = self.rolesapi.role_by_name(name="Org Admin Role for %s" % kt_org_label)
        self.userapi.unassign_role(user_id=kt_user['id'], role_id=oa_role['id'])

    def grant_full_admin(self, kt_user):
        admin_role = self.rolesapi.role_by_name(name="Administrator")
        self.userapi.assign_role(user_id=kt_user['id'], role_id=admin_role['id'])

    def ungrant_full_admin(self, kt_user, kt_org_label):
        admin_role = self.rolesapi.role_by_name(name="Administrator")
        self.userapi.unassign_role(user_id=kt_user['id'], role_id=admin_role['id'])

    def _convert_date(self, dt):
        retval = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        return retval
