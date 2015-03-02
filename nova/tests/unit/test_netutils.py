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

import mock

from nova import exception
from nova import test
from nova.virt import netutils
from oslo_concurrency import processutils
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


class MockInstance(object):

    @property
    def uuid(self):
        return 'test_id'

vif_complete_expected = [
    'VIF_INSTANCE_ID=test_id',
    'VIF_ID=vif_complete_id',
    'VIF_MAC_ADDRESS=vif_complete_address',
    'VIF_DEVNAME=vif_complete_devname',
    'VIF_OVS_INTERFACEID=vif_complete_ovs_interfaceid',
    'VIF_VNIC_TYPE=vif_complete_vnic_type',
    'VIF_DETAILS_detail_b="detail_b_value"',
    'VIF_DETAILS_detail_a="detail_a_value"',
]


def _execute_stub(environment, script, command):
    pass


def _execute_process_exception(environment, script, command):
    raise processutils.ProcessExecutionError(
        stdout='running %s' % script,
        stderr='VIF_PLUG_ERROR',
        exit_code=42,
        cmd=script,
        description='FOOBAR! SIERRA-SQUARE-DELTA-SQUARE!')


class VirtNetutilsTestCase(test.TestCase):

    # No setUp or teardown necessary. A really thorough unit test would
    # verify that the create_vif_plug_env doesn't modify the handed to it.
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
        # don't contain any values that were not in expected_values.
        for k, v in expected.iteritems():
            self.assertEqual(v, generated.get(k, 'XXX_INVALID_VALUE'))

        for k in generated:
            self.assertIn(k, expected)

    def test_create_vif_plug_env_complete(self):
        environment_vars = netutils.create_vif_plug_env(MockInstance(),
                                                        vif_complete)
        self.verify_environment(vif_complete_expected,
                                environment_vars)

    def test_create_vif_plug_env_missing_required_field(self):
        # The particular scenario tried here is a pathological in a sense
        # because it cannot really ever happen with the way
        # nova.network.models.VIF is implemented - but that isn't the point
        # really.  The point of the test is to make sure that
        # create_vif_plug_env rejects invalid data.

        test_vif = vif_complete.copy()
        del test_vif['vnic_type']
        self.assertRaises(exception.VirtualInterfacePlugException,
                          netutils.create_vif_plug_env, MockInstance(),
                          test_vif)

    def test_create_vif_plug_env_missing_optional_field(self):
        test_vif = vif_complete.copy()
        del test_vif['details']
        expected = [e for e in vif_complete_expected if not
                    e.startswith('VIF_DETAILS')]
        environment_vars = netutils.create_vif_plug_env(MockInstance(),
                                                        test_vif)
        self.verify_environment(expected, environment_vars)

    def test_create_vif_plug_env_details_fence_post(self):
        test_vif = vif_complete.copy()
        test_vif['details'] = {'one-detail': 'one-detail-value'}
        expected = [e for e in vif_complete_expected if not
                    e.startswith('VIF_DETAILS')]
        expected.append('VIF_DETAILS_one-detail="one-detail-value"')
        environment_vars = netutils.create_vif_plug_env(MockInstance(),
                                                        test_vif)
        self.verify_environment(expected, environment_vars)

    def test_create_vif_plug_env_details_with_none_value(self):
        test_vif = vif_complete.copy()
        test_vif['details'] = {'one-detail': None}
        environment_vars = netutils.create_vif_plug_env(MockInstance(),
                                                        test_vif)
        expected = [e for e in vif_complete_expected if not
                    e.startswith('VIF_DETAILS')]
        expected.append('VIF_DETAILS_one-detail=null')
        self.verify_environment(expected, environment_vars)

    @mock.patch('nova.utils.execute', side_effect=_execute_stub)
    def test_run_plug_script(self, execute_function):
        # Lame case.. just verifying that it is called at all.
        netutils.run_plug_script(MockInstance(), vif_complete,
                                 'some_script', 'plug')
        self.assertEqual(execute_function.call_count, 1)

    @mock.patch('nova.utils.execute', side_effect=_execute_stub)
    def test_run_plug_missing_required(self, execute_function):
        # Another almost lame case, just a level up from the
        # create_vif_plug_env's test, but still valuable to verify that
        # something doesn't happen to screw up the execption AND make sure
        # the script isn't executed anyways.
        test_vif = vif_complete.copy()
        del test_vif['vnic_type']
        self.assertRaises(exception.VirtualInterfacePlugException,
                          netutils.run_plug_script, MockInstance(),
                          test_vif, 'some_script', 'plug')
        self.assertEqual(execute_function.call_count, 0)

    @mock.patch('nova.utils.execute',
                side_effect=_execute_process_exception)
    def test_run_plug_with_process_exception(self, execute_function):
        try:
            netutils.run_plug_script(MockInstance(), vif_complete,
                                     'some_script', 'plug')
            self.assertEqual('We should not have gotten here', 'oh oh')
        except exception.VirtualInterfacePlugException as e:
            # Granted, this is a pretty soft check but it gives some
            # idea that we got where we wanted.
            self.assertTrue(e.message.startswith('Failed to plug'))

            # Should be obvious that this is so, but let's make sure our
            # test got us here by the intended means.
            self.assertEqual(execute_function.call_count, 1)


def generate_test_data(vif):
    """A test maintenance method for generating the expected data. The test
    strings are dumped to stdout and need to be manually copied and pasted into
    this test. The general idea is to avoid bugs in the test from mirroring
    bugs in the code and ignoring bugs. Still, it is tedious to manually
    construct the appropriate data sets so this is a bit of a bootstrap.
    """

    # template for basic VIF information. VIF details needs to be generated.
    environment_template = [
        '\'VIF_ID=%(id)s\',',
        '\'VIF_MAC_ADDRESS=%(address)s\',',
        '\'VIF_DEVNAME=%(devname)s\',',
        '\'VIF_OVS_INTERFACEID=%(ovs_interfaceid)s\',',
        '\'VIF_VNIC_TYPE=%(vnic_type)s\',',
    ]
    print('[')
    print('    VIF_INSTANCE_ID=test_id,')
    for e in environment_template:
        print('   ', e % vif)

    details = vif.get('details')
    if details:
        for k, v in details.iteritems():
            print('    \'VIF_DETAILS_%s=%s\',' % (k, jsonutils.dumps(v)))
    print (']')

if __name__ == "__main__":
    """Run as a module to generate test data template"""
    generate_test_data(vif_complete)
