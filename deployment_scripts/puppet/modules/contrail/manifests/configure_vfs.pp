#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
define contrail::configure_vfs (
  $numvfs,
  $totalvfs,
  $phys_dev = $title,
  ) {

  Exec {
    provider => 'shell',
    path => '/usr/bin:/bin:/sbin:/usr/sbin',
  }

  $vf_data           = get_vf_data($phys_dev, $contrail::dpdk_vf_number)
  $vf_dev_name       = "dpdk-vf-${phys_dev}"
  $vf_number         = $contrail::dpdk_vf_number
  $vf_origin_name    = $vf_data['vf_dev_name']
  $vf_dev_pci        = $vf_data['vf_pci_addr']
  $vf_dev_mac        = $vf_data['vf_mac_addr']

  exec { "rename-${vf_dev_name}":
    command => "ip link set ${vf_origin_name} name ${vf_dev_name}",
    unless  => "ip link | grep ${vf_dev_name}",
  }

  $udev_rule = join(['SUBSYSTEM=="net"',
                    'ACTION=="add"',
                    "KERNELS==\"${vf_dev_pci}\"",
                    "NAME=\"${vf_dev_name}\"",
                    "RUN+=\"/bin/ip link set dev %k address ${vf_dev_mac}\"",
                    ],', ')

  $interface_config = join(["auto ${vf_dev_name}",
                            "iface ${vf_dev_name} inet manual",
                            "pre-up ip link set link dev ${phys_dev} vf ${vf_number} vlan 0",
                            "post-up ip link set link dev ${phys_dev} vf ${vf_number} spoof off",
                            ],"\n")

  file_line {"udev_rule_for_${vf_dev_name}":
    line    => $udev_rule,
    path    => '/etc/udev/rules.d/72-contrail-dpdk-on-vf.rules',
    require => File['/etc/udev/rules.d/72-contrail-dpdk-on-vf.rules'],
  } ->
  file {"/etc/network/interfaces.d/ifcfg-${vf_dev_name}":
    ensure  => file,
    content => $interface_config,
  }

  exec { "ifup_${vf_dev_name}":
    command => "ifup ${vf_dev_name}",
    unless  => "ip link show dev ${vf_dev_name} | grep ,UP",
    require => [File["/etc/network/interfaces.d/ifcfg-${vf_dev_name}"],
                Exec["rename-${vf_dev_name}"],
                ]
  }

}
