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
import logging
import os

from certutils import certutils
from dateutil.tz import tzutc

from splice.common.connect import BaseConnection
import splice.common.utils

from spacewalk_splice_tool import utils, constants

_LOG = logging.getLogger(__name__)
CONFIG = None

SAT_OWNER_PREFIX = 'satellite-'

CERT_DIR_PATH = "/usr/share/rhsm/product/RHEL-6/"
CERT_DIR = None


class SplicePushSync:
    """
    class to push data into splice server (aka rcs)
    """

    def __init__(self):
        # TODO: stop loading this over and over
        global CONFIG
        CONFIG = utils.cfg_init(config_file=constants.SPLICE_CHECKIN_CONFIG)

    def get_splice_server_uuid(self):
        """
        obtains the UUID that sst is emulating
        """
        cfg = self._get_checkin_config()
        cutils = certutils.CertUtils()
        return cutils.get_subject_pieces(open(cfg["cert"]).read(), ['CN'])['CN']

    def _build_server_metadata(self, cfg, splice_server_uuid):
        """
        Build splice server metadata obj
        """
        _LOG.info("building server metadata")
        server_metadata = {}
        server_metadata['description'] = cfg["splice_server_description"]
        server_metadata['environment'] = cfg["splice_server_environment"]
        server_metadata['hostname'] = cfg["splice_server_hostname"]
        server_metadata['uuid'] = splice_server_uuid
        server_metadata['created'] = datetime.now(tzutc()).isoformat()
        server_metadata['updated'] = server_metadata['created']
        # wrap obj for consumption by upstream rcs
        return {"objects": [server_metadata]}

    def write_sample_json(self, sample_json, mpu_data, splice_server_data):
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
                    f.write(splice.common.utils.obj_to_json(data, indent=4))
                finally:
                    f.close()
            except Exception:
                _LOG.exception("Unable to write sample json for: %s" % (target_path))
        write_file("sst_mpu.json", mpu_data)
        write_file("sst_splice_server.json", splice_server_data)

    def _get_checkin_config(self):
        return {
            "host": CONFIG.get("splice", "hostname"),
            "port": CONFIG.getint("splice", "port"),
            "handler": CONFIG.get("splice", "handler"),
            "cert": CONFIG.get("splice", "splice_id_cert"),
            "key": CONFIG.get("splice", "splice_id_key"),
            "ca": CONFIG.get("splice", "splice_ca_cert"),
            "splice_server_environment": CONFIG.get("splice", "splice_server_environment"),
            "splice_server_hostname": CONFIG.get("splice", "splice_server_hostname"),
            "splice_server_description": CONFIG.get("splice", "splice_server_description"),
        }

    def build_rcs_data(self, data):
        """
        wraps the data in the right format for uploading
        """
        return {"objects": data}

    def upload_to_rcs(self, mpu_data, sample_json=None):
        cfg = self._get_checkin_config()
        try:
            splice_conn = BaseConnection(cfg["host"], cfg["port"], cfg["handler"],
                                         cert_file=cfg["cert"], key_file=cfg["key"],
                                         ca_cert=cfg["ca"])

            splice_server_data = self._build_server_metadata(cfg, self.get_splice_server_uuid())
            if sample_json:
                self.write_sample_json(sample_json=sample_json, mpu_data=mpu_data,
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
        except Exception, e:
            _LOG.error("Error uploading MarketingProductUsage Data; Error: %s" % e)
            utils.system_exit(os.EX_DATAERR, "Error uploading; Error: %s" % e)
