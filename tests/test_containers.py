import os
import unittest
from ConfigParser import ConfigParser

import mock

from ene_irc import EneIRC
from ene_irc.containers import Server, Channel


class ServerTestCase(unittest.TestCase):

    @mock.patch.object(EneIRC, 'load_configuration')
    def setUp(self, mock_load_configuration):
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config')

        self.server_config = ConfigParser()
        self.server_config.read(os.path.join(self.config_path, 'server.cfg'))

        self.channel_config = ConfigParser()
        self.channel_config.read(os.path.join(self.config_path, 'servers', 'irc.example.org.cfg'))
        
        mock_load_configuration.return_value = self.channel_config
        self.server = Server('irc.example.org', self.server_config)

    def test_server_container_attributes(self):
        self.assertIsInstance(self.server._config, ConfigParser)

        self.assertEqual(self.server.hostname, 'irc.example.org')
        self.assertTrue(self.server.enabled)
        self.assertTrue(self.server.auto_connect)
        self.assertEqual(self.server.nick, 'Ene')
        self.assertEqual(self.server.username, 'Ene')
        self.assertEqual(self.server.realname, 'Nose Tests')
        self.assertIsNone(self.server.password)
        self.assertEqual(self.server.port, 6669)
        self.assertFalse(self.server.ssl)

    def test_server_channel_containers_length(self):
        self.assertEqual(len(self.server.channels), 3)
        
    def test_first_server_channel_attributes(self):
        first = self.server.channels.pop(0)
        self.assertIsInstance(first, Channel)
        self.assertIsInstance(first._config, ConfigParser)
        
        self.assertIs(first.server, self.server)
        self.assertEqual(first.name, '#first')
        self.assertFalse(first.autojoin)
        self.assertIsNone(first.password)
        
    def test_second_server_channel_attributes(self):
        second = self.server.channels.pop(1)
        self.assertIsInstance(second, Channel)
        self.assertIsInstance(second._config, ConfigParser)
        
        self.assertIs(second.server, self.server)
        self.assertEqual(second.name, '#second')
        self.assertTrue(second.autojoin)
        self.assertIsNone(second.password)
        
    def test_third_server_channel_attributes(self):
        third = self.server.channels.pop(2)
        self.assertIsInstance(third, Channel)
        self.assertIsInstance(third._config, ConfigParser)
        
        self.assertIs(third.server, self.server)
        self.assertEqual(third.name, '#third')
        self.assertFalse(third.autojoin)
        self.assertEqual(third.password, 'secret')
