from .config import EneIRCTestCase
from ene_irc.languages.interface import LanguageInterface
from ene_irc.languages.aml import AgentMLLanguage


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
