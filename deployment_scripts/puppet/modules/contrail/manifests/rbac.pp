#    Copyright 2016 AT&T Corp
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
class contrail::rbac {

  $rbac_wrapper_path = '/var/lib/fuel/rbac_wrapper'
  $public_vip        = $contrail::mos_public_vip
  $api_port          = $contrail::api_server_port
  $rbacutil_path     = '/opt/contrail/utils'
  $confirmation      = '/bin/echo y'
  $domain            = 'default-domain'
  $access_list       = 'default-api-access-list'
  $rbac_access       = hiera_hash('rbac_access', {})
  $user_name         = pick($rbac_access['user'], 'admin')
  $user_password     = pick($rbac_access['password'], 'admin')
  $tenant_name       = pick($rbac_access['tenant'], 'admin')
  $rbac_rules        = hiera_hash('rbac_rules', {})

  file { "${rbac_wrapper_path}/rbac_settings.yaml":
    ensure  => present,
    content => template('contrail/rbac_settings_dump.yaml.erb'),
    backup  => '.puppet-bak',
  }

  exec { 'create default api access list':
    command => "${confirmation} | sudo python ${rbacutil_path}/rbacutil.py --name '${domain}:${access_list}' --op create --os-username ${user_name} --os-password ${user_password} --os-tenant-name ${tenant_name} --server ${public_vip}:${api_port}",
    unless  => "sudo python ${rbacutil_path}/rbacutil.py --name '${domain}:${access_list}' --op read --os-username ${user_name} --os-password ${user_password} --os-tenant-name '${tenant_name}' --server ${public_vip}:${api_port}",
    path    => '/bin:/usr/bin:/usr/local/bin',
    require => File["${rbac_wrapper_path}/rbac_settings.yaml"],
  }

  exec { 'execute rbac custom python script':
    command     => "sudo python ${rbac_wrapper_path}/rbac_wrapper.py ${public_vip}",
    path        => '/bin:/usr/bin:/usr/local/bin',
    timeout     => 900,
    require     => Exec['create default api access list'],
    subscribe   => File["${rbac_wrapper_path}/rbac_settings.yaml"],
    refreshonly => true,
  }

}
