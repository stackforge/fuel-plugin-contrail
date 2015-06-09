#    Copyright 2015 Mirantis, Inc.
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

include contrail
case $operatingsystem
{
    CentOS:
      {
        yumrepo {'mos': priority => 1, exclude => 'python-thrift,nodejs'} # Contrail requires newer python-thrift and nodejs from it's repo
        package {'yum-plugin-priorities': ensure => present }
      }
    Ubuntu:
      {
        if ($contrail::node_role =~ /^base-os$/) or ($contrail::node_role =~ /^compute$/) {
          file { '/etc/apt/preferences.d/contrail-pin-100':
            ensure  => file,
            content => template('contrail/contrail-pin-100.erb'),
          }
        }
        if $contrail::node_name =~ /^contrail.\d+$/ {
          file { '/etc/apt/sources.list.d/mos.list':
            ensure => absent,
          }
        }
      }
}
