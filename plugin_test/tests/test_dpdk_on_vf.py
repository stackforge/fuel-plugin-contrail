"""Copyright 2016 Mirantis, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import os

from proboscis import test
from proboscis import asserts

from fuelweb_test import logger
from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test.settings import CONTRAIL_PLUGIN_PACK_UB_PATH
from fuelweb_test.tests.base_test_case import SetupEnvironment
from fuelweb_test.tests.base_test_case import TestBasic

from helpers import vsrx
from helpers import plugin
from helpers import openstack
from helpers import baremetal
from tests.test_contrail_check import TestContrailCheck


@test(groups=["plugins"])
class DPDKonVFTests(TestBasic):
    """DPDKTests."""

    pack_copy_path = '/var/www/nailgun/plugins/contrail-5.0'
    add_package = '/var/www/nailgun/plugins/contrail-5.0/'\
                  'repositories/ubuntu/contrail-setup*'
    ostf_msg = 'OSTF tests passed successfully.'
    cluster_id = ''
    pack_path = CONTRAIL_PLUGIN_PACK_UB_PATH
    CONTRAIL_DISTRIBUTION = os.environ.get('CONTRAIL_DISTRIBUTION')
    bm_drv = baremetal.BMDriver()

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_ha_dpdk_on_vf", "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_ha_dpdk_on_vf(self):
        """Check Contrail deploy on HA environment.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration and CEPH storage
            2. Enable and configure Contrail plugin
            3. Enable dedicated analytics DB
            4. Enable DPDK on VF feature
            5. Deploy cluster with following node configuration:
                node-01: 'controller';
                node-02: 'controller';
                node-03: 'controller', 'ceph-osd';
                node-04: 'compute', 'ceph-osd';
                node-05: 'compute', 'ceph-osd';
                node-06: 'contrail-db';
                node-07: 'contrail-config';
                node-08: 'contrail-control';
                node-09: 'contrail-analytics', 'contrail-analytics-db';
                node-dpdk: 'compute', dpdk';
            6. Run OSTF tests
            7. Run contrail health check tests

        Duration 120 min

        """
        conf_contrail = {
            "dedicated_analytics_db": True,
            "dpdk_on_vf": True,
        }
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True,
                                                'volumes_ceph': True,
                                                'ephemeral_ceph': True,
                                                'objects_ceph': True,
                                                'volumes_lvm': False})
        self.bm_drv.host_prepare()

        plugin.show_range(self, 2, 4)
        # activate plugin with DPDK feature
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)

        conf_nodes = {
            'slave-01': ['controller'],
            'slave-02': ['controller'],
            'slave-03': ['controller', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-05': ['compute', 'ceph-osd'],
            'slave-06': ['contrail-db'],
            'slave-07': ['contrail-config'],
            'slave-08': ['contrail-control'],
            'slave-09': ['contrail-analytics', 'contrail-analytics-db'],
        }
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.show_step(5)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity', 'ha'],
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(6)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_dpdk_on_vf_add_compute",
                  "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_add_compute(self):
        """Verify that Contrail compute role can be added after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Enable dedicated analytics DB
            4. Enable DPDK on VF feature
            5. Deploy cluster with following node configuration:
                node-1: 'controller', 'ceph-osd';
                node-2: 'contrail-config', 'contrail-control',
                    'contrail-db';
                node-3: 'compute', 'ceph-osd';
                node-4: 'compute', 'ceph-osd';
                node-5: 'compute', 'ceph-osd';
                node-dpdk: 'compute', 'dpdk';
                node-7: 'contrail-analytics', 'contrail-analytics-db';
            6. Run OSTF tests
            7. Add one node with following configuration:
                node-5: "compute", "ceph-osd";
            8. Deploy changes
            9. Run OSTF tests
            10. Run contrail health check tests

        """
        conf_contrail = {
            "dedicated_analytics_db": True,
            "dpdk_on_vf": True,
        }
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True,
                                                'volumes_ceph': True,
                                                'ephemeral_ceph': True,
                                                'objects_ceph': True,
                                                'volumes_lvm': False})
        self.bm_drv.host_prepare()

        plugin.show_range(self, 2, 4)
        # activate plugin with DPDK feature
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)
        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd'],
            'slave-02': ['contrail-config',
                         'contrail-control',
                         'contrail-db'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-05': ['compute', 'ceph-osd'],
            'slave-07': ['contrail-analytics',
                         'contrail-analytics-db'],
        }
        conf_compute = {'slave-06': ['compute', 'ceph-osd']}

        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(5)
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

        # Add Compute node and check again
        self.show_step(6)
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_compute,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        self.show_step(7)
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(8)
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(9)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_dpdk_on_vf_delete_compute",
                  "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_delete_compute(self):
        """Verify that Contrail compute role can be deleted after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Enable DPDK on VF feature
            4. Deploy cluster with following node configuration:
                node-01: 'controller';
                node-02: 'contrail-control', 'contrail-config',
                    'contrail-db', 'contrail-analytics';
                node-03: 'contrail-db';
                node-04: 'compute', 'cinder';
                node-05: 'compute';
                node-06: 'contrail-db';
            5. Run OSTF tests
            6. Delete node-05 with "compute" role
            7. Deploy changes
            8. Run OSTF tests
            9. Run contrail health check tests

        """
        conf_contrail = {
            "dpdk_on_vf": True,
        }
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9)
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with DPDK feature
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(3)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)
        conf_no_compute = {
            'slave-01': ['controller'],
            'slave-02': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['contrail-db'],
            'slave-04': ['compute', 'cinder'],
            # node-05
            'slave-06': ['contrail-db'],
        }
        conf_compute = {'slave-05': ['compute']}

        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=dict(conf_no_compute, **conf_compute),
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.show_step(4)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

        # Delete Compute node and check again
        self.show_step(5)
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_compute,
            pending_addition=False, pending_deletion=True,
            update_interfaces=False)

        # Deploy cluster
        self.show_step(6)
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.show_step(7)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity'],
                                   should_fail=1,
                                   failed_test_name=['Check that required '
                                                     'services are running']
                                   )
            self.show_step(8)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_dpdk_on_vf_add_dpdk",
                  "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_add_dpdk(self):
        """Verify that DPDK role can be added after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Enable dedicated analytics DB
            4. Enable DPDK on VF feature
            5. Deploy cluster with following node configuration:
                node-01: 'controller', 'ceph-osd';
                node-02: 'contrail-config', 'contrail-control',
                    'contrail-db', 'contrail-analytics';
                node-03: 'compute', 'ceph-osd';
                node-04: 'compute', 'ceph-osd';
                node-05: 'controller', 'cinder';
                node-06: 'controller', 'cinder';
                node-07: 'contrail-analytics-db';
            6. Run OSTF tests
            7. Run contrail health check tests
            8. Add one node with following configuration:
                node-dpdk: "compute", "dpdk";
            9. Deploy changes
            10. Run OSTF tests
            11. Run contrail health check tests

        """
        conf_contrail = {
            "dedicated_analytics_db": True,
            "dpdk_on_vf": True,
        }
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True})
        self.bm_drv.host_prepare()

        plugin.show_range(self, 2, 4)
        # activate plugin with DPDK feature
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(4)
        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd'],
            'slave-02': ['contrail-config',
                         'contrail-control',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-05': ['controller', 'cinder'],
            'slave-06': ['controller', 'cinder'],
            'slave-07': ['contrail-analytics-db'],
        }
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_nodes,
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(5)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity', 'ha'])
            self.show_step(6)
            TestContrailCheck(self).cloud_check(['contrail'])

        self.show_step(7)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)
        self.show_step(8)
        openstack.deploy_cluster(self)

        self.show_step(9)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            self.show_step(10)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_dpdk_on_vf_delete_dpdk",
                  "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_delete_dpdk(self):
        """Verify that DPDK role can be deleted after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Enable DPDK on VF feature
            4. Deploy cluster with following node configuration:
                node-01: 'controller', 'ceph-osd', 'cinder';
                node-02: 'contrail-control', 'contrail-config',
                    'contrail-db', 'contrail-analytics';
                node-03: 'compute', 'ceph-osd';
                node-04: 'compute', 'ceph-osd';
                node-dpdk: 'compute', 'dpdk';
            5. Run OSTF tests
            6. Run contrail health check tests
            7. Delete node "node-dpdk" with "dpdk" and "compute" roles
            8. Deploy changes
            9. Run OSTF tests
            10. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True})
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with DPDK feature
        conf_contrail = {"dpdk_on_vf": True}
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(3)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)
        conf_no_dpdk = {
            'slave-01': ['controller', 'ceph-osd', 'cinder'],
            'slave-02': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
        }

        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_no_dpdk,
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(4)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            self.show_step(5)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

        self.show_step(6)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'],
                                    pending_deletion=True,
                                    pending_addition=False)
        self.show_step(7)
        openstack.deploy_cluster(self)

        self.show_step(8)
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity'],
                                   should_fail=1,
                                   failed_test_name=['Check that required '
                                                     'services are running']
                                   )
            self.show_step(9)
            TestContrailCheck(self).cloud_check(['contrail'])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_dpdk_on_vf_add_controller",
                  "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_add_controller(self):
        """Verify that Contrail controller role can be added after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Enable dedicated analytics DB
            4. Enable DPDK on VF feature
            5. Deploy cluster with following node configuration:
                node-1: 'controller', 'ceph-osd';
                node-2: 'contrail-config', 'contrail-control',
                    'contrail-db', 'contrail-analytics';
                node-3: 'compute', 'ceph-osd';
                node-4: 'compute', 'ceph-osd';
                node-6: 'contrail-analytics', 'contrail-analytics-db';
            6. Run OSTF tests
            7. Add one node with following configuration:
                node-5: 'controller', 'ceph-osd';
            8. Deploy changes
            9. Run OSTF tests
            10. Run contrail health check tests

        """
        conf_contrail = {
            "dedicated_analytics_db": True,
            "dpdk_on_vf": True,
        }
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True,
                                                'volumes_ceph': True,
                                                'ephemeral_ceph': True,
                                                'objects_ceph': True,
                                                'volumes_lvm': False})
        self.bm_drv.host_prepare()

        plugin.show_range(self, 2, 4)
        # activate plugin with DPDK feature
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)
        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd'],
            'slave-02': ['contrail-config',
                         'contrail-control',
                         'contrail-db'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-06': ['contrail-analytics',
                         'contrail-analytics-db'],
        }
        conf_controller = {'slave-05': ['controller', 'ceph-osd']}

        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(5)
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

        # Add Compute node and check again
        self.show_step(6)
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_controller,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        self.show_step(7)
        openstack.deploy_cluster(self)
        # Run OSTF tests
        self.show_step(8)
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(9)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

    @test(depends_on=[SetupEnvironment.prepare_slaves_5],
          groups=["contrail_dpdk_on_vf_delete_controller",
                  "contrail_dpdk_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_delete_controller(self):
        """Verify that Contrail controller role can be deleted after deploying.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Enable DPDK on VF feature
            4. Deploy cluster with following node configuration:
                node-01: 'controller';
                node-02: 'contrail-control', 'contrail-config',
                    'contrail-db', 'contrail-analytics';
                node-03: 'controller';
                node-04: 'compute', 'cinder';
                node-05: 'controller';
            5. Run OSTF tests
            6. Delete node-01 with "controller" role
            7. Deploy changes
            8. Run OSTF tests
            9. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=5)
        self.bm_drv.host_prepare()

        self.show_step(2)
        # activate plugin with DPDK on VF feature
        conf_contrail = {"dpdk_on_vf": True}
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        plugin.show_range(self, 3, 4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)
        conf_no_compute = {
            'slave-01': ['controller'],
            'slave-02': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['controller'],
            'slave-04': ['compute', 'cinder'],
            'slave-05': ['controller'],
        }
        conf_controller = {'slave-01': ['controller']}

        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=dict(conf_no_compute, **conf_controller),
            update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

        # Delete Compute node and check again
        plugin.show_range(self, 5, 7)
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes_dict=conf_controller,
            pending_addition=False, pending_deletion=True,
            update_interfaces=False)

        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        if vsrx_setup_result:
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity'],
                                   should_fail=1,
                                   failed_test_name=['Check that required '
                                                     'services are running']
                                   )
            self.show_step(8)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_dpdk_on_vf_disable",
                  "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_disable(self):
        """Verify that DPDK on VF feature could be disabled.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Enable DPDK on VF feature
            4. Deploy cluster with following node configuration:
                node-01: 'controller', 'ceph-osd', 'cinder';
                node-02: 'contrail-control', 'contrail-config',
                    'contrail-db', 'contrail-analytics';
                node-03: 'compute', 'ceph-osd';
                node-04: 'compute', 'ceph-osd';
                node-dpdk: 'compute', 'dpdk';
            5. Run OSTF tests
            6. Run contrail health check tests
            7. Disable DPDK on VF feature
            8. Deploy changes
            9. Run OSTF tests
            10. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True})
        self.bm_drv.host_prepare()

        plugin.show_range(self, 2, 4)
        # activate plugin with DPDK feature
        conf_contrail = {"dpdk_on_vf": True}
        plugin.activate_dpdk(self, **conf_contrail)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)

        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd', 'cinder'],
            'slave-02': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
        }
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.show_step(5)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity', 'ha'],
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(6)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

        self.show_step(7)
        # activate plugin with DPDK feature
        conf_contrail = {"dpdk_on_vf": False}
        plugin.activate_dpdk(self, **conf_contrail)
        self.show_step(8)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.show_step(9)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity', 'ha'],
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(10)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

    @test(depends_on=[SetupEnvironment.prepare_slaves_9],
          groups=["contrail_dpdk_on_vf_enable",
                  "contrail_dpdk_on_vf_tests"])
    @log_snapshot_after_test
    def contrail_dpdk_on_vf_enable(self):
        """Verify that DPDK on VF feature could be enabled.

        Scenario:
            1. Create an environment with "Neutron with tunneling
               segmentation" as a network configuration
            2. Enable and configure Contrail plugin
            3. Deploy cluster with following node configuration:
                node-01: 'controller', 'ceph-osd', 'cinder';
                node-02: 'contrail-control', 'contrail-config',
                    'contrail-db', 'contrail-analytics';
                node-03: 'compute', 'ceph-osd';
                node-04: 'compute', 'ceph-osd';
                node-dpdk: 'compute', 'dpdk';
            4. Run OSTF tests
            5. Run contrail health check tests
            6. Enable DPDK on VF feature
            7. Deploy changes
            8. Run OSTF tests
            9. Run contrail health check tests

        """
        self.show_step(1)
        plugin.prepare_contrail_plugin(self, slaves=9,
                                       options={'images_ceph': True})
        self.bm_drv.host_prepare()

        plugin.show_range(self, 2, 4)
        # activate plugin with DPDK feature
        plugin.activate_dpdk(self)
        # activate vSRX image
        vsrx_setup_result = vsrx.activate()

        self.show_step(4)
        self.bm_drv.setup_fuel_node(self,
                                    cluster_id=self.cluster_id,
                                    roles=['compute', 'dpdk'])
        openstack.setup_hugepages(self)

        conf_nodes = {
            'slave-01': ['controller', 'ceph-osd', 'cinder'],
            'slave-02': ['contrail-control',
                         'contrail-config',
                         'contrail-db',
                         'contrail-analytics'],
            'slave-03': ['compute', 'ceph-osd'],
            'slave-04': ['compute', 'ceph-osd'],
        }
        # Cluster configuration
        self.fuel_web.update_nodes(self.cluster_id,
                                   nodes_dict=conf_nodes,
                                   update_interfaces=False)
        self.bm_drv.update_vm_node_interfaces(self, self.cluster_id)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.show_step(5)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity', 'ha'],
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(6)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])

        self.show_step(7)
        # activate plugin with DPDK feature
        conf_contrail = {"dpdk_on_vf": True}
        plugin.activate_dpdk(self, **conf_contrail)
        self.show_step(8)
        # Deploy cluster
        openstack.deploy_cluster(self)
        # Run OSTF tests
        # FIXME: remove shouldfail, when livemigration+DPDK works
        if vsrx_setup_result:
            self.show_step(9)
            self.fuel_web.run_ostf(cluster_id=self.cluster_id,
                                   test_sets=['smoke', 'sanity', 'ha'],
                                   should_fail=1,
                                   failed_test_name=['Instance live migration']
                                   )
            self.show_step(10)
            TestContrailCheck(self).cloud_check(
                ['dpdk', 'contrail'],
                should_fail=["test_dpdk_boot_snapshot_vm"])
