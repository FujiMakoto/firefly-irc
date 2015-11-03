import unittest
import ene_irc


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
