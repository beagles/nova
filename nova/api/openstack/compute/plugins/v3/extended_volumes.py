#   Copyright 2013 OpenStack Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

"""The Extended Volumes API extension."""
from nova.api.openstack import api_version_request
from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova import compute
from nova import objects
from nova import volume

ALIAS = "os-extended-volumes"
authorize = extensions.soft_extension_authorizer('compute', 'v3:' + ALIAS)


class ExtendedVolumesController(wsgi.Controller):
    def __init__(self, *args, **kwargs):
        super(ExtendedVolumesController, self).__init__(*args, **kwargs)
        self.compute_api = compute.API()
        self.volume_api = volume.API()

    def _extend_server(self, context, server, instance, requested_version):
        bdms = objects.BlockDeviceMappingList.get_by_instance_uuid(
                context, instance.uuid)
        volumes_attached = []
        api_version = api_version_request.APIVersionRequest('2.3')
        for bdm in bdms:
            if bdm.get('volume_id'):
                volume_attached = {'id': bdm['volume_id']}
                if requested_version >= api_version:
                    volume_attached['delete_on_termination'] = (
                        bdm['delete_on_termination'])
                volumes_attached.append(volume_attached)
        key = "%s:volumes_attached" % ExtendedVolumes.alias
        server[key] = volumes_attached

    @wsgi.extends
    def show(self, req, resp_obj, id):
        context = req.environ['nova.context']
        if authorize(context):
            server = resp_obj.obj['server']
            db_instance = req.get_db_instance(server['id'])
            # server['id'] is guaranteed to be in the cache due to
            # the core API adding it in its 'show' method.
            self._extend_server(context, server, db_instance,
                                req.api_version_request)

    @wsgi.extends
    def detail(self, req, resp_obj):
        context = req.environ['nova.context']
        if authorize(context):
            servers = list(resp_obj.obj['servers'])
            for server in servers:
                db_instance = req.get_db_instance(server['id'])
                # server['id'] is guaranteed to be in the cache due to
                # the core API adding it in its 'detail' method.
                self._extend_server(context, server, db_instance,
                                    req.api_version_request)


class ExtendedVolumes(extensions.V3APIExtensionBase):
    """Extended Volumes support."""

    name = "ExtendedVolumes"
    alias = ALIAS
    version = 1

    def get_controller_extensions(self):
        controller = ExtendedVolumesController()
        extension = extensions.ControllerExtension(self, 'servers', controller)
        return [extension]

    def get_resources(self):
        return []
