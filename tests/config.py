import ConfigParser
import unittest
import ene_irc

from ene_irc import EneIRC
from ene_irc.containers import Server
from ene_irc.languages.aml import AgentMLLanguage


class EneIRCTestCase(unittest.TestCase):
    """
    Base class for all EneIRC test cases
    """
    def setUp(self, **kwargs):
        """
        Set up the Unit Test
        """
        # Load a test server
        servers_config = EneIRC.load_configuration('servers')
        servers = []
        hostnames = servers_config.sections()
        for hostname in hostnames:
            servers.append((hostname, servers_config))

        hostname, config = servers.pop()
        self.ene_irc = ene_irc.EneIRC(Server(hostname, config))

    def tearDown(self):
        pass


class AgentMLTestCase(unittest.TestCase):
    """
    Base class for all AgentML test cases
    """
    def setUp(self, **kwargs):
        """
        Set up the Unit Test
        """
        self.aml = AgentMLLanguage()

    def tearDown(self):
        pass
