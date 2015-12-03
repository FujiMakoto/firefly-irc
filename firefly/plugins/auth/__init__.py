from ircmessage import style

from firefly import irc, PluginAbstract
from firefly.auth import Auth
from firefly.errors import AuthAlreadyLoggedInError, AuthError


class AuthPlugin(PluginAbstract):

    FIREFLY_IRC_PLUGIN_NAME = 'Auth'

    def __init__(self, firefly):
        """
        @type   firefly:    firefly.FireflyIRC
        """
        super(AuthPlugin, self).__init__(firefly)
        self.auth = Auth(firefly)

    @irc.command()
    def status(self, args):
        """
        Returns the current authentication status of the host.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Returns your current authentication status.'

        def _status(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            user = self.auth.check(response.request.source)
            if not user:
                response.add_message('You are not logged in.')
                return

            response.add_message('You are currently logged in as {user}.'.format(user=style(user.email, bold=True)))

        return _status

    @irc.command()
    def login(self, args):
        """
        Attempt to authenticate as a user.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Authenticate your current host session.'
        args.add_argument('email')
        args.add_argument('password')

        def _login(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            try:
                self.auth.attempt(response.request.source, args.email, args.password)
            except AuthAlreadyLoggedInError as e:
                response.add_message('You are already logged in to an account.')
                return
            except AuthError:
                response.add_message('Login failed; An invalid email or password was provided.')
                return

            response.add_message('You have successfully logged in as {user}.'.format(user=style(args.email, bold=True)))

        return _login

    @irc.command()
    def logout(self, args):
        """
        Attempt to authenticate as a user.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Terminate any active authentication sessions under your hostmask.'

        def _logout(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            if self.auth.logout(response.request.source):
                response.add_message('You have been logged out successfully.')
            else:
                response.add_message('You are not logged in.')

        return _logout
