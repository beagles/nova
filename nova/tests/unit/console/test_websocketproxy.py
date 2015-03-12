# All Rights Reserved.
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

"""Tests for nova websocketproxy."""


import mock

from nova.console import websocketproxy
from nova import exception
from nova import test


class NovaProxyRequestHandlerBaseTestCase(test.NoDBTestCase):

    def setUp(self):
        super(NovaProxyRequestHandlerBaseTestCase, self).setUp()

        self.wh = websocketproxy.NovaProxyRequestHandlerBase()
        self.wh.socket = mock.MagicMock()
        self.wh.msg = mock.MagicMock()
        self.wh.do_proxy = mock.MagicMock()
        self.wh.headers = mock.MagicMock()

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/?token=123-456-789"

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_token_invalid(self, check_token):
        check_token.return_value = False

        self.wh.path = "http://127.0.0.1/?token=XXX"

        self.assertRaises(exception.InvalidToken,
                          self.wh.new_websocket_client)
        check_token.assert_called_with(mock.ANY, token="XXX")

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader.return_value = "token=123-456-789"

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_novnc_token_invalid(self, check_token):
        check_token.return_value = False

        self.wh.path = "http://127.0.0.1/"
        self.wh.headers.getheader.return_value = "token=XXX"

        self.assertRaises(exception.InvalidToken,
                          self.wh.new_websocket_client)
        check_token.assert_called_with(mock.ANY, token="XXX")

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_internal_access_path(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'internal_access_path': 'vmid'
        }

        tsock = mock.MagicMock()
        tsock.recv.return_value = "HTTP/1.1 200 OK\r\n\r\n"

        self.wh.socket.return_value = tsock
        self.wh.path = "http://127.0.0.1/?token=123-456-789"

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with(tsock)

    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_internal_access_path_err(self, check_token):
        check_token.return_value = {
            'host': 'node1',
            'port': '10000',
            'internal_access_path': 'xxx'
        }

        tsock = mock.MagicMock()
        tsock.recv.return_value = "HTTP/1.1 500 Internal Server Error\r\n\r\n"

        self.wh.socket.return_value = tsock
        self.wh.path = "http://127.0.0.1/?token=123-456-789"

        self.assertRaises(exception.InvalidConnectionInfo,
                          self.wh.new_websocket_client)
        check_token.assert_called_with(mock.ANY, token="123-456-789")

    @mock.patch('sys.version_info')
    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_py273_good_scheme(
            self, check_token, version_info):
        version_info.return_value = (2, 7, 3)
        check_token.return_value = {
            'host': 'node1',
            'port': '10000'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "http://127.0.0.1/?token=123-456-789"

        self.wh.new_websocket_client()

        check_token.assert_called_with(mock.ANY, token="123-456-789")
        self.wh.socket.assert_called_with('node1', 10000, connect=True)
        self.wh.do_proxy.assert_called_with('<socket>')

    @mock.patch('sys.version_info')
    @mock.patch('nova.consoleauth.rpcapi.ConsoleAuthAPI.check_token')
    def test_new_websocket_client_py273_special_scheme(
            self, check_token, version_info):
        version_info.return_value = (2, 7, 3)
        check_token.return_value = {
            'host': 'node1',
            'port': '10000'
        }
        self.wh.socket.return_value = '<socket>'
        self.wh.path = "ws://127.0.0.1/?token=123-456-789"

        self.assertRaises(exception.NovaException,
                          self.wh.new_websocket_client)

    @mock.patch('socket.getfqdn')
    def test_address_string_doesnt_do_reverse_dns_lookup(self, getfqdn):
        request_mock = mock.MagicMock()
        request_mock.makefile().readline.side_effect = [
            'GET /vnc.html?token=123-456-789 HTTP/1.1\r\n',
            ''
        ]
        server_mock = mock.MagicMock()
        client_address = ('8.8.8.8', 54321)

        handler = websocketproxy.NovaProxyRequestHandler(
            request_mock, client_address, server_mock)
        handler.log_message('log message using client address context info')

        self.assertFalse(getfqdn.called)  # no reverse dns look up
        self.assertEqual(handler.address_string(), '8.8.8.8')  # plain address
