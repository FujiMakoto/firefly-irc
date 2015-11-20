import argparse
from ene_irc.errors import ArgumentParserError, ArgumentParserExit


class ArgumentParser(argparse.ArgumentParser):
    """
    Subclass ArgumentParser to be more suitable for runtime parsing.
    """
    def __init__(self, name, *args, **kwargs):
        """
        @type   name:   str
        @param  name:   The command name.
        """
        self.name = name
        argparse.ArgumentParser.__init__(self, *args, add_help=False, prog=name, **kwargs)

    def exit(self, status=0, msg=None):
        raise ArgumentParserExit(status, msg)

    def error(self, msg):
        raise ArgumentParserError(msg.capitalize())
