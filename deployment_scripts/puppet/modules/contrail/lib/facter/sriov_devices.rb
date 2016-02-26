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

# This facter returns the version and build for the python-contrail package.
# It may be used to detect a version of contrail used in the environment.

require 'facter'

sriov_hash = Hash.new

Dir.foreach('/sys/class/net') do |network_interface|
  next if network_interface == '.' or network_interface == '..'
  network_interface_path = "/sys/class/net/" + network_interface
  if (File.exists?(network_interface_path + "/device/sriov_totalvfs") and
    not File.exists?(network_interface_path + "/master/bridge/bridge_id"))
    sriov_hash[network_interface] = Hash.new
    sriov_hash[network_interface]["totalvfs"] = IO.read(network_interface_path + "/device/sriov_totalvfs").to_i
    sriov_hash[network_interface]["numvfs"] = IO.read(network_interface_path + "/device/sriov_numvfs").to_i
  end
end


Facter.add("sriov_devices") do
  setcode do
    sriov_hash
  end
end
