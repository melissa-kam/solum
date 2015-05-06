# Copyright 2014 - Rackspace Hosting
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json

from heatclient import exc
import mock
from oslo.config import cfg
import yaml

from solum.common import exception
from solum.deployer.handlers import heat as heat_handler
from solum.objects import assembly
from solum.tests import base
from solum.tests import fakes
from solum.tests import utils


STATES = assembly.States


class HandlerTest(base.BaseTestCase):
    def setUp(self):
        super(HandlerTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_create(self):
        handler = heat_handler.Handler()
        handler.echo = mock.MagicMock()
        handler.echo({}, 'foo')
        handler.echo.assert_called_once_with({}, 'foo')

    @mock.patch('solum.deployer.handlers.heat.tlog')
    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.catalog.get')
    @mock.patch('solum.objects.registry')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_deploy_docker_on_vm_with_dreg(self, mock_clients, mock_registry,
                                           mock_get_templ, mock_cond, m_log):
        handler = heat_handler.Handler()

        fake_assembly = fakes.FakeAssembly()

        m_log.TenantLogger.call.return_value = mock.MagicMock()

        mock_registry.Assembly.get_by_id.return_value = fake_assembly
        fake_template = self._get_fake_template()
        template = self._get_tmpl_for_docker_reg(fake_assembly, fake_template,
                                                 'created_image_id')
        cfg.CONF.api.image_format = "vm"
        cfg.CONF.worker.image_storage = "docker_registry"
        mock_get_templ.return_value = template
        handler._find_id_if_stack_exists = mock.MagicMock(return_value=(None))
        stacks = mock_clients.return_value.heat.return_value.stacks
        stacks.create.return_value = {"stack": {
            "id": "fake_id",
            "links": [{"href": "http://fake.ref",
                       "rel": "self"}]}}
        handler._check_stack_status = mock.MagicMock()
        handler.deploy(self.ctx, 77, 'created_image_id', [80])
        stacks = mock_clients.return_value.heat.return_value.stacks
        stacks.create.assert_called_once()
        assign_and_create_mock = mock_registry.Component.assign_and_create
        comp_name = 'Heat_Stack_for_%s' % fake_assembly.name
        assign_and_create_mock.assert_called_once_with(self.ctx,
                                                       fake_assembly,
                                                       comp_name,
                                                       'heat_stack',
                                                       'Heat Stack test',
                                                       'http://fake.ref',
                                                       'fake_id')

    @mock.patch('solum.deployer.handlers.heat.tlog')
    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.catalog.get')
    @mock.patch('solum.objects.registry')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_deploy_docker_on_vm_swift(self, mock_clients, mock_registry,
                                       mock_get_templ, mock_cond, m_log):
        handler = heat_handler.Handler()

        m_log.TenantLogger.call.return_value = mock.MagicMock()
        fake_assembly = fakes.FakeAssembly()
        mock_registry.Assembly.get_by_id.return_value = fake_assembly
        fake_template = self._get_fake_template()
        img = ("http://a.b.c/d?temp_url_sig=v&temp_url_expires=v"
               "DOCKER_IMAGE_TAG=tenant-name-ts-commit")
        template = self._get_tmpl_for_swift(fake_assembly, fake_template, img)
        cfg.CONF.api.image_format = "vm"
        cfg.CONF.worker.image_storage = "swift"
        cfg.CONF.deployer.flavor = "flavor"
        cfg.CONF.deployer.image = "coreos"
        mock_get_templ.return_value = template
        handler._find_id_if_stack_exists = mock.MagicMock(return_value=(None))
        stacks = mock_clients.return_value.heat.return_value.stacks
        stacks.create.return_value = {"stack": {
            "id": "fake_id",
            "links": [{"href": "http://fake.ref",
                       "rel": "self"}]}}
        handler._check_stack_status = mock.MagicMock()
        handler.deploy(self.ctx, 77, img, [80])
        stacks = mock_clients.return_value.heat.return_value.stacks

        parameters = {'name': fake_assembly.uuid,
                      'count': 1,
                      'flavor': "flavor",
                      'image': "coreos"}

        stacks.create.assert_called_once_with(stack_name='faker-test_uuid',
                                              template=template,
                                              parameters=parameters)
        assign_and_create_mock = mock_registry.Component.assign_and_create
        comp_name = 'Heat_Stack_for_%s' % fake_assembly.name
        assign_and_create_mock.assert_called_once_with(self.ctx,
                                                       fake_assembly,
                                                       comp_name,
                                                       'heat_stack',
                                                       'Heat Stack test',
                                                       'http://fake.ref',
                                                       'fake_id')
        m_log.log.assert_called_once()

    @mock.patch('solum.deployer.handlers.heat.tlog')
    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.catalog.get')
    @mock.patch('solum.objects.registry')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_comp_name_error(self, mock_clients, mock_registry,
                             mock_get_templ, mock_cond, m_log):
        handler = heat_handler.Handler()

        m_log.TenantLogger.call.return_value = mock.MagicMock()

        fake_assembly = fakes.FakeAssembly()
        mock_registry.Assembly.get_by_id.return_value = fake_assembly
        fake_template = json.dumps({'description': 'test'})
        mock_get_templ.return_value = fake_template
        handler._find_id_if_stack_exists = mock.MagicMock(return_value=(None))
        stacks = mock_clients.return_value.heat.return_value.stacks
        stacks.create.return_value = {"stack": {
            "id": "fake_id",
            "links": [{"href": "http://fake.ref",
                       "rel": "self"}]}}
        handler._check_stack_status = mock.MagicMock()
        handler.deploy(self.ctx, 77, 'created_image_id', [80])
        assign_and_create_mock = mock_registry.Component.assign_and_create
        comp_name = 'Heat Stack for %s' % fake_assembly.name
        self.assertRaises(AssertionError,
                          assign_and_create_mock.assert_called_once_with,
                          comp_name)
        m_log.log.assert_called_once()

    @mock.patch('solum.deployer.handlers.heat.tlog')
    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.catalog.get')
    @mock.patch('solum.objects.registry')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_deploy_docker(self, mock_clients, mock_registry,
                           mock_get_templ, mock_cond, m_log):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()
        mock_registry.Assembly.get_by_id.return_value = fake_assembly

        m_log.TenantLogger.call.return_value = mock.MagicMock()

        cfg.CONF.api.image_format = "docker"

        fake_template = self._get_fake_template()
        template = self._get_tmpl_for_docker_reg(fake_assembly, fake_template,
                                                 'created_image_id')
        mock_get_templ.return_value = template

        handler._find_id_if_stack_exists = mock.MagicMock(return_value=(None))
        stacks = mock_clients.return_value.heat.return_value.stacks
        stacks.create.return_value = {"stack": {
            "id": "fake_id",
            "links": [{"href": "http://fake.ref",
                       "rel": "self"}]}}
        handler._check_stack_status = mock.MagicMock()
        handler.deploy(self.ctx, 77, 'created_image_id', [80])
        parameters = {'image': 'created_image_id',
                      'app_name': 'faker',
                      'port': 80}
        stacks.create.assert_called_once_with(stack_name='faker-test_uuid',
                                              template=template,
                                              parameters=parameters)
        assign_and_create_mock = mock_registry.Component.assign_and_create
        comp_name = 'Heat_Stack_for_%s' % fake_assembly.name
        assign_and_create_mock.assert_called_once_with(self.ctx,
                                                       fake_assembly,
                                                       comp_name,
                                                       'heat_stack',
                                                       'Heat Stack test',
                                                       'http://fake.ref',
                                                       'fake_id')

    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.clients.OpenStackClients')
    @mock.patch('httplib2.Http')
    def test_update_assembly_status(self, mock_http, mock_clients, mock_ua):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()
        stack = mock.MagicMock()
        stack.status = 'COMPLETE'
        mock_clients.heat().stacks.get.return_value = stack

        resp = {'status': '200'}
        conn = mock.MagicMock()
        conn.request.return_value = [resp, '']
        mock_http.return_value = conn

        cfg.CONF.deployer.du_attempts = 1

        mock_logger = mock.MagicMock()
        handler._parse_server_url = mock.MagicMock(return_value=('xyz'))
        handler._check_stack_status(self.ctx, fake_assembly.id, mock_clients,
                                    'fake_id', [80], mock_logger)

        c1 = mock.call(fake_assembly.id,
                       {'status': STATES.STARTING_APP,
                        'application_uri': 'xyz:80'})

        c2 = mock.call(fake_assembly.id,
                       {'status': 'READY'})

        calls = [c1, c2]

        mock_ua.assert_has_calls(calls, any_order=False)

    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.clients.OpenStackClients')
    @mock.patch('httplib2.Http')
    def test_update_assembly_status_multiple_ports(self, mock_http,
                                                   mock_clients, mock_ua):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()
        stack = mock.MagicMock()
        stack.status = 'COMPLETE'
        mock_clients.heat().stacks.get.return_value = stack

        resp = {'status': '200'}
        conn = mock.MagicMock()
        conn.request.return_value = [resp, '']
        mock_http.return_value = conn

        cfg.CONF.deployer.du_attempts = 1

        mock_logger = mock.MagicMock()
        handler._parse_server_url = mock.MagicMock(return_value=('xyz'))
        handler._check_stack_status(self.ctx, fake_assembly.id, mock_clients,
                                    'fake_id', [80, 81], mock_logger)

        c1 = mock.call(fake_assembly.id,
                       {'status': STATES.STARTING_APP,
                        'application_uri': 'xyz:[80,81]'})

        c2 = mock.call(fake_assembly.id,
                       {'status': 'READY'})

        calls = [c1, c2]

        mock_ua.assert_has_calls(calls, any_order=False)

    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_update_assembly_status_failed(self, mock_clients, mock_ua):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()
        stack = mock.MagicMock()
        stack.status = 'FAILED'
        mock_clients.heat().stacks.get.return_value = stack
        mock_logger = mock.MagicMock()
        handler._check_stack_status(self.ctx, fake_assembly.id, mock_clients,
                                    'fake_id', [80], mock_logger)
        mock_ua.assert_called_once_with(fake_assembly.id,
                                        {'status':
                                         STATES.ERROR_STACK_CREATE_FAILED})

    @mock.patch('solum.conductor.api.API.update_assembly')
    def test_get_template(self, mock_update_assembly):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        image_format = 'vm'
        image_storage = 'glance'
        image_id = 'abc'
        ports = [80]
        mock_logger = mock.MagicMock()
        template = handler._get_template(self.ctx, image_format,
                                         image_storage, image_id,
                                         fake_assembly, ports, mock_logger)
        self.assertIsNone(template)
        mock_update_assembly.assert_called_once_with(fake_assembly.id,
                                                     {'status': STATES.ERROR})

    @mock.patch('solum.conductor.api.API.update_assembly')
    def test_get_template_vm_glance(self, mock_update_assembly):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        image_format = 'vm'
        image_storage = 'glance'
        image_id = 'abc'
        ports = [80]
        mock_logger = mock.MagicMock()
        template = handler._get_template(self.ctx, image_format,
                                         image_storage, image_id,
                                         fake_assembly, ports, mock_logger)
        self.assertIsNone(template)
        mock_update_assembly.assert_called_once_with(fake_assembly.id,
                                                     {'status': STATES.ERROR})

    @mock.patch('solum.common.catalog.get')
    def test_get_template_vm_docker_reg(self, mock_catalog_get):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        template_getter = mock.MagicMock()
        template_getter.return_value = self._get_fake_template()
        handler._get_template_for_docker_reg = template_getter

        image_format = 'vm'
        image_storage = 'docker_registry'
        image_id = 'abc'
        ports = [80]
        mock_logger = mock.MagicMock()
        template = handler._get_template(self.ctx, image_format,
                                         image_storage, image_id,
                                         fake_assembly, ports, mock_logger)
        self.assertIsNotNone(template)
        handler._get_template_for_docker_reg.assert_called_once()
        mock_catalog_get.assert_called_once_with('templates', 'coreos')

    @mock.patch('solum.common.catalog.get')
    def test_get_template_vm_swift(self, mock_catalog_get):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        template_getter = mock.MagicMock()
        template_getter.return_value = self._get_fake_template()
        handler._get_template_for_swift = template_getter

        image_format = 'vm'
        image_storage = 'swift'
        image_id = 'abc'
        ports = [80]
        mock_logger = mock.MagicMock()
        template = handler._get_template(self.ctx, image_format,
                                         image_storage, image_id,
                                         fake_assembly, ports, mock_logger)
        self.assertIsNotNone(template)
        handler._get_template_for_swift.assert_called_once()
        mock_catalog_get.assert_called_once_with('templates', 'coreos')

    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.catalog.get')
    def test_get_template_vm_swift_error(self, mock_catalog_get, mock_ua):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        exc_obj = exception.ObjectNotFound()
        mock_catalog_get.side_effect = exc_obj

        template_getter = mock.MagicMock()
        template_getter.return_value = self._get_fake_template()
        handler._get_template_for_swift = template_getter

        image_format = 'vm'
        image_storage = 'swift'
        image_id = 'abc'
        ports = [80]
        mock_logger = mock.MagicMock()
        template = handler._get_template(self.ctx, image_format,
                                         image_storage, image_id,
                                         fake_assembly, ports, mock_logger)
        self.assertIsNone(template)
        mock_ua.assert_called_once_with(fake_assembly.id,
                                        {'status': STATES.ERROR})

        assert not handler._get_template_for_swift.called

    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.catalog.get')
    def test_get_template_docker_read_error(self, mock_catalog_get, mock_ua):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        exc_obj = exception.ObjectNotFound()
        mock_catalog_get.side_effect = exc_obj

        template_getter = mock.MagicMock()
        template_getter.return_value = self._get_fake_template()
        handler._get_template_for_swift = template_getter

        image_format = 'docker'
        image_storage = 'swift'
        image_id = 'abc'
        ports = [80]
        mock_logger = mock.MagicMock()
        template = handler._get_template(self.ctx, image_format,
                                         image_storage, image_id,
                                         fake_assembly, ports, mock_logger)
        self.assertIsNone(template)
        mock_ua.assert_called_once_with(fake_assembly.id,
                                        {'status': STATES.ERROR})

    @mock.patch('solum.common.heat_utils.get_network_parameters')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_get_parameters_for_docker(self, mock_clients, mock_heat_utils):

        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        image_format = 'docker'
        image_id = 'abc DOCKER_IMAGE_TAG=abc'
        ports = [80]

        mock_logger = mock.MagicMock()

        params = handler._get_parameters(self.ctx, image_format,
                                         image_id, fake_assembly,
                                         ports, mock_clients, mock_logger)

        self.assertEqual(params['app_name'], fake_assembly.name)
        self.assertEqual(params['image'], 'abc')
        self.assertEqual(params['port'], 80)

    @mock.patch('solum.common.heat_utils.get_network_parameters')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_get_parameters_for_vm(self, mock_clients, mock_heat_utils):

        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        image_format = 'vm'
        image_id = 'abc DOCKER_IMAGE_TAG=abc'
        ports = [80]

        mock_logger = mock.MagicMock()

        cfg.CONF.set_override('flavor', 'abc', group='deployer')
        cfg.CONF.set_override('image', 'def', group='deployer')

        params = handler._get_parameters(self.ctx, image_format,
                                         image_id, fake_assembly,
                                         ports, mock_clients, mock_logger)

        self.assertEqual(params['name'], str(fake_assembly.uuid))
        self.assertEqual(params['count'], 1)
        self.assertEqual(params['flavor'], 'abc')
        self.assertEqual(params['image'], 'def')
        self.assertIsNone(params.get('port'))

    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.heat_utils.get_network_parameters')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_get_parameters_for_unrecognized_img_format(self, mock_clients,
                                                        mock_heat_utils,
                                                        mock_ua):

        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        image_format = 'abc'
        image_id = 'abc DOCKER_IMAGE_TAG=abc'
        ports = [80]

        mock_logger = mock.MagicMock()

        params = handler._get_parameters(self.ctx, image_format,
                                         image_id, fake_assembly,
                                         ports, mock_clients, mock_logger)

        self.assertIsNone(params)

        mock_ua.assert_called_once_with(fake_assembly.id,
                                        {'status':
                                         STATES.ERROR})

    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_check_stack_status(self, mock_clients, mock_ua):
        handler = heat_handler.Handler()
        fake_assembly = fakes.FakeAssembly()

        mock_clients.heat().stacks.get.side_effect = Exception()

        cfg.CONF.set_override('wait_interval', 1, group='deployer')
        cfg.CONF.set_override('growth_factor', 1, group='deployer')
        cfg.CONF.set_override('max_attempts', 1, group='deployer')

        mock_logger = mock.MagicMock()
        handler._check_stack_status(self.ctx, fake_assembly.id, mock_clients,
                                    'fake_id', [80], mock_logger)
        mock_ua.assert_called_once_with(fake_assembly.id,
                                        {'status':
                                         STATES.ERROR_STACK_CREATE_FAILED})

    def test_parse_server_url(self):
        handler = heat_handler.Handler()
        heat_output = mock.MagicMock()
        heat_output._info = {"id": "fake_id",
                             "outputs": [{"output_value": "192.168.78.21",
                                          "description": "IP", "output_key":
                                          "public_ip"},
                                         {"output_value":
                                          "http://192.168.78.21:5000",
                                          "description": "URL", "output_key":
                                          "URL"}]}
        host_url = handler._parse_server_url(heat_output)
        self.assertEqual(host_url, "192.168.78.21")

    def test_find_id_if_stack_exists(self):
        handler = heat_handler.Handler()
        assem = mock.MagicMock
        assem.heat_stack_component = mock.MagicMock
        assem.heat_stack_component.heat_stack_id = '123'
        id = handler._find_id_if_stack_exists(assem)
        self.assertEqual(id, '123')

    @mock.patch('solum.deployer.handlers.heat.tlog')
    @mock.patch('solum.objects.registry')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_destroy_success(self, mock_client, mock_registry, m_log):
        fake_assem = fakes.FakeAssembly()
        mock_registry.Assembly.get_by_id.return_value = fake_assem

        handler = heat_handler.Handler()

        m_log.TenantLogger.call.return_value = mock.MagicMock()

        handler._find_id_if_stack_exists = mock.MagicMock(return_value='42')
        mock_heat = mock_client.return_value.heat.return_value
        mock_heat.stacks.get.side_effect = exc.HTTPNotFound

        cfg.CONF.deployer.max_attempts = 1
        cfg.CONF.deployer.wait_interval = 0
        cfg.CONF.deployer.growth_factor = 1.2

        handler.destroy_assembly(self.ctx, fake_assem.id)

        mock_client.heat.stacks.delete.assert_called_once()
        fake_assem.destroy.assert_called_once()
        m_log.log.assert_called_once()

    @mock.patch('solum.deployer.handlers.heat.tlog')
    @mock.patch('solum.conductor.api.API.update_assembly')
    @mock.patch('solum.objects.registry')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_destroy_error(self, mock_client, mock_registry, mock_cond, m_log):
        fake_assem = fakes.FakeAssembly()
        mock_registry.Assembly.get_by_id.return_value = fake_assem

        m_log.TenantLogger.call.return_value = mock.MagicMock()

        handler = heat_handler.Handler()
        handler._find_id_if_stack_exists = mock.MagicMock(return_value='42')

        cfg.CONF.deployer.max_attempts = 1
        cfg.CONF.deployer.wait_interval = 0
        cfg.CONF.deployer.growth_factor = 1.2

        handler.destroy_assembly(self.ctx, fake_assem.id)

        mock_client.heat.stacks.delete.assert_called_once()
        mock_cond.assert_called_once_with(
            fake_assem.id, {'status': STATES.ERROR_STACK_DELETE_FAILED})

    @mock.patch('solum.deployer.handlers.heat.tlog')
    @mock.patch('solum.objects.registry')
    @mock.patch('solum.common.clients.OpenStackClients')
    def test_destroy_absent(self, mock_client, mock_registry, mock_tlogger):

        fake_assem = fakes.FakeAssembly()
        mock_registry.Assembly.get_by_id.return_value = fake_assem

        mock_tlogger.TenantLogger.call.return_value = mock.MagicMock()

        hh = heat_handler.Handler()
        hh._find_id_if_stack_exists = mock.MagicMock(return_value=None)
        hh.destroy_assembly(self.ctx, fake_assem.id)

        assert not mock_client.heat.stacks.delete.called
        fake_assem.destroy.assert_called_once()
        mock_tlogger.log.assert_called_once()
        mock_tlogger.upload.assert_called_once()

    @mock.patch('solum.objects.registry')
    def test_successful_deploy_destroys_twins(self, mock_registry):
        handler = heat_handler.Handler()
        old_app = fakes.FakeAssembly()
        old_app.name = 'old app'
        old_app.status = 'READY'

        new_app = fakes.FakeAssembly()
        new_app.id = 9
        new_app.plan_id = old_app.plan_id
        new_app.name = 'new app'
        new_app.status = 'READY'

        self.assertEqual(old_app.plan_id, new_app.plan_id)
        self.assertEqual(old_app.plan_uuid, new_app.plan_uuid)
        mock_registry.AssemblyList.get_all.return_value = [old_app, new_app]

        handler.destroy_assembly = mock.MagicMock()
        handler._destroy_other_assemblies(self.ctx, new_app)
        handler.destroy_assembly.assert_called_once_with(self.ctx, old_app.id)

    @mock.patch('solum.objects.registry')
    def test_successful_deploy_preserves_others(self, mock_registry):
        handler = heat_handler.Handler()
        old_app = fakes.FakeAssembly()
        old_app.name = 'old app'
        old_app.status = 'READY'

        new_app = fakes.FakeAssembly()
        new_app.id = 9
        new_app.plan_uuid = 'new fake plan uuid'
        new_app.name = 'new app'
        new_app.status = 'READY'

        self.assertNotEqual(old_app.plan_id, new_app.plan_id)
        self.assertNotEqual(old_app.plan_uuid, new_app.plan_uuid)
        mock_registry.AssemblyList.get_all.return_value = [old_app, new_app]

        handler.destroy_assembly = mock.MagicMock()
        handler._destroy_other_assemblies(self.ctx, new_app)
        self.assertEqual(0, handler.destroy_assembly.call_count)

    @mock.patch('solum.objects.registry')
    def test_successful_deploy_preserves_notreadies(self, mock_registry):
        handler = heat_handler.Handler()
        old_app = fakes.FakeAssembly()
        old_app.name = 'old app'
        old_app.status = 'BUILDING'

        new_app = fakes.FakeAssembly()
        new_app.id = 9
        new_app.plan_id = old_app.plan_id
        new_app.name = 'new app'
        new_app.status = 'READY'

        self.assertEqual(old_app.plan_id, new_app.plan_id)
        self.assertEqual(old_app.plan_uuid, new_app.plan_uuid)
        mock_registry.AssemblyList.get_all.return_value = [old_app, new_app]

        handler.destroy_assembly = mock.MagicMock()
        handler._destroy_other_assemblies(self.ctx, new_app)
        self.assertEqual(0, handler.destroy_assembly.call_count)

    @mock.patch('solum.objects.registry')
    def test_unsuccessful_deploy_preserves_everyone(self, mock_registry):
        handler = heat_handler.Handler()
        old_app = fakes.FakeAssembly()
        old_app.name = 'old app'
        old_app.status = 'READY'

        new_app = fakes.FakeAssembly()
        new_app.id = 9
        new_app.plan_id = old_app.plan_id
        new_app.name = 'new app'
        new_app.status = 'ERROR'

        self.assertEqual(old_app.plan_id, new_app.plan_id)
        self.assertEqual(old_app.plan_uuid, new_app.plan_uuid)
        mock_registry.AssemblyList.get_all.return_value = [old_app, new_app]

        handler.destroy_assembly = mock.MagicMock()
        handler._destroy_other_assemblies(self.ctx, new_app)
        self.assertEqual(0, handler.destroy_assembly.call_count)

    def _get_fake_template(self):
        t = "description: test\n"
        t += "resources:\n"
        t += "  compute_instance:\n"
        t += "    properties:\n"
        t += "      user_data:\n"
        t += "        str_replace:\n"
        t += "          {template:"
        t += "            #!/bin/bash -x\n"
        t += "            #Invoke the container\n"
        t += "}\n"
        return t

    def _get_tmpl_for_docker_reg(self, assem, template, image_id):
        template_bdy = yaml.safe_load(template)

        run_docker = ('#!/bin/bash -x\n'
                      '# Invoke the container\n'
                      'docker run -p 80:80 -d {img}')
        run_docker = run_docker.format(img=image_id)
        comp_instance = template_bdy['resources']['compute_instance']
        user_data = comp_instance['properties']['user_data']
        user_data['str_replace']['template'] = run_docker
        comp_instance['properties']['user_data'] = user_data
        template_bdy['resources']['compute_instance'] = comp_instance
        template = yaml.dump(template_bdy)
        return template

    def _get_tmpl_for_swift(self, assem, template, image_tar_location):
        template_bdy = yaml.safe_load(template)

        image_loc_and_du_name = image_tar_location.split("DOCKER_IMAGE_TAG=")
        image_tar_location = image_loc_and_du_name[0]
        du_name = image_loc_and_du_name[1]

        run_docker = ('#!/bin/bash -x\n'
                      '# Invoke the container\n'
                      'wget \"{image_tar_location}\" --output-document={du}\n'
                      'docker load < {du}\n'
                      'docker run -p 80:80 -d {du}')
        run_docker = run_docker.format(image_tar_location=image_tar_location,
                                       du=du_name)

        comp_instance = template_bdy['resources']['compute_instance']
        user_data = comp_instance['properties']['user_data']
        user_data['str_replace']['template'] = run_docker
        comp_instance['properties']['user_data'] = user_data
        template_bdy['resources']['compute_instance'] = comp_instance
        template = yaml.safe_dump(template_bdy,
                                  encoding='utf-8',
                                  allow_unicode=True)
        return template
