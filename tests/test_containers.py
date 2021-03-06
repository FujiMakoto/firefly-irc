import os
import unittest
from ConfigParser import ConfigParser

import arrow
import mock
import socket

from firefly import FireflyIRC
from firefly.containers import Server, Channel, ServerInfo, Destination, Hostmask, Message, Identity, Response


class ServerTestCase(unittest.TestCase):

    @mock.patch.object(FireflyIRC, 'load_configuration')
    def setUp(self, mock_load_configuration):
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config')

        self.server_config = ConfigParser()
        self.server_config.read(os.path.join(self.config_path, 'server.cfg'))

        self.channel_config = ConfigParser()
        self.channel_config.read(os.path.join(self.config_path, 'servers', 'irc.example.org.cfg'))

        self.identity_config = ConfigParser()
        self.identity_config.read(os.path.join(self.config_path, 'identities', 'test.cfg'))

        def load_configuration(name, plugin=None, basedir=None, default=None, ext='.cfg'):
            if basedir == 'servers':
                return self.channel_config

            if basedir == 'identities':
                return self.identity_config

        mock_load_configuration.side_effect = load_configuration
        self.server = Server('irc.example.org', self.server_config)

    def test_server_container_attributes(self):
        self.assertIsInstance(self.server._config, ConfigParser)

        self.assertEqual(self.server.hostname, 'irc.example.org')
        self.assertTrue(self.server.enabled)
        self.assertTrue(self.server.auto_connect)
        self.assertEqual(self.server.nick, 'Firefly')
        self.assertEqual(self.server.username, 'Firefly')
        self.assertEqual(self.server.realname, 'Nose Tests')
        self.assertIsNone(self.server.password)
        self.assertEqual(self.server.port, 6669)
        self.assertFalse(self.server.ssl)

    def test_server_channel_containers_length(self):
        self.server.add_channel('#first')
        self.server.add_channel('#second')
        self.server.add_channel('#third')
        self.assertEqual(len(self.server.channels), 3)
        
    def test_first_server_channel_attributes(self):
        self.server.add_channel('#first')
        self.server.add_channel('#second')
        self.server.add_channel('#third')

        first = self.server.channels['#first']
        self.assertIsInstance(first, Channel)
        self.assertIsInstance(first._config, ConfigParser)
        
        self.assertIs(first.server, self.server)
        self.assertEqual(first.name, '#first')
        self.assertTrue(first.autojoin)
        self.assertIsNone(first.password)
        
    def test_second_server_channel_attributes(self):
        self.server.add_channel('#first')
        self.server.add_channel('#second')
        self.server.add_channel('#third')

        second = self.server.channels['#second']
        self.assertIsInstance(second, Channel)
        self.assertIsInstance(second._config, ConfigParser)
        
        self.assertIs(second.server, self.server)
        self.assertEqual(second.name, '#second')
        self.assertTrue(second.autojoin)
        self.assertIsNone(second.password)
        
    def test_third_server_channel_attributes(self):
        self.server.add_channel('#first')
        self.server.add_channel('#second')
        self.server.add_channel('#third')

        third = self.server.channels['#third']
        self.assertIsInstance(third, Channel)
        self.assertIsInstance(third._config, ConfigParser)

        self.assertIs(third.server, self.server)
        self.assertEqual(third.name, '#third')
        self.assertFalse(third.autojoin)
        self.assertEqual(third.password, 'secret')


class IdentityTestCase(unittest.TestCase):

    @mock.patch.object(FireflyIRC, 'load_configuration')
    def setUp(self, mock_load_configuration):
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config')

        self.identity_config = ConfigParser()
        self.identity_config.read(os.path.join(self.config_path, 'identities', 'test.cfg'))

        mock_load_configuration.return_value = self.identity_config
        self.identity = Identity('test', self.identity_config)

    def test_identity_container_attributes(self):
        self.assertIsInstance(self.identity._config, ConfigParser)

        self.assertEqual(self.identity.identity, 'test')
        self.assertEqual(self.identity.container, 'test')
        self.assertEqual(self.identity.name, 'Testing')
        self.assertListEqual(self.identity.aliases, ['tester', 'foo', 'bar', 'ba z'])
        self.assertListEqual(self.identity.nicks, ['Testing', 'tester', 'foo', 'bar', 'ba z'])
        self.assertEqual(self.identity.gender, 'Male')

        self.assertIsInstance(self.identity.epoch, arrow.Arrow)
        self.assertEqual(self.identity.epoch.timestamp, 1443657600)

        now = arrow.now()
        distance = self.identity.epoch.humanize(now, only_distance=True)
        self.assertEqual(self.identity.age, distance)


class ServerInfoTestCase(unittest.TestCase):

    FIRST_RESPONSE  = ['CALLERID', 'CASEMAPPING=rfc1459', 'DEAF=D', 'KICKLEN=180', 'MODES=4', 'PREFIX=(ohv)@%+',
                       'STATUSMSG=@%+', 'EXCEPTS=e', 'INVEX=I', 'NICKLEN=15', 'NETWORK=TestCase', 'MAXLIST=beI:100',
                       'MAXTARGETS=4']

    SECOND_RESPONSE = ['CHANTYPES=#&', 'CHANLIMIT=#:25,&:10', 'CHANNELLEN=50', 'TOPICLEN=300',
                       'CHANMODES=beI,k,l,imnprstORS', 'WATCH=60', 'ELIST=CMNTU', 'SAFELIST', 'AWAYLEN=240', 'KNOCK']

    SUPPORTS = [('CASEMAPPING', 'rfc1459'), ('DEAF', 'D'), ('KICKLEN', '180'), ('MODES', '4'), ('PREFIX', '(ohv)@%+'),
                ('STATUSMSG', '@%+'), ('EXCEPTS', 'e'), ('INVEX', 'I'), ('NICKLEN', '15'), ('NETWORK', 'TestCase'),
                ('MAXLIST', 'beI:100'), ('MAXTARGETS', '4'), ('CHANTYPES', '#&'), ('CHANLIMIT', '#:25,&:10'),
                ('CHANNELLEN', '50'), ('TOPICLEN', '300'), ('CHANMODES', 'beI,k,l,imnprstORS'), ('WATCH', '60'),
                ('ELIST', 'CMNTU'), ('AWAYLEN', '240')]

    CHANMODES = (['b', 'e', 'I'], ['k'], ['l'], ['i', 'm', 'n', 'p', 'r', 's', 't', 'O', 'R', 'S'])

    PREFIX = (('o', '@'), ('h', '%'), ('v', '+'))

    CHANTYPES = ['#', '&']

    CHANLIMIT = [('#', 25), ('&', 10)]

    def setUp(self):
        self.server_info = ServerInfo()

    def test_server_info_container_attributes(self):
        # Support responses are usually split into multiple messages
        self.server_info.parse_supports(self.FIRST_RESPONSE)
        self.server_info.parse_supports(self.SECOND_RESPONSE)

        self.assertEqual(self.server_info.network, 'TestCase')
        self.assertListEqual(self.server_info.supports, self.SUPPORTS)
        self.assertTupleEqual(self.server_info.channel_modes, self.CHANMODES)
        self.assertTupleEqual(self.server_info.prefixes, self.PREFIX)
        self.assertListEqual(self.server_info.channel_types, self.CHANTYPES)
        self.assertListEqual(self.server_info.channel_limits, self.CHANLIMIT)

        self.assertEqual(self.server_info.max_nick_length, 15)
        self.assertEqual(self.server_info.max_channel_length, 50)
        self.assertEqual(self.server_info.max_topic_length, 300)
        self.assertEqual(self.server_info.max_kick_length, 180)
        self.assertEqual(self.server_info.max_away_length, 240)


# noinspection PyTypeChecker
class DestinationTestCase(unittest.TestCase):

    def setUp(self):
        mock_server_info = mock.MagicMock(channel_types=['#', '&'])
        mock_firefly = mock.MagicMock(server_info=mock_server_info)

        self.mock_firefly = mock_firefly

    def test_channel_destination(self):
        destination = Destination(self.mock_firefly, '#test')

        self.assertEqual(destination.type, destination.CHANNEL)
        self.assertTrue(destination.is_channel)
        self.assertFalse(destination.is_user)

        self.assertEqual(destination.raw, '#test')
        self.assertEqual(destination.name, 'test')
        self.assertEqual(str(destination), '#test')

    def test_user_destination(self):
        destination = Destination(self.mock_firefly, '`TestCase')

        self.assertEqual(destination.type, destination.USER)
        self.assertFalse(destination.is_channel)
        self.assertTrue(destination.is_user)

        self.assertEqual(destination.raw, '`TestCase')
        self.assertEqual(destination.name, '`TestCase')
        self.assertEqual(str(destination), '`TestCase')


class HostmaskTestCase(unittest.TestCase):

    # TODO: Add test case for invalid hostmasks when exception handling is implemented

    def test_hostmask_attributes(self):
        hostmask = Hostmask('Nick!~user@example.org')

        self.assertEqual(hostmask.hostmask, 'Nick!~user@example.org')
        self.assertEqual(hostmask.nick, 'Nick')
        self.assertEqual(hostmask.username, '~user')
        self.assertEqual(hostmask.host, 'example.org')

    # This test will fail if the host machine is not connected to a working network
    def test_hostmask_resolution(self):
        hostmask = Hostmask('Nick!~user@example.org')
        self.assertEqual(hostmask.resolve_host(), '93.184.216.34')

        hostmask = Hostmask('Nick!~user@testhost.example')
        self.assertFalse(hostmask.resolve_host())

        hostmask = Hostmask('Nick!~user@testhost.example')
        self.assertRaises(socket.error, hostmask.resolve_host, False)


class MessageTestCase(unittest.TestCase):

    def setUp(self):
        mock_server_info = mock.MagicMock(channel_types=['#', '&'])
        mock_firefly = mock.MagicMock(server_info=mock_server_info)
        self.mock_firefly = mock_firefly

        self.message  = '\x0308,02\x02\x1fHello, world!\x0F'
        self.stripped = 'Hello, world!'
        self.hostmask = Hostmask('Nick!~user@example.org')

    def test_message_attributes(self):
        destination = Destination(self.mock_firefly, '&test-channel')
        message = Message(self.message, destination, self.hostmask)

        self.assertEqual(message.raw, self.message)
        self.assertEqual(message.stripped, self.stripped)
        self.assertIs(message.destination, destination)
        self.assertIs(message.source, self.hostmask)
        self.assertEqual(str(message), message.stripped)

        self.assertEqual(message.type, Message.MESSAGE)
        self.assertTrue(message.is_message)
        self.assertFalse(message.is_notice)
        self.assertFalse(message.is_action)

    def test_notice_attributes(self):
        destination = Destination(self.mock_firefly, 'TestUser')
        message = Message(self.message, destination, self.hostmask, Message.NOTICE)

        self.assertEqual(message.raw, self.message)
        self.assertEqual(message.stripped, self.stripped)
        self.assertIs(message.destination, destination)
        self.assertIs(message.source, self.hostmask)
        self.assertEqual(str(message), message.stripped)

        self.assertEqual(message.type, Message.NOTICE)
        self.assertFalse(message.is_message)
        self.assertTrue(message.is_notice)
        self.assertFalse(message.is_action)

    def test_action_attributes(self):
        destination = Destination(self.mock_firefly, '#testchan')
        message = Message(self.message, destination, self.hostmask, Message.ACTION)

        self.assertEqual(message.raw, self.message)
        self.assertEqual(message.stripped, self.stripped)
        self.assertIs(message.destination, destination)
        self.assertIs(message.source, self.hostmask)
        self.assertEqual(str(message), message.stripped)

        self.assertEqual(message.type, Message.ACTION)
        self.assertFalse(message.is_message)
        self.assertFalse(message.is_notice)
        self.assertTrue(message.is_action)

    def test_get_mentions_start(self):
        test = 'Testcase: hello! This, this is a test.'
        message = Message(test, self.mock_firefly, self.hostmask)

        r = message.get_mentions(['casetest', 'TestCase'])
        self.assertIsNotNone(r)

        self.assertTupleEqual(r, ('Testcase', 'hello! This, this is a test.', r[2]))
        self.assertEqual(r[2].group('separator'), ':')

    def test_get_mentions_end(self):
        test = 'Hello! This, this TestCase is a test, TestCase,'
        message = Message(test, self.mock_firefly, self.hostmask)

        r = message.get_mentions(['casetest', 'TestCase'], message.MENTION_END)
        self.assertIsNotNone(r)

        self.assertTupleEqual(r, ('TestCase', 'Hello! This, this TestCase is a test', r[2]))
        self.assertEqual(r[2].group('ender'), ',')

    def test_get_mentions_anywhere(self):
        test = 'Hello! This, this testCase is a test.'
        message = Message(test, self.mock_firefly, self.hostmask)

        r = message.get_mentions(['casetest', 'TestCase'], message.MENTION_ANYWHERE)
        self.assertIsNotNone(r)

        self.assertTupleEqual(r, ('testCase', 'Hello! This, this testCase is a test.', r[2]))


# noinspection PyTypeChecker
class ResponseTestCase(unittest.TestCase):

    def setUp(self):
        mock_server_info = mock.MagicMock(channel_types=['#', '&'])
        mock_firefly = mock.MagicMock(server_info=mock_server_info)
        self.mock_firefly = mock_firefly

        self.channel_destination = Destination(mock_firefly, '#testchan')
        self.user_destination = Destination(mock_firefly, 'test_nick')
        self.hostmask = Hostmask('Nick!~user@example.org')
        message  = '\x0308,02\x02\x1fHello, world!\x0F'
        self.channel_message = Message(message, self.channel_destination, self.hostmask)
        self.user_message = Message(message, self.user_destination, self.hostmask)

    def test_add_messages(self):
        response = Response(self.mock_firefly, self.channel_message, self.hostmask, self.channel_destination)

        message1 = 'Hello world! Message 1'
        message2 = 'Hello world! Message 2'
        message3 = 'Hello world! Message 3'

        response.add_message(message1)
        response.add_message(message2)
        response.add_message(message3)

        self.assertListEqual(response._messages, [
            ('message', message1, None),
            ('message', message2, None),
            ('message', message3, None)
        ])
        self.assertListEqual(response.messages, [message1, message2, message3])
        self.assertListEqual(response.actions, [])
        self.assertListEqual(response.notices, [])
        
    def test_add_actions(self):
        response = Response(self.mock_firefly, self.channel_message, self.hostmask, self.channel_destination)

        message1 = 'performs an action test 1'
        message2 = 'performs an action test 2'
        message3 = 'performs an action test 3'

        response.add_action(message1)
        response.add_action(message2)
        response.add_action(message3)

        self.assertListEqual(response._messages, [
            ('action', message1, None),
            ('action', message2, None),
            ('action', message3, None)
        ])
        self.assertListEqual(response.messages, [])
        self.assertListEqual(response.actions, [message1, message2, message3])
        self.assertListEqual(response.notices, [])
        
    def test_add_notices(self):
        response = Response(self.mock_firefly, self.channel_message, self.hostmask, self.channel_destination)

        message1 = 'Hello world! Notice 1'
        message2 = 'Hello world! Notice 2'
        message3 = 'Hello world! Notice 3'

        response.add_notice(message1)
        response.add_notice(message2)
        response.add_notice(message3)

        self.assertListEqual(response._messages, [
            ('notice', message1, None),
            ('notice', message2, None),
            ('notice', message3, None)
        ])
        self.assertListEqual(response.messages, [])
        self.assertListEqual(response.actions, [])
        self.assertListEqual(response.notices, [message1, message2, message3])

    def test_send_messages(self):
        response = Response(self.mock_firefly, self.channel_message, self.hostmask, self.channel_destination)

        message1 = 'Hello world! Message 1'
        message2 = 'performs an action test 2'
        message3 = 'Hello world! Notice 3'

        response.add_message(message1)
        response.add_action(message2)
        response.add_notice(message3)

        mock_message = mock.Mock()
        mock_action  = mock.Mock()
        mock_notice  = mock.Mock()

        self.mock_firefly.msg      = mock_message
        self.mock_firefly.describe = mock_action
        self.mock_firefly.notice   = mock_notice

        response.send()

        mock_message.assert_called_once_with(self.channel_destination, message1)
        mock_action.assert_called_once_with(self.channel_destination, message2)
        mock_notice.assert_called_once_with(self.channel_destination, message3)

    def test_delivery_timestamps(self):
        response = Response(self.mock_firefly, self.channel_message, self.hostmask, self.channel_destination)

        message1 = 'Hello world! Message 1'
        message2 = 'performs an action test 2'
        message3 = 'Hello world! Notice 3'

        response.add_message(message1)
        response.add_action(message2)
        response.add_notice(message3)

        mock_message = mock.Mock()
        mock_action  = mock.Mock()
        mock_notice  = mock.Mock()

        self.mock_firefly.msg      = mock_message
        self.mock_firefly.describe = mock_action
        self.mock_firefly.notice   = mock_notice

        response.send()

        self.assertIsInstance(response._delivered[0][2], arrow.Arrow)
        self.assertIsInstance(response._delivered[1][2], arrow.Arrow)
        self.assertIsInstance(response._delivered[2][2], arrow.Arrow)

    def test_delivery_default_channel_destination(self):
        response = Response(self.mock_firefly, self.channel_message, self.hostmask, self.channel_destination)

        message1 = 'Hello world! Message 1'
        message2 = 'performs an action test 2'
        message3 = 'Hello world! Notice 3'

        response.add_message(message1)
        response.add_action(message2)
        response.add_notice(message3)

        mock_message = mock.Mock()
        mock_action  = mock.Mock()
        mock_notice  = mock.Mock()

        self.mock_firefly.msg      = mock_message
        self.mock_firefly.describe = mock_action
        self.mock_firefly.notice   = mock_notice

        self.assertEqual(response._destination, response.DEST_CHANNEL)
        self.assertIs(response.destination, self.channel_destination)

        response.send()

        mock_message.assert_called_once_with(self.channel_destination, message1)
        mock_action.assert_called_once_with(self.channel_destination, message2)
        mock_notice.assert_called_once_with(self.channel_destination, message3)

    def test_delivery_default_user_destination(self):
        response = Response(self.mock_firefly, self.user_message, self.hostmask, self.user_destination)

        message1 = 'Hello world! Message 1'
        message2 = 'performs an action test 2'
        message3 = 'Hello world! Notice 3'

        response.add_message(message1)
        response.add_action(message2)
        response.add_notice(message3)

        mock_message = mock.Mock()
        mock_action  = mock.Mock()
        mock_notice  = mock.Mock()

        self.mock_firefly.msg      = mock_message
        self.mock_firefly.describe = mock_action
        self.mock_firefly.notice   = mock_notice

        self.assertEqual(response._destination, response.DEST_USER)
        self.assertIs(response.destination, self.hostmask)

        response.send()

        mock_message.assert_called_once_with(self.hostmask, message1)
        mock_action.assert_called_once_with(self.hostmask, message2)
        mock_notice.assert_called_once_with(self.hostmask, message3)

    def test_delivery_mixed_destinations(self):
        response = Response(self.mock_firefly, self.channel_message, self.hostmask, self.channel_destination)

        message1 = 'Hello world! Default message 1'
        message2 = 'performs an action channel test 2'
        message3 = 'Hello world! User notice 3'

        response.add_message(message1)
        response.add_action(message2, response.DEST_CHANNEL)
        response.add_notice(message3, response.DEST_USER)

        mock_message = mock.Mock()
        mock_action  = mock.Mock()
        mock_notice  = mock.Mock()

        self.mock_firefly.msg      = mock_message
        self.mock_firefly.describe = mock_action
        self.mock_firefly.notice   = mock_notice

        response.send()

        mock_message.assert_called_once_with(self.channel_destination, message1)
        mock_action.assert_called_once_with(self.channel_destination, message2)
        mock_notice.assert_called_once_with(self.hostmask, message3)
