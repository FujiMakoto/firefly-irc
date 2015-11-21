class LanguageImportError(ImportError):
    pass


class NoSuchPluginError(Exception):
    pass


class NoSuchCommandError(Exception):
    pass


###############################
# Argument Parser Errors      #
###############################

class ArgumentParserError(Exception):

    """Exception raised when the ArgumentParser signals an error."""


class ArgumentParserExit(Exception):

    """Exception raised when the argument parser exited.

    Attributes:
        status: The exit status.
    """

    def __init__(self, status, msg):
        self.status = status
        Exception.__init__(msg)


###############################
# Plugin Errors               #
###############################

class PluginError(Exception):
    pass


class PluginCommandExistsError(PluginError):
    """
    Raised when naming conflicts occur between loaded commands
    """
    pass
