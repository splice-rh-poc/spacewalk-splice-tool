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

from datetime import datetime
import io
import json
import logging
from optparse import OptionParser
import os
import re
import socket
import sys
import tempfile
import time

from certutils import certutils
from dateutil.tz import tzutc
from splice.common.connect import BaseConnection
import splice.common.utils

from spacewalk_splice_tool import facts, connect, utils, constants, transforms, katello_sync
from spacewalk_splice_tool.sw_client import SpacewalkClient
from spacewalk_splice_tool.katello_connect import KatelloConnection, NotFoundException

_LIBPATH = "/usr/share/rhsm"
# add to the path if need be
if _LIBPATH not in sys.path:
    sys.path.append(_LIBPATH)

from subscription_manager.certdirectory import CertificateDirectory

_LOG = logging.getLogger(__name__)
CONFIG = None

SAT_OWNER_PREFIX = 'satellite-'

CERT_DIR_PATH = "/usr/share/rhsm/product/RHEL-6/"
CERT_DIR = None

def get_product_ids(subscribedchannels):
    """
    For the subscribed base and child channels look up product ids
    """
    if CERT_DIR is None:
        global CERT_DIR
        CERT_DIR = CertificateDirectory(CERT_DIR_PATH)

    mapping_file = os.path.join(
        os.path.join(constants.CHANNEL_PRODUCT_ID_MAPPING_DIR,
                     utils.get_release()),
        constants.CHANNEL_PRODUCT_ID_MAPPING_FILE)
    channel_mappings = utils.read_mapping_file(mapping_file)

    product_ids = []
    for channel in subscribedchannels.split(';'):
        origin_channel = channel
        if origin_channel in channel_mappings:
            cert = channel_mappings[origin_channel]
            product_ids.append(cert.split('-')[-1].split('.')[0])

    _LOG.debug("mapped subscribed channels %s to installed products %s" % (subscribedchannels, product_ids))
    # reformat to how candlepin expects the product id list
    installed_products = []
    for p in product_ids:
        product_cert = CERT_DIR.findByProduct(str(p))
        installed_products.append({"productId": product_cert.products[0].id, "productName": product_cert.products[0].name})
    return installed_products


def get_splice_serv_id():
    """
    return the splice server UUID to be used
    """
    cutils = certutils.CertUtils()
    return cutils.get_subject_pieces(open(CONFIG.get("splice", "splice_id_cert")).read(), ['CN'])['CN']

def _get_splice_server_uuid():
    """
    obtains the UUID that sst is emulating
    """
    cfg = get_checkin_config()
    cutils = certutils.CertUtils()
    return cutils.get_subject_pieces(open(cfg["cert"]).read(), ['CN'])['CN']


def build_server_metadata(cfg):
    """
    Build splice server metadata obj
    """
    _LOG.info("building server metadata")
    server_metadata = {}
    server_metadata['description'] = cfg["splice_server_description"]
    server_metadata['environment'] = cfg["splice_server_environment"]
    server_metadata['hostname'] = cfg["splice_server_hostname"]
    server_metadata['uuid'] = _get_splice_server_uuid()
    server_metadata['created'] = datetime.now(tzutc()).isoformat()
    server_metadata['updated'] = server_metadata['created']
    # wrap obj for consumption by upstream rcs
    return {"objects": [server_metadata]}

def get_katello_consumers():
    katello_conn = KatelloConnection()
    return katello_conn.getConsumers()

def get_katello_entitlements(uuid):
    katello_conn = KatelloConnection()
    return katello_conn.getEntitlements(uuid)

def write_sample_json(sample_json, mpu_data, splice_server_data):
    def write_file(file_name, data):
        if not data:
            return
        if not os.path.exists(sample_json):
            _LOG.info("Directory doesn't exist: %s" % (sample_json))
            return
        target_path = os.path.join(sample_json, file_name)
        try:
            _LOG.info("Will write json data to: %s" % (target_path))
            f = open(target_path, "w")
            try:
                f.write(splice.common.utils.obj_to_json(data, indent = 4))
            finally:
                f.close()
        except Exception, e:
            _LOG.exception("Unable to write sample json for: %s" % (target_path))
    write_file("sst_mpu.json", mpu_data)
    write_file("sst_splice_server.json", splice_server_data)

def upload_to_rcs(mpu_data, sample_json=None):
    cfg = get_checkin_config()
    try:
        splice_conn = BaseConnection(cfg["host"], cfg["port"], cfg["handler"],
            cert_file=cfg["cert"], key_file=cfg["key"], ca_cert=cfg["ca"])

        splice_server_data = build_server_metadata(cfg)
        if sample_json:
            write_sample_json(sample_json=sample_json, mpu_data=mpu_data,
                            splice_server_data=splice_server_data)
        # upload the server metadata to rcs
        _LOG.info("sending metadata to server")
        url = "/v1/spliceserver/"
        status, body = splice_conn.POST(url, splice_server_data)
        _LOG.debug("POST to %s: received %s %s" % (url, status, body))
        if status != 204:
            _LOG.error("Splice server metadata was not uploaded correctly")
            utils.system_exit(os.EX_DATAERR, "Error uploading splice server data")

        # upload the data to rcs
        url = "/v1/marketingproductusage/"
        status, body = splice_conn.POST(url, mpu_data)
        _LOG.debug("POST to %s: received %s %s" % (url, status, body))
        if status != 202 and status != 204:
            _LOG.error("MarketingProductUsage data was not uploaded correctly")
            utils.system_exit(os.EX_DATAERR, "Error uploading marketing product usage data")

        utils.system_exit(os.EX_OK, "Upload was successful")
    except Exception, e:
        _LOG.error("Error uploading MarketingProductUsage Data; Error: %s" % e)
        utils.system_exit(os.EX_DATAERR, "Error uploading; Error: %s" % e)


def get_checkin_config():
    return {
        "host" : CONFIG.get("splice", "hostname"),
        "port" : CONFIG.getint("splice", "port"),
        "handler" : CONFIG.get("splice", "handler"),
        "cert" : CONFIG.get("splice", "splice_id_cert"),
        "key" : CONFIG.get("splice", "splice_id_key"),
        "ca" : CONFIG.get("splice", "splice_ca_cert"),
        "splice_server_environment" : CONFIG.get("splice", "splice_server_environment"),
        "splice_server_hostname" : CONFIG.get("splice", "splice_server_hostname"),
        "splice_server_description" : CONFIG.get("splice", "splice_server_description"),
    }

def build_rcs_data(data):
    """
    wraps the data in the right format for uploading
    """
    return {"objects": data}


def get_parent_channel(channel, channels):
    for c in channels:
        if c['new_channel_label'] == channel['original_channel_label']:
            return get_parent_channel(c, channels)
    return channel
    

def channel_mapping(channels):
    channel_map = {}

    for channel in channels:
        parent_channel = get_parent_channel(channel, channels)
        channel_map[channel['new_channel_label']] = \
            parent_channel['original_channel_label']

    return channel_map


def update_system_channel(systems, channels):

    _LOG.info("calculating base channels from cloned channels")
    channel_map = channel_mapping(channels)
    for system in systems:
        system['software_channel'] = channel_map.get(
                                        system['software_channel'],
                                        system['software_channel'])


def spacewalk_sync(options):
    """
    Performs the data capture, translation and checkin to katello
    """
    _LOG.info("Started capturing system data from spacewalk")
    client = SpacewalkClient(CONFIG.get('spacewalk', 'host'),
                             CONFIG.get('spacewalk', 'ssh_key_path'))
    katello_client = KatelloConnection()
    kps = katello_sync.KatelloPushSync(katello_client=katello_client)
    dt = transforms.DataTransforms()
    consumers = []

    _LOG.info("retrieving data from spacewalk")
    sw_user_list = client.get_user_list()
    system_details = client.get_system_list()
    channel_details = client.get_channel_list()
    hosts_guests = client.get_host_guest_list()
    update_system_channel(system_details, channel_details)
    org_list = client.get_org_list()

    kps.update_owners(org_list)
    kps.update_users(sw_user_list)
    kps.update_roles(sw_user_list)

    katello_consumer_list = katello_client.getConsumers()
    kps.delete_stale_consumers(katello_consumer_list, system_details)

    _LOG.info("adding installed products to %s spacewalk records" % len(system_details))
    # enrich with engineering product IDs
    clone_mapping = []
    map(lambda details :
            details.update({'installed_products' : \
                            get_product_ids(details['software_channel'])}),
                           system_details)

    # convert the system details to katello consumers
    consumers.extend(dt.transform_to_consumers(system_details))
    _LOG.info("found %s systems to upload into katello" % len(consumers))
    _LOG.info("uploading to katello...")
    kps.upload_to_katello(consumers)
    _LOG.info("upload completed. updating with guest info..")
    # refresh the consumer list. we need the full details here to get at the system ID
    katello_consumer_list = katello_client.getConsumers(with_details=False)
    kps.upload_host_guest_mapping(hosts_guests, katello_consumer_list)
    _LOG.info("guest upload completed")


def splice_sync(options):
    """
    Syncs data from katello to splice
    """
    _LOG.info("Started syncing system data to splice")
    # now pull put out of katello, and into rcs!
    katello_consumers = get_katello_consumers()
    katello_client = KatelloConnection()
    dt = transforms.DataTransforms()
    _LOG.info("calculating marketing product usage")

    # create the base marketing usage list
    rcs_mkt_usage = map(dt.transform_to_rcs, katello_consumers)
    # strip out blank values that we don't want to send to splice
    rcs_mkt_usage = filter(None, rcs_mkt_usage)

    # enrich with product usage info
    map(lambda rmu : 
            rmu.update(
                {'product_info': dt.transform_entitlements_to_rcs(
                                    get_katello_entitlements(
                                        rmu['instance_identifier']))}), 
                                        rcs_mkt_usage)
    _LOG.info("uploading to splice...")
    upload_to_rcs(mpu_data=build_rcs_data(rcs_mkt_usage), sample_json=options.sample_json)
    _LOG.info("upload completed")


def main(options):

    global CONFIG
    CONFIG = utils.cfg_init(config_file=constants.SPLICE_CHECKIN_CONFIG)

    start_time = time.time()
    _LOG.info("run starting")

    socket.setdefaulttimeout(CONFIG.getfloat('main', 'socket_timeout'))

    if options.spacewalk_sync:
        spacewalk_sync(options)

    if options.splice_sync:
        splice_sync(options)

    finish_time = time.time() - start_time
    _LOG.info("run complete") 
