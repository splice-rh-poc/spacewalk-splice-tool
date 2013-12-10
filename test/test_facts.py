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

from base import SpliceToolTest

from spacewalk_splice_tool import facts


# more stuff should be tested here instead of via other classes
class FactsTest(SpliceToolTest):

    def test_cpu_translations(self):
        facts_dict = facts.cpu_facts({'architecture': 'EM64T'})
        self.assertEquals(facts_dict['lscpu.architecture'], 'x86_64')

        facts_dict = facts.cpu_facts({'architecture': 'athlon'})
        self.assertEquals(facts_dict['lscpu.architecture'], 'i386')

        facts_dict = facts.cpu_facts({'architecture': 'ppc64pseries'})
        self.assertEquals(facts_dict['lscpu.architecture'], 'ppc64')

        facts_dict = facts.cpu_facts({'architecture': 'ppc64iseries'})
        self.assertEquals(facts_dict['lscpu.architecture'], 'ppc64')

