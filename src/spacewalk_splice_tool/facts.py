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


def translate_sw_facts_to_subsmgr(system_details):
    """
    translate spacewalk facts to subscription manager format
    @param system_details: system deatils returned from spacewalk server for a systemid
    @type system_details: {}
    @return facts dict representing subscription mamager facts data
    """
    facts = dict()
    facts['systemid'] = system_details['server_id']
    # leave this blank in the katello UI
    facts['distribution.name'] = ""
    facts.update(cpu_facts(system_details))
    facts.update(network_facts(system_details))
    facts.update(memory_facts(system_details))
    facts.update(guest_facts(system_details))
    return facts


def cpu_facts(cpuinfo):
    """
    Translate the cpu facts from spacewalk server to subscription mgr format
    """
    # we set this to 1 by default so candlepin does not remove the field from
    # the facts list. This is needed so the fact can bubble through to RCS.
    cpu_socket_count = 1
    if "sockets" in cpuinfo and len(cpuinfo['sockets']) > 0:
        cpu_socket_count = cpuinfo['sockets']

    cpu_count = 1
    if "hardware" in cpuinfo and len(cpuinfo['hardware']) > 0:
        cpu_count = cpuinfo['hardware'].split(';')[0].split()[0]

    # convert "EM64T" to "x86_64" (sometimes reported by rhel4 up2date)
    cpu_arch = cpuinfo['architecture']
    if cpu_arch == 'EM64T':
        cpu_arch = 'x86_64'

    cpu_facts_dict = dict()

    # rules.js depends on uname.machine, not lscpu
    cpu_facts_dict['uname.machine'] = cpu_arch
    cpu_facts_dict['lscpu.l1d_cache'] = ""
    cpu_facts_dict['lscpu.architecture'] = cpu_arch
    cpu_facts_dict['lscpu.stepping'] = ""
    cpu_facts_dict['lscpu.cpu_mhz'] = ""
    cpu_facts_dict['lscpu.vendor_id'] = ""
    cpu_facts_dict['lscpu.cpu(s)'] = cpu_count
    cpu_facts_dict['cpu.cpu(s)'] = cpu_count
    cpu_facts_dict['lscpu.model'] = ""
    cpu_facts_dict['lscpu.on-line_cpu(s)_list'] = ""
    cpu_facts_dict['lscpu.byte_order'] = ""
    cpu_facts_dict['lscpu.cpu_socket(s)'] = cpu_socket_count
    cpu_facts_dict['lscpu.core(s)_per_socket'] = \
        int(cpu_count) / int(cpu_socket_count)
    cpu_facts_dict['lscpu.hypervisor_vendor'] = ""
    #cpu_facts_dict['lscpu.numa_node0_cpu(s)'] = ""
    cpu_facts_dict['lscpu.bogomips'] = ""
    #cpu_facts_dict['cpu.core(s)_per_socket'] = ""
    cpu_facts_dict['cpu.cpu_socket(s)'] = cpu_socket_count
    cpu_facts_dict['lscpu.virtualization_type'] = ""
    cpu_facts_dict['lscpu.cpu_family'] = ""
    #cpu_facts_dict['lscpu.numa_node(s)'] = ""
    cpu_facts_dict['lscpu.l1i_cache'] = ""
    cpu_facts_dict['lscpu.l2_cache'] = ""
    cpu_facts_dict['lscpu.l3_cache'] = ""
    #cpu_facts_dict['lscpu.thread(s)_per_core'] = ""
    cpu_facts_dict['lscpu.cpu_op-mode(s)'] = ""
    return cpu_facts_dict


def memory_facts(meminfo):
    """
    Translate memory info
    """
    mem_facts_dict = dict()
    if 'memory' in meminfo and len(meminfo['memory']) > 0:
        mem_facts_dict['memory.memtotal'] = int(meminfo['memory']) * 1024
    return mem_facts_dict


def network_facts(nwkinfo):
    """
    Translate network interface facts
    """
    nwk_facts_dict = dict()

    network_info = nwkinfo['hardware'].split(';')[1:]
    for n in network_info:
        (iface, addrmask, hwaddr) = n.split()
        nwk_facts_dict['net.interface.' + iface + '.mac_address'] = hwaddr
        nwk_facts_dict['net.interface.' + iface + '.ipv4_address'] = addrmask.split('/')[0]
        nwk_facts_dict['net.interface.' + iface + '.netmask'] = addrmask.split('/')[1]

    nwk_facts_dict['net.ipv4_address'] = nwkinfo['ip_address']
    nwk_facts_dict['network.hostname'] = nwkinfo['hostname']

    return nwk_facts_dict


def guest_facts(guestinfo):
    guest_facts_dict = dict()
    if 'is_virtualized' in guestinfo and guestinfo['is_virtualized'] == 'Yes':
        guest_facts_dict['virt.is_guest'] = True
        guest_facts_dict['virt.host_type'] = 'Unknown'
    return guest_facts_dict


def inactive_facts(details):
    inactive_facts_dict = dict()
    if "inactive" in details:
        if "last_boot" in details["inactive"]:
            inactive_facts_dict["inactive_dot_last_boot"] = str(details["inactive"]["last_boot"])
        if "last_checkin" in details["inactive"]:
            inactive_facts_dict["inactive_dot_last_checkin"] = str(details["inactive"]["last_checkin"])
    return inactive_facts_dict
