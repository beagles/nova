#    Copyright 2015 OpenStack Foundation
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

from nova import test
from nova.virt import netutils
from oslo_serialization import jsonutils

vif_complete = {
    'id': 'vif_complete_id',
    'address': 'vif_complete_address',
    'devname': 'vif_complete_devname',
    'ovs_interfaceid': 'vif_complete_ovs_interfaceid',
    'vnic_type': 'vif_complete_vnic_type',
    'details': {
        'detail_a': 'detail_a_value',
        'detail_b': 'detail_b_value'}
}

# template for basic VIF information. VIF details needs to be generated.
environment_template = [
    'VIF_ID=%(id)s',
    'VIF_MAC_ADDRESS=%(address)s',
    'VIF_DEVNAME=%(devname)s',
    'VIF_OVS_INTERFACEID=%(ovs_interfaceid)s',
    'VIF_VNIC_TYPE=%(vnic_type)s',
]


# XXX Comparing the 'template' generated environment vs the netutils method
# *is* kind of lame because we are basically comparing algorithms. A better
# approach might be to not use the generated, but include a helper snippet
# that allows it to be generated manually
def generate_environment(vif):
    result = []
    for e in environment_template:
        result.append(e % vif)

    details = vif.get('details')
    if details:
        for k, v in details.iteritems():
            result.append('VIF_DETAILS_%s=%s' % (k, jsonutils.dumps(v)))

    return result


class VirtNetutilsTestCase(test.TestCase):

    # No setUp or teardown necessary. A really thorough unit test would
    # verify that the convert_vif_to_env doesn't modify the handed to it.
    # We don't do that too often AFAICT.
    def verify_environment(self, expected_env, generated_env):
        def _convert_env_to_dict(e):
            result = dict()
            for l in e:
                k, v = l.split('=')
                result[k] = l
            return result

        expected = _convert_env_to_dict(expected_env)
        generated = _convert_env_to_dict(generated_env)

        # So the general idea is compare all of expected_values with the
        # generated values. Then verify that the generated values
        # don't contain any values that were not in expected_values

        for k, v in expected.iteritems():
            self.assertEqual(v, generated.get(k, 'XXX_INVALID_VALUE'))

        for k in generated:
            self.assertIn(k, expected)

    def test_convert_vif_to_env_complete(self):
        environment_vars = netutils.convert_vif_to_env(vif_complete)
        self.verify_environment(generate_environment(vif_complete),
                                environment_vars)

    def test_convert_vif_to_env_missing_required_field(self):
        test_vif = vif_complete.copy()
        del test_vif['vnic_type']
        environment_vars = netutils.convert_vif_to_env(test_vif)
        self.verify_environment(generate_environment(test_vif),
                                environment_vars)

    def test_convert_vif_to_env_missing_optional_field(self):
        test_vif = vif_complete.copy()
        del test_vif['details']
        environment_vars = netutils.convert_vif_to_env(test_vif)
        self.verify_environment(generate_environment(test_vif),
                                environment_vars)

    def test_convert_vif_to_env_details_fence_post(self):
        test_vif = vif_complete.copy()
        test_vif['details'] = {'one-detail': 'one-detail-value'}
        environment_vars = netutils.convert_vif_to_env(test_vif)
        self.verify_environment(generate_environment(test_vif),
                                environment_vars)

    def test_convert_vif_to_env_details_with_none_value(self):
        test_vif = vif_complete.copy()
        test_vif['details'] = {'one-detail': None}
        environment_vars = netutils.convert_vif_to_env(test_vif)
        self.verify_environment(generate_environment(test_vif),
                                environment_vars)
