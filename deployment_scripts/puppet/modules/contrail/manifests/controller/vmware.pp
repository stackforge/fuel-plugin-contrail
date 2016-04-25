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

class contrail::controller::vmware {

  if $contrail::use_vcenter {

    $pkgs = ['contrail-fabric-utils','contrail-setup']
    $pip_pkgs = ['Fabric-1.7.5']

    apt::pin {'fix_python_ecdsa':
      priority => 1400,
      label    => 'contrail',
      packages => 'python-ecdsa'
    } ->
    class { 'contrail::package':
      install     => $pkgs,
      pip_install => $pip_pkgs,
    } ->

    exec {'retrive latest install packages':
      command => '/usr/bin/apt-get download contrail-install-packages && /bin/ln -s -f contrail-install-packages*.deb latest-contrail-install-packages.deb',
      creates => '/opt/contrail/latest-contrail-install-packages.deb',
      cwd     => '/opt/contrail',
    } ->

    exec {'retrive vmdk':
      command => "/usr/bin/curl -fLO http://mirrors-aic.it.att.com/files/contrail-vcenter/ContrailVM-disk1.vmdk",
      creates => '/opt/contrail/ContrailVM-disk1.vmdk',
      cwd     => '/opt/contrail',
    } ->

    file { '/opt/contrail/utils/fabfile/testbeds/testbed.py':
      content => template('contrail/vmware_testbed.py.erb'),
      mode    => '0775',
    } ->

    file_line{'vmware_pub_authorized_keys':
      path   => '/root/.ssh/authorized_keys',
      line   => file('/var/lib/astute/vmware/vmware.pub'),
    }

    if $contrail::provision_vmware {

      file { '/opt/contrail/utils/fabfile/tasks/additional_tasks.py':
        mode    => '0644',
        source  => 'puppet:///modules/contrail/additional_tasks.py',
        before  => Exec['fab_prepare_contrailvm'],
        require => Class['contrail::package'],
      } ->

      file_line { 'add_additional_tasks':
        path    => '/opt/contrail/utils/fabfile/__init__.py',
        line    => 'from tasks.additional_tasks import *',
        before  => Exec['fab_prepare_contrailvm'],
      }

      if $contrail::env == 'dev' {

        file_line { 'change_memsize1':
          path    => '/opt/contrail/utils/fabfile/templates/compute_vmx_template.py',
          line    => 'memsize = "2048"',
          match   => '^memsize',
          require => Class['contrail::package'],
          before  => Exec['fab_prov_esxi'],
        }

        file_line { 'change_memsize2':
          path    => '/opt/contrail/utils/fabfile/templates/compute_vmx_template.py',
          line    => 'sched.mem.min = "2048"',
          match   => '^sched\.mem\.min',
          require => Class['contrail::package'],
          before  => Exec['fab_prov_esxi'],
        }

      }

      service { "ssh":
        ensure  => running,
        enable  => true,
      }

      augeas { "ssh_root_access_yes":
        context    => '/files/etc/ssh/sshd_config',
        changes    => ['set PermitRootLogin yes',
                       'set PasswordAuthentication yes'],
      } ->
      # NOTE(AK858F): This is dirty fix, ask me why
      exec {'restart_ssh' :
        command    => '/sbin/restart ssh',
      } ->

      exec { 'fab_prov_esxi':
        path      => '/usr/local/bin:/bin:/usr/bin/',
        cwd       => '/opt/contrail/utils',
        command   => 'fab prov_esxi && touch /opt/contrail/fab_prov_esxi-DONE',
        tries     => 3,
        try_sleep => 30,
        require   => File_Line['vmware_pub_authorized_keys'],
      } ->

      exec { 'fab_prepare_contrailvm':
        timeout   => 3600,
        path      => '/usr/local/bin:/bin:/usr/bin/',
        cwd       => '/opt/contrail/utils',
        command   => 'fab prepare_contrailvm:/opt/contrail/latest-contrail-install-packages.deb && touch /opt/contrail/fab_prepare_contrailvm-DONE',
        tries     => 3,
        try_sleep => 30,
        creates   => '/opt/contrail/fab_prepare_contrailvm-DONE',
      } ->

      exec { 'fab_install_vrouter':
        timeout   => 3600,
        path      => '/usr/local/bin:/bin:/usr/bin/',
        cwd       => '/opt/contrail/utils',
        command   => 'fab fab_install_vrouter && touch /opt/contrail/fab_install_vrouter-DONE',
        tries     => 3,
        try_sleep => 30,
        creates   => '/opt/contrail/fab_install_vrouter-DONE',
      } ->

      exec { 'fab_setup_vcenter':
        path      => '/usr/local/bin:/bin:/usr/bin/',
        cwd       => '/opt/contrail/utils',
        command   => 'fab setup_vcenter && touch /opt/contrail/fab_setup_vcenter-DONE',
        tries     => 3,
        try_sleep => 30,
        creates   => '/opt/contrail/fab_setup_vcenter-DONE',
      } ->

      contrail::provision_contrailvm {$contrail::contrail_vcenter_vm_ips:
      } ->

      augeas { "ssh_root_access_no":
        context    => "/files/etc/ssh/sshd_config",
        changes    => ["set PermitRootLogin no",
                       "set PasswordAuthentication no"],
        notify     => Service["ssh"]
      }
    }
  }
}

