import inspect
import unittest

from mock import mock

from ene_irc import EneIRC, irc
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
        servers_config = EneIRC.load_configuration('servers')
        servers = []
        hostnames = servers_config.sections()
        for hostname in hostnames:
            servers.append((hostname, servers_config))

        hostname, config = servers.pop()
        self.ene_irc = EneIRC(Server(hostname, config))

    @mock.patch('ene_irc.IRCClient')
    def test_event_bindings(self, mock_class):
        events = [(en, getattr(irc, en)) for en in dir(irc) if en.startswith('on_')]
        ene_methods = dir(self.ene_irc)

        # Make sure all of our event methods exist
        for event_name, meth_name in events:
            self.assertIn(meth_name, ene_methods, 'Missing method {m} for event {e}'.format(m=meth_name, e=event_name))

        # Make sure the correct events are fired
        for event_name, meth_name in events:
            # First we grab our event method and its argument names so we can mock patch it
            method = getattr(self.ene_irc, meth_name)
            margs = inspect.getargspec(method).args
            kwargs = {arg: (self.ARGS[arg] if arg in self.ARGS else None) for arg in margs if arg != 'self'}

            with mock.patch('ene_irc.EneIRC.{m}'.format(m=meth_name), self.ene_irc._fire_event) as mock_method:
                with mock.patch.object(self.ene_irc, '_fire_event') as mock_fire_event:
                    # Fire the event dispatcher and make sure it fires off the correct plugin event in return
                    method(**kwargs)
                    called_events = [c[1][0] for c in mock_fire_event.mock_calls]
                    self.assertIn(meth_name, called_events, 'Event {mn} was not fired'.format(mn=meth_name))


class LanguageTests(EneIRCTestCase):
    """
    Basic language instantiation tests
    """
    def test_default_instantiation(self):
        self.assertIsInstance(self.ene_irc.language, LanguageInterface)

    def test_aml_instantiation(self):
        self.ene_irc._load_language_interface('aml')
        self.assertIsInstance(self.ene_irc.language, AgentMLLanguage)

    def test_bad_instantiation(self):
        self.assertRaises(ImportError, self.ene_irc._load_language_interface, '_invalid_language_interface')
