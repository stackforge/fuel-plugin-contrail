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

class contrail::vmware_integration {

  if $::use_vcenter == true {

    file {'/opt/contrail':
      ensure => directory,
      mode   => '0755',
    } ->

    exec {'retrive install packages':
      command => "/usr/bin/wget -q http://${::master_ip}/plugins/contrail-3.0/contrail-install-packages.deb -O /opt/contrail/contrail-install-packages.deb",
      creates => '/opt/contrail/contrail-install-packages.deb'
    } ->

    exec {'retrive vmware plugin packages':
      command => "/usr/bin/wget -q http://${::master_ip}/plugins/contrail-3.0/contrail-install-vcenter-plugin.deb -O /opt/contrail/contrail-install-vcenter-plugin.deb",
      creates => '/opt/contrail/contrail-install-vcenter-plugin.deb'
    } ->

    exec {'retrive vmdk':
      command => "/usr/bin/wget -q http://${::master_ip}/plugins/contrail-3.0/ContrailVM-disk1.vmdk -O /opt/contrail/ContrailVM-disk1.vmdk",
      creates => '/opt/contrail/ContrailVM-disk1.vmdk'
    }

  }

}