import unittest
import ene_irc
from ene_irc.languages.aml import AgentMLLanguage


class EneIRCTestCase(unittest.TestCase):
    """
    Base class for all EneIRC test cases
    """
    def setUp(self, **kwargs):
        """
        Set up the Unit Test
        """
        self.ene_irc = ene_irc.EneIRC()

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
