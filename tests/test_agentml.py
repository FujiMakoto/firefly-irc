from .config import AgentMLTestCase
from ene_irc.languages.aml import AgentML


class AgentMLTests(AgentMLTestCase):
    """
    Basic language instantiation tests
    """
    def test_default_instantiation(self):
        self.assertIsInstance(self.aml.aml, AgentML)
