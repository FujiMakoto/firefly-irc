import ConfigParser
import unittest
import firefly

from firefly import FireflyIRC
from firefly.containers import Server
from firefly.languages.aml import AgentMLLanguage


class EneIRCTestCase(unittest.TestCase):
    """
    Base class for all EneIRC test cases
    """
    def setUp(self, **kwargs):
        """
        Set up the Unit Test
        """
        # Load a test server
        servers_config = FireflyIRC.load_configuration('servers')
        servers = []
        hostnames = servers_config.sections()
        for hostname in hostnames:
            servers.append((hostname, servers_config))

        hostname, config = servers.pop()
        self.ene_irc = firefly.FireflyIRC(Server(hostname, config))

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
