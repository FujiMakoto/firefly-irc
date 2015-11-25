import unittest

from firefly.languages.aml import AgentML, AgentMLLanguage


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


class AgentMLTests(AgentMLTestCase):
    """
    Basic language instantiation tests
    """
    def test_default_instantiation(self):
        self.assertIsInstance(self.aml.aml, AgentML)
