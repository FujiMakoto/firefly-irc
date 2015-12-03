import logging

import arrow
from passlib.hash import bcrypt

from firefly import FireflyIRC
from firefly.errors import AuthError, AuthAlreadyLoggedInError, AuthNoSuchUserError, AuthBadLoginError


class Auth(object):

    def __init__(self, firefly):
        """
        @type   firefly:    firefly.FireflyIRC
        """
        self._log = logging.getLogger('firefly.auth')
        self._users_config = FireflyIRC.load_configuration('users')

        self.firefly = firefly
        self._sessions = {}

    def check(self, hostmask):
        """
        Check and see if the specified hostmask has an active authentication session
        @type   hostmask:   firefly.containers.Hostmask
        @rtype: User or bool
        """
        self._log.info('Checking to see if %s has an active auth session', hostmask.nick)

        # Make sure a session exists first
        if hostmask.host not in self._sessions:
            self._log.info('No auth session for the host %s exists', hostmask.host)
            return False

        # If it does, make sure it's active
        if self._sessions[hostmask.host].active:
            self._log.info('The auth session for %s is active', hostmask.host)
            return self._sessions[hostmask.host].user

        # If it's not active, remove it and return false
        self._log.info('The auth session for %s has expired', hostmask.host)
        del self._sessions[hostmask.host]
        return False

    def attempt(self, hostmask, email, password):
        """
        Attempt to authenticate the specified hostmask.

        @type   hostmask:   firefly.containers.Hostmask
        @param  hostmask:   The hostmask that is authenticating.

        @type   email:      str
        @param  email:      The account e-mail/username.

        @type   password:   str

        @raise  AuthAlreadyLoggedInError:   Raised if the specified hostmask is already logged into an account.
        @raise  AuthNoSuchUserError:        Raised if no account for the specified e-mail exists.
        @raise  AuthBadLoginError:          Raised if the account exists, but the supplied password was invalid.
        @raise  AuthError:                  Raised if a configuration error occurred.
        """
        self._log.info('Attempting to authenticate %s as %s', hostmask.nick, email)

        # Make sure we're not already logged in
        if self.check(hostmask):
            self._log.info('%s is already logged into an account', hostmask.nick)
            raise AuthAlreadyLoggedInError(self._sessions[hostmask.host])

        # Make sure we actually have an account
        if email not in self._users_config.sections():
            self._log.info('No account under the e-mail address %s exists', email)
            raise AuthNoSuchUserError(email)

        # Check our password
        pass_hash = self._users_config.get(email, 'Password')
        try:
            valid_login = bcrypt.verify(password, pass_hash)
        except ValueError:
            self._log.error('User %s has an invalid password hash', email)
            raise AuthError('User {e} has an invalid password hash'.format(e=email))

        if not valid_login:
            self._log.info('Bad password provided for the account %s', email)
            raise AuthBadLoginError(email)

        # If we're still here, we've successfully authenticated and we need to create a new login session
        user = User(email, self._users_config)
        self._sessions[hostmask.host] = AuthSession(user, hostmask, {'hours': +36})

    def logout(self, hostmask):
        """
        Terminate any existing auth sessions for the specified hostmask.

        @type   hostmask:   firefly.containers.Hostmask

        @rtype:     bool
        @return:    False if the user was not logged in, True on successful logout
        """
        # Make sure we're actually logged in
        if hostmask.host not in self._sessions:
            return False

        del self._sessions[hostmask.host]
        return True

    @property
    def sessions(self):
        return self._sessions.copy()


class AuthSession(object):

    def __init__(self, user, hostmask, lifetime, access_refresh=True):
        """
        @type   user:
        @param  user:           The account being authenticated.

        @type   hostmask:       firefly.containers.Hostmask
        @param  hostmask:       The authenticating client.

        @type   lifetime:       dict
        @param  lifetime:       The session lifetime in dict format (e.g. {'days': 3})

        @type   access_refresh: bool
        @param  access_refresh: If true, the session lifetime will be refreshed every time the active state is checked.
        """
        self.user           = user
        self.hostmask       = hostmask
        self.lifetime       = lifetime
        self.expires        = arrow.now().replace(**lifetime) if lifetime else False
        self.access_refresh = access_refresh

    def refresh(self):
        """
        Refresh the sessions lifetime.
        """
        if self.lifetime:
            self.expires = arrow.now().replace(**self.lifetime)

    @property
    def active(self):
        # Is our session never ending?
        if self.expires is False:
            return True

        active = arrow.now() < self.expires

        # Refresh our session if needed
        if active:
            if self.access_refresh:
                self.refresh()

        return active


class User(object):

    def __init__(self, email, config):
        """
        @type   email:      str
        @param  email:      The account e-mail/username.

        @type   config:     ConfigParser.ConfigParser
        @param  config:     Users configuration instance.
        """
        self._log = logging.getLogger('firefly.user')
        self._config = config

        self.email = email
        self.group = config.get(email, 'Group').lower()
        self.nick  = config.get(email, 'Nick')
        self.name  = config.get(email, 'DisplayName')

    @property
    def is_admin(self):
        return self.group == 'admin'
