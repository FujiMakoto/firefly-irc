import inspect
import unittest

from mock import mock

import ene_irc
from ene_irc import EneIRC, irc, PluginAbstract, errors, containers
from ene_irc.containers import Server
from ene_irc.languages.aml import AgentMLLanguage
from ene_irc.languages.interface import LanguageInterface


class EneIRCTestCase(unittest.TestCase):
    """
    Base class for all EneIRC test cases
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

    def setUp(self, **kwargs):
        """
        Set up the Unit Test
        """
        """
        Set up the Unit Test
        """
        servers_config = EneIRC.load_configuration('servers')
        servers = []
        hostnames = servers_config.sections()
        for hostname in hostnames:
            servers.append((hostname, servers_config))

        self.hostname, self.config = servers.pop()


class MessageDeliveryTestCase(EneIRCTestCase):

    @mock.patch.object(ene_irc.IRCClient, 'msg')
    def test_channel_message(self, mock_msg):
        ene = EneIRC(Server(self.hostname, self.config))

        dest = containers.Destination(ene, '#testchan')
        ene.msg(dest, 'Hello, world!')

        mock_msg.assert_called_once_with(ene, '#testchan', 'Hello, world!', None)

    @mock.patch.object(ene_irc.IRCClient, 'msg')
    def test_user_message(self, mock_msg):
        ene = EneIRC(Server(self.hostname, self.config))

        host = containers.Hostmask('test_nick!~user@example.org')
        ene.msg(host, 'Hello, world!')

        mock_msg.assert_called_once_with(ene, 'test_nick', 'Hello, world!', None)

    @mock.patch.object(ene_irc.IRCClient, 'notice')
    def test_channel_notice(self, mock_notice):
        ene = EneIRC(Server(self.hostname, self.config))

        dest = containers.Destination(ene, '#testchan')
        ene.notice(dest, 'Hello, world!')

        mock_notice.assert_called_once_with(ene, '#testchan', 'Hello, world!')

    @mock.patch.object(ene_irc.IRCClient, 'notice')
    def test_user_notice(self, mock_notice):
        ene = EneIRC(Server(self.hostname, self.config))

        host = containers.Hostmask('test_nick!~user@example.org')
        ene.notice(host, 'Hello, world!')

        mock_notice.assert_called_once_with(ene, 'test_nick', 'Hello, world!')


# noinspection PyPep8Naming
class PluginEventTestCase(EneIRCTestCase):

    @mock.patch('ene_irc.IRCClient')
    @mock.patch.object(EneIRC, 'join')
    def test_event_bindings(self, mock_join, mock_class):
        ene = EneIRC(Server(self.hostname, self.config))
        events = [(en, getattr(irc, en)) for en in dir(irc) if en.startswith('on_')]
        ene_methods = dir(ene)

        # Make sure all of our event methods exist
        for event_name, meth_name in events:
            self.assertIn(meth_name, ene_methods, 'Missing method {m} for event {e}'.format(m=meth_name, e=event_name))

        # Make sure the correct events are fired
        for event_name, meth_name in events:
            # First we grab our event method and its argument names so we can mock patch it
            method = getattr(ene, meth_name)
            margs = inspect.getargspec(method).args
            kwargs = {arg: (self.ARGS[arg] if arg in self.ARGS else None) for arg in margs if arg != 'self'}

            with mock.patch('ene_irc.EneIRC.{m}'.format(m=meth_name), ene._fire_event) as mock_method:
                with mock.patch.object(ene, '_fire_event') as mock_fire_event:
                    # Fire the event dispatcher and make sure it fires off the correct plugin event in return
                    method(**kwargs)
                    called_events = [c[1][0] for c in mock_fire_event.mock_calls]
                    self.assertIn(meth_name, called_events)

    @mock.patch.object(EneIRC, '_fire_event')
    @mock.patch.object(EneIRC, '_fire_command')
    @mock.patch.object(EneIRC, 'channelMessage')
    @mock.patch.object(EneIRC, 'privateMessage')
    def test_command_call(self, mock_privateMessage, mock_channelMessage, mock__fire_command,
                          mock__fire_event):
        ene = EneIRC(Server(self.hostname, self.config))
        ene.privmsg('test_nick!~user@example.org', '#testchan', '>>> plugintest ping 3')

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

    @mock.patch.object(EneIRC, '_fire_event')
    @mock.patch.object(EneIRC, '_fire_command')
    @mock.patch.object(EneIRC, 'channelMessage')
    @mock.patch.object(EneIRC, 'privateMessage')
    def test_channel_message_routed(self, mock_privateMessage, mock_channelMessage, mock__fire_command,
                                    mock__fire_event):
        ene = EneIRC(Server(self.hostname, self.config))
        ene.privmsg('test_nick!~user@example.org', '#testchan', 'Hello, world!')

        self.assertEqual(mock_channelMessage.call_count, 1)
        mock_privateMessage.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(EneIRC, '_fire_event')
    @mock.patch.object(EneIRC, '_fire_command')
    @mock.patch.object(EneIRC, 'channelMessage')
    @mock.patch.object(EneIRC, 'privateMessage')
    def test_private_message_routed(self, mock_privateMessage, mock_channelMessage, mock__fire_command,
                                    mock__fire_event):
        ene = EneIRC(Server(self.hostname, self.config))
        ene.privmsg('test_nick!~user@example.org', 'test_nick', 'Hello, world!')

        self.assertEqual(mock_privateMessage.call_count, 1)
        mock_channelMessage.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(EneIRC, '_fire_event')
    @mock.patch.object(EneIRC, '_fire_command')
    @mock.patch.object(EneIRC, 'channelNotice')
    @mock.patch.object(EneIRC, 'privateNotice')
    def test_channel_notice_routed(self, mock_privateNotice, mock_channelNotice, mock__fire_command,
                                    mock__fire_event):
        ene = EneIRC(Server(self.hostname, self.config))
        ene.noticed('test_nick!~user@example.org', '#testchan', 'Hello, world!')

        self.assertEqual(mock_channelNotice.call_count, 1)
        mock_privateNotice.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(EneIRC, '_fire_event')
    @mock.patch.object(EneIRC, '_fire_command')
    @mock.patch.object(EneIRC, 'channelNotice')
    @mock.patch.object(EneIRC, 'privateNotice')
    def test_private_notice_routed(self, mock_privateNotice, mock_channelNotice, mock__fire_command,
                                    mock__fire_event):
        ene = EneIRC(Server(self.hostname, self.config))
        ene.noticed('test_nick!~user@example.org', 'test_nick', 'Hello, world!')

        self.assertEqual(mock_privateNotice.call_count, 1)
        mock_channelNotice.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(EneIRC, '_fire_event')
    @mock.patch.object(EneIRC, '_fire_command')
    @mock.patch.object(EneIRC, 'channelAction')
    @mock.patch.object(EneIRC, 'privateAction')
    def test_private_action_routed(self, mock_privateAction, mock_channelAction, mock__fire_command,
                                    mock__fire_event):
        ene = EneIRC(Server(self.hostname, self.config))
        ene.action('test_nick!~user@example.org', '#testchan', 'waves')

        self.assertEqual(mock_channelAction.call_count, 1)
        mock_privateAction.assert_not_called()
        mock__fire_command.assert_not_called()

    @mock.patch.object(EneIRC, '_fire_event')
    @mock.patch.object(EneIRC, '_fire_command')
    @mock.patch.object(EneIRC, 'channelAction')
    @mock.patch.object(EneIRC, 'privateAction')
    def test_private_action_routed(self, mock_privateAction, mock_channelAction, mock__fire_command,
                                    mock__fire_event):
        ene = EneIRC(Server(self.hostname, self.config))
        ene.action('test_nick!~user@example.org', 'test_nick', 'waves')

        self.assertEqual(mock_privateAction.call_count, 1)
        mock_channelAction.assert_not_called()
        mock__fire_command.assert_not_called()


class PluginCommandTestCase(EneIRCTestCase):

    class PluginTest(PluginAbstract):

        @irc.command()
        def ping(self, args):
            """
            @type   args:   ene_irc.args.ArgumentParser
            """
            args.add_argument('times', type=int, help='How many times to pong')
            args.add_argument('--message', help='The response message to use', default='pong')

            def _ping(args, message):
                """
                @type   args:       argparse.Namespace
                @type   message:    ene_irc.containers.Message
                """
                pongs = [args.message]
                pongs = pongs * args.times

                return ' '.join(pongs)

            return _ping

    def test_bind_command(self):
        ene = EneIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        ene.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', ene.registry._commands)
        self.assertIn('ping', ene.registry._commands['plugintest'])

    def test_get_command(self):
        ene = EneIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        ene.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', ene.registry._commands)
        self.assertIn('ping', ene.registry._commands['plugintest'])

        command = ene.registry.get_command('plugintest', 'ping')
        self.assertIsInstance(command, tuple)

    def test_get_command_bad_plugin(self):
        ene = EneIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        ene.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', ene.registry._commands)
        self.assertIn('ping', ene.registry._commands['plugintest'])

        command = ene.registry.get_command('PLUGINtest', 'ping')
        self.assertIsInstance(command, tuple)
        self.assertRaises(errors.NoSuchPluginError, ene.registry.get_command, 'badplugin', 'ping')

    def test_get_command_bad_command(self):
        ene = EneIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        ene.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        self.assertIn('plugintest', ene.registry._commands)
        self.assertIn('ping', ene.registry._commands['plugintest'])

        command = ene.registry.get_command('plugintest', 'pInG ')
        self.assertIsInstance(command, tuple)
        self.assertRaises(errors.NoSuchCommandError, ene.registry.get_command, 'plugintest', 'badcommand')

    @mock.patch.object(EneIRC, 'msg')
    def test_ping_once(self, mock_msg):
        ene = EneIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        ene.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        dest = containers.Destination(ene, '#test')
        message = containers.Message('>>> plugintest ping 1', dest, containers.Hostmask('Nick!~user@example.org'))
        ene._fire_command('plugintest', 'ping', ['1'], message)

        mock_msg.assert_called_once_with(dest, 'pong')

    @mock.patch.object(EneIRC, 'msg')
    def test_ping_thrice(self, mock_msg):
        ene_irc = EneIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        ene_irc.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        dest = containers.Destination(ene_irc, 'test_nick')
        host = containers.Hostmask('test_nick!~user@example.org')
        message = containers.Message('>>> plugintest ping 3', dest, host)
        ene_irc._fire_command('plugintest', 'ping', ['3'], message)

        mock_msg.assert_called_once_with(host, 'pong pong pong')

    @mock.patch.object(EneIRC, 'msg')
    def test_ping_with_option(self, mock_msg):
        ene = EneIRC(Server(self.hostname, self.config))
        params = {'name': 'ping', 'permission': 'guest'}

        ene.registry.bind_command('ping', self.PluginTest, self.PluginTest.ping, params)

        dest = containers.Destination(ene, 'test_nick')
        host = containers.Hostmask('test_nick!~user@example.org')
        message = containers.Message('>>> plugintest ping 3 --message=wong', dest, host)
        ene._fire_command('plugintest', 'ping', ['3', '--message=wong'], message)

        mock_msg.assert_called_once_with(host, 'wong wong wong')


class LanguageTests(EneIRCTestCase):
    """
    Basic language instantiation tests
    """
    def test_default_instantiation(self):
        ene = EneIRC(Server(self.hostname, self.config))
        self.assertIsInstance(ene.language, LanguageInterface)

    def test_aml_instantiation(self):
        ene = EneIRC(Server(self.hostname, self.config))
        ene._load_language_interface('aml')
        self.assertIsInstance(ene.language, AgentMLLanguage)

    def test_bad_instantiation(self):
        ene = EneIRC(Server(self.hostname, self.config))
        self.assertRaises(ImportError, ene._load_language_interface, '_invalid_language_interface')
