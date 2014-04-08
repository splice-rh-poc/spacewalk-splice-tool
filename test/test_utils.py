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
from spacewalk_splice_tool import utils

# from subscription-manager
class MockStderr:
    def __init__(self):
        self.buffer = ""

    def write(self, buf):
        self.buffer = self.buffer + buf

    @staticmethod
    def isatty(buf=None):
        return False


class UtilsTest(SpliceToolTest):

    def test_system_exit(self):
        self.assertRaises(SystemExit, utils.system_exit, 500)

    def test_system_exit_message(self):
        self.mock_stderr = MockStderr()
        sys.stderr = self.mock_stderr
        self.assertRaises(SystemExit, utils.system_exit, 500, message='foobarbaz')
        exit_output = self.mock_stderr.buffer
        self.assertTrue(exit_output.find("foobarbaz") == 0, "message was not printed on exit")
        sys.stderr = sys.__stderr__


    def test_get_release(self):
        self.unmock(utils, 'get_release')
        utils.open = Mock()
        utils.open.return_value.readlines.return_value = \
            'Red Hat Enterprise Linux Server release 6.4 (Santiago)'
        release = utils.get_release()
        self.assertEquals('RHEL-6', release)

    def test_config(self):
        # unmock cfg_init, which is mocked in base.py
        self.unmock(utils, 'cfg_init')
        cfg = utils.cfg_init(config_file="../etc/splice/checkin.test.conf")
        self.assertEquals(443, cfg.getint("splice", "port"))

    def test_config_reinit(self):
        # unmock cfg_init, which is mocked in base.py
        self.unmock(utils, 'cfg_init')
        cfg = utils.cfg_init(config_file="../etc/splice/checkin.test.conf")
        self.assertEquals(443, cfg.getint("splice", "port"))

    def test_autoentitle_config(self):
        cfg = utils.cfg_init()
        self.assertEquals(True, utils.get_autoentitle(cfg))
        self.unmock(utils, 'cfg_init')
        cfg = utils.cfg_init(config_file="../etc/splice/checkin.test.conf")
        cfg.set('katello', 'autoentitle_systems', 'False')
        self.assertEquals(False, utils.get_autoentitle(cfg))

    def test_flatten_orgs(self):
        cfg = utils.cfg_init()
        self.assertEquals(False, utils.get_flatten_orgs(cfg))
        self.unmock(utils, 'cfg_init')
        cfg = utils.cfg_init(config_file="../etc/splice/checkin.test.conf")
        cfg.set('katello', 'flatten_orgs', 'True')
        self.assertEquals(True, utils.get_autoentitle(cfg))

    def test_multisw_config(self):
        # test first with mocked config (single spacewalk)
        cfg = utils.cfg_init()
        self.assertEquals(['spacewalk'], utils.get_multi_sw_cfg(cfg))

        # unmock cfg_init, which is mocked in base.py
        self.unmock(utils, 'cfg_init')
        cfg = utils.cfg_init(config_file="../etc/splice/checkin.test.conf")
        self.assertTrue('spacewalk_foo' in utils.get_multi_sw_cfg(cfg))
        self.assertTrue('spacewalk_bar' in utils.get_multi_sw_cfg(cfg))
        self.assertTrue('spacewalk_baz' in utils.get_multi_sw_cfg(cfg))
