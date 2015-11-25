import inspect
import unittest

import os
from ConfigParser import ConfigParser

from mock import mock

import firefly
from firefly import FireflyIRC, irc, PluginAbstract, errors, containers
from firefly.containers import Server
from firefly.languages.aml import AgentMLLanguage
from firefly.languages.interface import LanguageInterface


class FireflyIRCTestCase(unittest.TestCase):
    """
    Base class for all FireflyIRC test cases
    """

    ARGS = {
        'when': '',
        'info': 'TestCase IRCd',
        'server_name': 'TestCase Server',
        'version': '1.3.5',
        'umodes': 'FHJLdfjl',
        'cmodes': 'FHJLdfjl',
        'options': ['one', 'two', 'three'],
        'channels': 42,
        'ops': 0,
        'user': 'Nick!~user@example.org',
        'channel': '#testchan',
        'message': 'Hello, world!',
        'set': False,
        'modes': 'dfj',
        'args': (1, 2, 3),
        'secs': 0.001345,
        'kicker': 'MeanOp',
        'nick': 'Nick',
        'quitMessage': 'Good riddance!',
        'kickee': 'AnnoyingUser',
        'data': 'Test data',
        'newTopic': "It's a new day!",
        'oldname': 'LameUser',
        'newname': 'CoolUser',
        'motd': ['This is the ', 'message of the day'],
        'prefix': None,
        'params': None,
        'command': None,
        'messages': None,

        'notice': None,
        'action': None
    }

    @mock.patch.object(FireflyIRC, 'load_configuration')
    def setUp(self, mock_load_configuration, **kwargs):
        """
        Set up the Unit Test
        """
        """
        Set up the Unit Test
        """
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config')

        self.server_config = ConfigParser()
        self.server_config.read(os.path.join(self.config_path, 'server.cfg'))

        self.channel_config = ConfigParser()
        self.channel_config.read(os.path.join(self.config_path, 'servers', 'irc.example.org.cfg'))

        self.identity_config = ConfigParser()
        self.identity_config.read(os.path.join(self.config_path, 'identities', 'test.cfg'))

        def load_configuration(name, plugin=None, basedir=None, default=None):
            if basedir == 'servers':
                return self.channel_config

            if basedir == 'identities':
                return self.identity_config

        mock_load_configuration.side_effect = load_configuration

        servers = []
        hostnames = self.server_config.sections()
        for hostname in hostnames:
            servers.append((hostname, self.server_config))

        self.hostname, self.config = servers.pop()


class MessageDeliveryTestCase(FireflyIRCTestCase):

    @mock.patch.object(firefly.IRCClient, 'msg')
    def test_channel_message(self, mock_msg):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))

        dest = containers.Destination(firefly_irc, '#testchan')
        firefly_irc.msg(dest, 'Hello, world!')

        mock_msg.assert_called_once_with(firefly_irc, '#testchan', 'Hello, world!', None)

    @mock.patch.object(firefly.IRCClient, 'msg')
    def test_user_message(self, mock_msg):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))

        host = containers.Hostmask('test_nick!~user@example.org')
        firefly_irc.msg(host, 'Hello, world!')

        mock_msg.assert_called_once_with(firefly_irc, 'test_nick', 'Hello, world!', None)

    @mock.patch.object(firefly.IRCClient, 'notice')
    def test_channel_notice(self, mock_notice):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))

        dest = containers.Destination(firefly_irc, '#testchan')
        firefly_irc.notice(dest, 'Hello, world!')

        mock_notice.assert_called_once_with(firefly_irc, '#testchan', 'Hello, world!')

    @mock.patch.object(firefly.IRCClient, 'notice')
    def test_user_notice(self, mock_notice):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))

        host = containers.Hostmask('test_nick!~user@example.org')
        firefly_irc.notice(host, 'Hello, world!')

        mock_notice.assert_called_once_with(firefly_irc, 'test_nick', 'Hello, world!')


# noinspection PyPep8Naming
class PluginEventTestCase(FireflyIRCTestCase):

    @mock.patch('firefly.IRCClient')
    @mock.patch.object(FireflyIRC, 'join')
    def test_event_bindings(self, mock_join, mock_class):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.language.get_reply = mock.Mock()
        firefly_irc.language.get_reply.return_value = None
        events = [(en, getattr(irc, en)) for en in dir(irc) if en.startswith('on_')]
        firefly_methods = dir(firefly_irc)

        # Make sure all of our event methods exist
        for event_name, meth_name in events:
            self.assertIn(meth_name, firefly_methods, 'Missing method {m} for event {e}'.format(m=meth_name, e=event_name))

        # Make sure the correct events are fired
        for event_name, meth_name in events:
            # First we grab our event method and its argument names so we can mock patch it
            method = getattr(firefly_irc, meth_name)
            margs = inspect.getargspec(method).args
            kwargs = {arg: (self.ARGS[arg] if arg in self.ARGS else None) for arg in margs if arg != 'self'}

            with mock.patch('firefly.FireflyIRC.{m}'.format(m=meth_name), firefly_irc._fire_event) as mock_method:
                with mock.patch.object(firefly_irc, '_fire_event') as mock_fire_event:
                    # Fire the event dispatcher and make sure it fires off the correct plugin event in return
                    method(**kwargs)
                    called_events = [c[1][0] for c in mock_fire_event.mock_calls]
                    self.assertIn(meth_name, called_events)

    @mock.patch.object(FireflyIRC, '_fire_event')
    @mock.patch.object(FireflyIRC, '_fire_command')
    @mock.patch.object(FireflyIRC, 'channelMessage')
    @mock.patch.object(FireflyIRC, 'privateMessage')
    def test_command_call(self, mock_privateMessage, mock_channelMessage, mock__fire_command,
                          mock__fire_event):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.language.get_reply = mock.Mock()
        firefly_irc.language.get_reply.return_value = None
        firefly_irc.privmsg('test_nick!~user@example.org', '#testchan', '>>> plugintest ping 3')

        _fire_command_args = mock__fire_command.call_args_list
        self.assertTrue(mock__fire_command.called)
        self.assertEqual(_fire_command_args[0][0][0], 'plugintest')
        self.assertEqual(_fire_command_args[0][0][1], 'ping')
        self.assertListEqual(_fire_command_args[0][0][2], ['3'])

        _fire_event_args = mock__fire_event.call_args_list
        self.assertFalse(_fire_event_args[0][0][1], 'has_reply was True when it should have been False')
        self.assertTrue(_fire_event_args[0][0][2], 'is_command was False when it should have been True')

        channelMessage_args = mock_channelMessage.call_args_list
        self.assertFalse(channelMessage_args[0][0][1], 'has_reply was True when it should have been False')
        self.assertTrue(channelMessage_args[0][0][2], 'is_command was False when it should have been True')

    @mock.patch.object(FireflyIRC, '_fire_event')
    @mock.patch.object(FireflyIRC, '_fire_command')
    @mock.patch.object(FireflyIRC, 'channelMessage')
    @mock.patch.object(FireflyIRC, 'privateMessage')
    def test_channel_message_routed(self, mock_privateMessage, mock_channelMessage, mock__fire_command,
                                    mock__fire_event):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.language.get_reply = mock.Mock()
        firefly_irc.language.get_reply.return_value = None
        firefly_irc.privmsg('test_nick!~user@example.org', '#testchan', 'Hello, world!')

        self.assertEqual(mock_channelMessage.call_count, 1)
        mock_privateMessage.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(FireflyIRC, '_fire_event')
    @mock.patch.object(FireflyIRC, '_fire_command')
    @mock.patch.object(FireflyIRC, 'channelMessage')
    @mock.patch.object(FireflyIRC, 'privateMessage')
    def test_private_message_routed(self, mock_privateMessage, mock_channelMessage, mock__fire_command,
                                    mock__fire_event):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.language.get_reply = mock.Mock()
        firefly_irc.language.get_reply.return_value = None
        firefly_irc.privmsg('test_nick!~user@example.org', 'test_nick', 'Hello, world!')

        self.assertEqual(mock_privateMessage.call_count, 1)
        mock_channelMessage.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(FireflyIRC, '_fire_event')
    @mock.patch.object(FireflyIRC, '_fire_command')
    @mock.patch.object(FireflyIRC, 'channelNotice')
    @mock.patch.object(FireflyIRC, 'privateNotice')
    def test_channel_notice_routed(self, mock_privateNotice, mock_channelNotice, mock__fire_command,
                                    mock__fire_event):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.noticed('test_nick!~user@example.org', '#testchan', 'Hello, world!')

        self.assertEqual(mock_channelNotice.call_count, 1)
        mock_privateNotice.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(FireflyIRC, '_fire_event')
    @mock.patch.object(FireflyIRC, '_fire_command')
    @mock.patch.object(FireflyIRC, 'channelNotice')
    @mock.patch.object(FireflyIRC, 'privateNotice')
    def test_private_notice_routed(self, mock_privateNotice, mock_channelNotice, mock__fire_command,
                                    mock__fire_event):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.noticed('test_nick!~user@example.org', 'test_nick', 'Hello, world!')

        self.assertEqual(mock_privateNotice.call_count, 1)
        mock_channelNotice.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(FireflyIRC, '_fire_event')
    @mock.patch.object(FireflyIRC, '_fire_command')
    @mock.patch.object(FireflyIRC, 'channelAction')
    @mock.patch.object(FireflyIRC, 'privateAction')
    def test_private_action_routed(self, mock_privateAction, mock_channelAction, mock__fire_command,
                                    mock__fire_event):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.action('test_nick!~user@example.org', '#testchan', 'waves')

        self.assertEqual(mock_channelAction.call_count, 1)
        mock_privateAction.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(FireflyIRC, '_fire_event')
    @mock.patch.object(FireflyIRC, '_fire_command')
    @mock.patch.object(FireflyIRC, 'channelAction')
    @mock.patch.object(FireflyIRC, 'privateAction')
    def test_private_action_routed(self, mock_privateAction, mock_channelAction, mock__fire_command,
                                    mock__fire_event):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc.action('test_nick!~user@example.org', 'test_nick', 'waves')

        self.assertEqual(mock_privateAction.call_count, 1)
        mock_channelAction.assert_not_called()
        mock__fire_command.assert_not_called()


class PluginCommandTestCase(FireflyIRCTestCase):

    class PluginTest(PluginAbstract):

        @irc.command()
        def ping(self, args):
            """
            @type   args:   firefly.args.ArgumentParser
            """
            args.add_argument('times', type=int, help='How many times to pong')
            args.add_argument('--message', help='The response message to use', default='pong')

            def _ping(args, response):
                """
                @type   args:       argparse.Namespace
                @type   response:   firefly.containers.Response
                """
                pongs = [args.message]
                pongs = pongs * args.times

                response.add_message(' '.join(pongs))

            return _ping

    def test_bind_command(self):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        firefly_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', firefly_irc.registry._commands)
        self.assertIn('ping', firefly_irc.registry._commands['plugintest'])

    def test_get_command(self):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        firefly_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', firefly_irc.registry._commands)
        self.assertIn('ping', firefly_irc.registry._commands['plugintest'])

        command = firefly_irc.registry.get_command('plugintest', 'ping')
        self.assertIsInstance(command, tuple)

    def test_get_command_bad_plugin(self):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        firefly_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', firefly_irc.registry._commands)
        self.assertIn('ping', firefly_irc.registry._commands['plugintest'])

        command = firefly_irc.registry.get_command('PLUGINtest', 'ping')
        self.assertIsInstance(command, tuple)
        self.assertRaises(errors.NoSuchPluginError, firefly_irc.registry.get_command, 'badplugin', 'ping')

    def test_get_command_bad_command(self):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        firefly_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', firefly_irc.registry._commands)
        self.assertIn('ping', firefly_irc.registry._commands['plugintest'])

        command = firefly_irc.registry.get_command('plugintest', 'pInG ')
        self.assertIsInstance(command, tuple)
        self.assertRaises(errors.NoSuchCommandError, firefly_irc.registry.get_command, 'plugintest', 'badcommand')

    @mock.patch.object(FireflyIRC, 'msg')
    def test_ping_once(self, mock_msg):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        firefly_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        dest = containers.Destination(firefly_irc, '#test')
        message = containers.Message('>>> plugintest ping 1', dest, containers.Hostmask('Nick!~user@example.org'))
        firefly_irc._fire_command('plugintest', 'ping', ['1'], message)

        mock_msg.assert_called_once_with(dest, 'pong')

    @mock.patch.object(FireflyIRC, 'msg')
    def test_ping_thrice(self, mock_msg):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        firefly_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        dest = containers.Destination(firefly_irc, 'test_nick')
        host = containers.Hostmask('test_nick!~user@example.org')
        message = containers.Message('>>> plugintest ping 3', dest, host)
        firefly_irc._fire_command('plugintest', 'ping', ['3'], message)

        mock_msg.assert_called_once_with(host, 'pong pong pong')

    @mock.patch.object(FireflyIRC, 'msg')
    def test_ping_with_option(self, mock_msg):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        firefly_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        dest = containers.Destination(firefly_irc, 'test_nick')
        host = containers.Hostmask('test_nick!~user@example.org')
        message = containers.Message('>>> plugintest ping 3 --message=wong', dest, host)
        firefly_irc._fire_command('plugintest', 'ping', ['3', '--message=wong'], message)

        mock_msg.assert_called_once_with(host, 'wong wong wong')


class LanguageTests(FireflyIRCTestCase):
    """
    Basic language instantiation tests
    """
    def test_default_instantiation(self):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        self.assertIsInstance(firefly_irc.language, LanguageInterface)

    def test_aml_instantiation(self):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        firefly_irc._load_language_interface('aml')
        self.assertIsInstance(firefly_irc.language, AgentMLLanguage)

    def test_bad_instantiation(self):
        firefly_irc = FireflyIRC(Server(self.hostname, self.config))
        self.assertRaises(ImportError, firefly_irc._load_language_interface, '_invalid_language_interface')
