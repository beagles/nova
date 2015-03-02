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

import copy

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

vif_complete_expected = [
    'VIF_ID=vif_complete_id',
    'VIF_MAC_ADDRESS=vif_complete_address',
    'VIF_DEVNAME=vif_complete_devname',
    'VIF_OVS_INTERFACEID=vif_complete_ovs_interfaceid',
    'VIF_VNIC_TYPE=vif_complete_vnic_type',
    'VIF_DETAILS_detail_b="detail_b_value"',
    'VIF_DETAILS_detail_a="detail_a_value"',
]

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
        self.verify_environment(vif_complete_expected,
                                environment_vars)

    def test_convert_vif_to_env_missing_required_field(self):
        test_vif = vif_complete.copy()
        del test_vif['vnic_type']
        expected = [e for e in vif_complete_expected if not
                    e.startswith('VIF_VNIC_TYPE')]
        environment_vars = netutils.convert_vif_to_env(test_vif)
        self.verify_environment(expected, environment_vars)

    def test_convert_vif_to_env_missing_optional_field(self):
        test_vif = vif_complete.copy()
        del test_vif['details']
        expected = [e for e in vif_complete_expected if not
                    e.startswith('VIF_DETAILS')]
        environment_vars = netutils.convert_vif_to_env(test_vif)
        self.verify_environment(expected, environment_vars)

    def test_convert_vif_to_env_details_fence_post(self):
        test_vif = vif_complete.copy()
        test_vif['details'] = {'one-detail': 'one-detail-value'}
        expected = [e for e in vif_complete_expected if not
                    e.startswith('VIF_DETAILS')]
        expected.append('VIF_DETAILS_one-detail="one-detail-value"')
        environment_vars = netutils.convert_vif_to_env(test_vif)
        self.verify_environment(expected, environment_vars)

    def test_convert_vif_to_env_details_with_none_value(self):
        test_vif = vif_complete.copy()
        test_vif['details'] = {'one-detail': None}
        environment_vars = netutils.convert_vif_to_env(test_vif)
        expected = [e for e in vif_complete_expected if not
                    e.startswith('VIF_DETAILS')]
        expected.append('VIF_DETAILS_one-detail=null')
        self.verify_environment(expected, environment_vars)


def generate_test_data(vif):
    """A test maintenance method for generating the expected data. The test
    strings are dumped to stdout and need to be manually copied and pasted into
    this test. The general idea is to avoid bugs in the test from mirroring
    bugs in the code and ignoring bugs. Still, it is tedious to manually
    construct the appropriate data sets so this is a bit of a bootstrap."""

    # template for basic VIF information. VIF details needs to be generated.
    environment_template = [
        '\'VIF_ID=%(id)s\',',
        '\'VIF_MAC_ADDRESS=%(address)s\',',
        '\'VIF_DEVNAME=%(devname)s\',',
        '\'VIF_OVS_INTERFACEID=%(ovs_interfaceid)s\',',
        '\'VIF_VNIC_TYPE=%(vnic_type)s\',',
    ]
    print '['
    for e in environment_template:
        print '   ', e % vif

    details = vif.get('details')
    if details:
        for k, v in details.iteritems():
            print '    \'VIF_DETAILS_%s=%s\',' % (k, jsonutils.dumps(v))
    print ']'

if __name__ == "__main__":
    """Run as a module to generate test data template"""
    generate_test_data(vif_complete)
