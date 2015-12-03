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
    """
    Exception raised when the ArgumentParser signals an error.
    """
    pass


class ArgumentParserExit(Exception):
    """
    Exception raised when the argument parser exited.

    Attributes:
        status: The exit status.
    """
    def __init__(self, status, msg):
        self.status = status
        Exception.__init__(msg)


###############################
# Auth Errors                 #
###############################

class AuthError(Exception):
    pass


class AuthAlreadyLoggedInError(AuthError):

    def __init__(self, session):
        """
        @type   session:    firefly.auth.AuthSession
        """
        Exception.__init__(self, 'An auth session already exists for {h} ({n})'
                           .format(h=session.hostmask.host, n=session.hostmask.nick))


class AuthNoSuchUserError(AuthError):

    def __init__(self, email):
        """
        @type   email:  str
        """
        self.email = email
        Exception.__init__(self, 'No account with the e-mail address {e} exists'.format(e=email))


class AuthBadLoginError(AuthError):

    def __init__(self, email):
        self.email = email
        Exception.__init__(self, 'Invalid password supplied for the account %s'.format(e=email))


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
