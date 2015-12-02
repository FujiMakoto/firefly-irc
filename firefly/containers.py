import shlex
from collections import deque
from time import time

import arrow
import itertools

import firefly
import logging
import socket
import re
from ircmessage import unstyle


class Server(object):

    def __init__(self, hostname, config):
        """
        @type   hostname:   str
        @param  hostname:   Server hostname

        @type   config:     ConfigParser.ConfigParser
        @param  config:     Server configuration instance
        """
        self._log = logging.getLogger('firefly.server')
        self._log.info('Loading %s server configuration', hostname)
        self._config = config
        self._server_config = None
        self._config_channels = {}

        self.hostname       = hostname
        self.enabled        = config.getboolean(hostname, 'Enabled')
        self.identity       = None
        self.auto_connect   = config.getboolean(hostname, 'Autoconnect')
        self.nick           = config.get(hostname, 'Nick')
        self.username       = config.get(hostname, 'Username')
        self.realname       = config.get(hostname, 'Realname')
        self.password       = config.get(hostname, 'Password') or None
        self.port           = config.getint(hostname, 'Port')
        self.ssl            = config.getboolean(hostname, 'SSL')

        self.command_prefix = self._parse_command_prefix(config.get(hostname, 'CommandPrefix'))
        self.public_errors  = config.getboolean(hostname, 'PublicErrors')

        self._load_server_config()
        self._load_identity()
        self.channels = {}

    def _load_server_config(self):
        """
        Attempt to load the server configuration
        """
        config_filename = re.sub('\s', '_', self.hostname)

        try:
            self._server_config = firefly.FireflyIRC.load_configuration(config_filename, basedir='servers',
                                                                        default='default', ext=None)
        except ValueError:
            self._log.info('%s has no server configuration file present', self.hostname)
            return

        sections = self._server_config.sections()
        for channel in sections:
            chan = Channel(self, channel, self._server_config)
            self._log.info('%s channel configuration loaded', channel)
            self._config_channels[channel] = chan

    def _load_identity(self):
        identity = self._config.get(self.hostname, 'Identity')
        config_filename = identity.lower().strip().replace(' ', '_')

        # Attempt to load the identity configuration
        try:
            config = firefly.FireflyIRC.load_configuration(config_filename, basedir='identities')
        except ValueError:
            self._log.error('Unable to load identity configuration file: %s', config_filename)
            self._log.error('Falling back to default configuration')

            identity = 'Default'
            config = firefly.FireflyIRC.load_configuration('default', basedir='identities')

        self.identity = Identity(identity, config)

    def _parse_command_prefix(self, prefix):
        """
        Make sure we're not trying to stupidly use a word character as the command prefix

        @type   prefix: str

        @rtype: str or bool
        """
        if not re.match('^[^\w\s]+$', prefix):
            self._log.error('Server configuration contains an erroneous command prefix: {p}')
            self._log.error('Commands will be disabled until configuration issues are resolved')
            return False

        return prefix

    def get_or_create_channel(self, name):
        """
        Fetch or create and return a Channel instance.

        @type   name:   str
        @param  name:   Name of the channel to fetch

        @rtype: Channel
        """
        # Does this channel already exist?
        if name in self.channels:
            return self.channels[name]

        # Create a new channel instance and return
        self.add_channel(name)
        return self.channels[name]

    def add_channel(self, name):
        """
        Add a channel to the channels list
        @type   name:   str
        """
        self._log.info('Adding %s to the server channel list', name)

        # Does this exist as an autojoin channel?
        if name in self._config_channels:
            self.channels[name] = self._config_channels[name]
            return

        # Create a new channel instance and return
        self.channels[name] = Channel(self, name)

    def remove_channel(self, name):
        """
        Remove a channel to the channels list
        @type   name:   str
        """
        self._log.info('Removing %s from the server channel list', name)

        if name not in self.channels:
            self._log.warning('%s not in the channels list', name)
            return

        del self.channels[name]

    @property
    def autojoin_channels(self):
        """
        Load autojoin channels from the configuration
        @rtype: dict of (str: Channel)
        """
        if not self._server_config:
            self._log.info('No server configuration to load autojoin channels from')
            return {}

        channels = {}

        for name, channel in self._config_channels.iteritems():
            if not channel.autojoin:
                self._log.info('Skipping non-autojoin channel %s', name)
                continue
            self._log.info('%s registered as an autojoin channel', name)

            channels[name] = channel

        return channels


class Identity(object):

    def __init__(self, identity, config):
        """
        @type   identity:   str
        @param  identity:   Identity name

        @type   config:     ConfigParser.ConfigParser
        @param  config:     Server configuration instance
        """
        self._log = logging.getLogger('firefly.identity')
        self._log.info('Loading %s identity configuration', identity)
        self._config = config

        self.identity   = identity
        self.name       = config.get(identity, 'Name')
        self.container  = config.get(identity, 'Container')

        aliases = config.get(identity, 'Aliases')
        if aliases:
            self.aliases = [alias.lower().strip() for alias in aliases.split(',')]
        else:
            self.aliases = []

        self.epoch  = arrow.get(config.getint(identity, 'Epoch'))
        self.gender = config.get(identity, 'Gender')

    @property
    def age(self):
        return self.epoch.humanize(only_distance=True)

    @property
    def nicks(self):
        return [self.name] + self.aliases

    def __repr__(self):
        return '<FireflyIRC Container: Identity({id}, ConfigParser)>'.format(id=self.identity)

    def __str__(self):
        return self.name


class Channel(object):

    def __init__(self, server, name, config=None):
        """
        @type   server: Server
        @param  server: The server this channel is on.

        @type   name:   str
        @param  name:   Channel name (with prefix)

        @type   config: ConfigParser.ConfigParser or None
        @param  config: Channel configuration instance
        """
        self._log = logging.getLogger('firefly.channel')
        self._log.info('Loading %s channel configuration for %s', name, server.hostname)
        self._config = config

        self.server     = server
        self.name       = name
        self.autojoin   = (config.getboolean(name, 'Autojoin')) if config else None
        self.password   = (config.get(name, 'Password') or None) if config else None

        self.message_log = ChannelLog(self)


class ServerInfo(object):
    """
    Server information container.

    This object is used to store various information about a server, such as supported modes and limits.

    Items are parsed according in accordance to IRC specification,
    U{http://www.irc.org/tech_docs/005.html}
    """
    def __init__(self):
        self._log = logging.getLogger('firefly.server_info')

        # Generic server information
        self.network = None

        # List of raw (unprocessed) server support information in (key, value) tuple format.
        self.supports = []

        # List of channel modes in ([A], [B], [C], [D]) format. For more information, see _parse_chanmodes below.
        self.channel_modes = []

        # List of channel mode prefixes in (mode, prefix) tuple format.
        self.prefixes = []

        # List of supported channel types, e.g. ['#', '&']
        self.channel_types = []

        # Maximum number of channels we can join in (prefix, count) tuple format.
        self.channel_limits = []

        # Maximum lengths.
        self.max_nick_length    = None
        self.max_channel_length = None
        self.max_topic_length   = None
        self.max_kick_length    = None
        self.max_away_length    = None

    def parse_supports(self, supports_list):
        """
        Parse a single "supports" response. We may get multiple of these responses.

        @type   supports_list:  C{list of str}
        """
        for supports in supports_list:
            try:
                key, value = str(supports).split('=', 1)
            except ValueError:
                continue

            self.supports.append((key, value))
            try:
                self._parse_single(key, value)
            except (AttributeError, ValueError, KeyError, IndexError):
                self._log.exception('Exception thrown while parsing supports entry')

    def _parse_single(self, key, value):
        """
        Process a single supports key, value entry.

        @type   key:    C{str}

        @type   value:  C{str}ess

        @return:    True if processed, False if unrecognized
        @rtype:     C{bool}
        """
        if key == 'NETWORK':
            self._parse_network(value)
            return True

        # Modes
        if key == 'CHANMODES':
            self._parse_chanmodes(value)
            return True

        if key == 'PREFIX':
            self._parse_prefix(value)
            return True

        # Types
        if key == 'CHANTYPES':
            self._parse_chantypes(value)
            return True

        # Limits
        if key == 'CHANLIMIT':
            self._parse_chanlimit(value)
            return True

        if key == 'MAXCHANNELS':
            self._parse_chanlimit(value)
            return True

        # Length limits
        if key == 'NICKLEN':
            self._parse_nicklen(value)
            return True

        if key == 'CHANNELLEN':
            self._parse_channellen(value)
            return True

        if key == 'TOPICLEN':
            self._parse_topiclen(value)
            return True

        if key == 'KICKLEN':
            self._parse_kicklen(value)
            return True

        if key == 'AWAYLEN':
            self._parse_awaylen(value)
            return True

        return False

    def _parse_network(self, value):
        """
        NETWORK; name; all
        The IRC network name.

        @type   value:  C{str}
        """
        self.network = value

    def _parse_chanmodes(self, value):
        """
        CHANMODES; A,B,C,D; all
        This is a list of channel modes according to 4 types.
        A = Mode that adds or removes a nick or address to a list. Always has a parameter.
        B = Mode that changes a setting and always has a parameter.
        C = Mode that changes a setting and only has a parameter when set.
        D = Mode that changes a setting and never has a parameter.

        @type   value:  C{str}
        """
        a, b, c, d = value.split(',')

        a = [mode for mode in a]
        b = [mode for mode in b]
        c = [mode for mode in c]
        d = [mode for mode in d]

        self.channel_modes = (a, b, c, d)
        self._log.debug('Channel modes set: %s', str(self.channel_modes))

    def _parse_chantypes(self, value):
        """
        CHANTYPES; chars; all
        The supported channel prefixes.

        @type   value:  C{str}
        """
        self.channel_types = [prefix for prefix in value]
        self._log.debug('Channel types set: %s', str(self.channel_types))

    def _parse_prefix(self, value):
        """
        PREFIX; (modes)prefixes; all
        A list of channel modes a person can get and the respective prefix a channel or nickname will get in case
            the person has it. The order of the modes goes from most powerful to least powerful.
        Those prefixes are shown in the output of the WHOIS, WHO and NAMES command.

        @type   value:  C{str}
        """
        match = re.match('^\((.+)\)(.+)$', value)
        if not match:
            return

        modes, prefixes = match.groups()

        modes       = [mode for mode in modes]
        prefixes    = [prefix for prefix in prefixes]

        self.prefixes = tuple(zip(modes, prefixes))
        self._log.debug('Prefixes set: %s', str(self.prefixes))

    def _parse_chanlimit(self, value):
        """
        CHANLIMIT; pfx:num[,pfx:num,...]; all
        Maximum number of channels allowed to join by channel prefix.

        @type   value:  C{str}
        """
        limits = value.split(',')

        for limit in limits:
            prefixes, limit = limit.split(':')

            for prefix in prefixes:
                self.channel_limits.append((prefix, int(limit)))

        self._log.debug('Channel limits set: %s', str(self.channel_limits))

    def _parse_maxchannels(self, value):
        """
        MAXCHANNELS; number; all
        Maximum number of channels allowed to join.
        This has been replaced by CHANLIMIT.

        @type   value:  C{str}
        """
        self.channel_limits.append((None, int(value)))
        self._log.debug('Channel limits set: %s', str(self.channel_limits))

    def _parse_nicklen(self, value):
        """
        NICKLEN; number; all
        Maximum nickname length.

        @type   value:  C{str}
        """
        self.max_nick_length = int(value)
        self._log.debug('Max nick length set: %d', self.max_nick_length)

    def _parse_channellen(self, value):
        """
        CHANNELLEN; number; all
        Maximum channel name length.

        @type   value:  C{str}
        """
        self.max_channel_length = int(value)
        self._log.debug('Max channel length set: %d', self.max_channel_length)

    def _parse_topiclen(self, value):
        """
        TOPICLEN; number; all
        Maximum topic length.

        @type   value:  C{str}
        """
        self.max_topic_length = int(value)
        self._log.debug('Max topic length set: %d', self.max_topic_length)

    def _parse_kicklen(self, value):
        """
        KICKLEN; number; all
        Maximum kick comment length.

        @type   value:  C{str}
        """
        self.max_kick_length = int(value)
        self._log.debug('Max kick length set: %d', self.max_kick_length)

    def _parse_awaylen(self, value):
        """
        AWAYLEN; number; ircu
        The max length of an away message.

        @type   value:  C{str}
        """
        self.max_away_length = int(value)
        self._log.debug('Max away length set: %s', self.max_away_length)
        
    def __repr__(self):
        return '<FireflyIRC Container: ServerInfo for {s}>'.format(s=self.network)
    
    def __str__(self):
        return self.network


class Destination(object):
    """
    Message source container.
    """
    # Type constants
    CHANNEL = 'channel'
    USER    = 'user'

    def __init__(self, irc, destination):
        """
        @type   irc:            firefly.FireflyIRC

        @type   destination:    C{str}
        """
        self.firefly = irc
        self.raw = destination
        self._log = logging.getLogger('firefly.source')

        # Source type, either channel or user.
        self.type = None

        # Only applicable to channels; contains the prefix used by the channel.
        self.prefix = None

        # The name of the source. Either the users name, or the name of the channel without its prefix.
        self.name = None

        self._parse_destination()

    def _parse_destination(self):
        """
        Parse the destination and determine if it's from a user or a channel.
        """
        chan_types = self.firefly.server_info.channel_types or ['#']

        for chan_type in chan_types:
            if self.raw.startswith(chan_type):
                self.type   = self.CHANNEL
                self.prefix = chan_type

                # Note that we intentionally strip all instances of the prefix here. This means both #foo and ##foo
                # will result in the name "foo" being returned. Please be sure you account for this.
                self.name   = self.raw.lstrip(chan_type)

                self._log.debug('Registering source %s as a channel (Name: %s - Prefix: %s)',
                                self.raw, self.name, self.prefix)
                break
        else:
            self.type = self.USER
            self.name = self.raw

            self._log.debug('Registering source %s as a user', self.raw)

    @property
    def is_channel(self):
        """
        Source is a channel.
        @rtype: C{bool}
        """
        return self.type == self.CHANNEL

    @property
    def is_user(self):
        """
        Source is a user.
        @rtype: C{bool}
        """
        return self.type == self.USER

    def __repr__(self):
        return '<FireflyIRC Container: Destination(firefly, {d})>'.format(d=self.raw)

    def __str__(self):
        return self.raw


class Hostmask(object):
    """
    Client hostmask container.
    """
    def __init__(self, hostmask):
        """
        @type   hostmask:   C{str}
        """
        self._log = logging.getLogger('firefly.client')
        self._regex = re.compile('(?P<nick>[^!]+)!(?P<username>[^@]+)@(?P<host>.+)')

        self.hostmask = hostmask
        self.nick     = None
        self.username = None
        self.host     = None
        self._ip      = None

        self._parse_hostmask()

    def _parse_hostmask(self):
        """
        Parse the components of the hostmask.
        """
        self._log.debug('Attempting to parse hostmask components: %s', self.hostmask)
        match = self._regex.match(self.hostmask)

        # Make sure we have a valid hostmask.
        if not match:
            self._log.info('Unrecognized hostmask format: %s', self.hostmask)
            return

        self.nick, self.username, self.host = match.groups()
        self._log.debug('Hostmask components successfully parsed...')
        self._log.debug('Nick: %s', self.nick)
        self._log.debug('Username: %s', self.username)
        self._log.debug('Host: %s', self.host)

    def resolve_host(self, ignore_errors=True, ignore_cache=False):
        """
        Attempt to resolve the clients hostname.
        Obviously, this won't work if the host is masked.

        @type   ignore_errors:  C{bool}
        @param  ignore_errors:  If True, False will be returned if resolution fails, otherwise expect a socket.error

        @type   ignore_cache:   C{bool}
        @param  ignore_cache:   Force resolution even if a cached result is available

        @raise  socket.error:   Thrown if name resolution fails and ignore_errors is False.

        @rtype: C{str or bool}
        """
        if not self.host:
            self._log.warn('No host set, unable to resolve')

        # Check if we've already resolved this host before
        if self._ip and not ignore_cache:
            self._log.debug('Returning cached host resolution: %s', self._ip)
            return self._ip
        # Check if we've previously failed to resolve this host
        elif self._ip is False and not ignore_cache:
            self._log.debug('Previously failed to resolve this host, returning None')
            return self._ip

        try:
            self._ip = socket.gethostbyname(self.host)
        except socket.error as e:
            self._log.info('Could not resolve host %s (%s)', self.host, e.message)
            self._ip = False

            if not ignore_errors:
                raise

        if self._ip:
            self._log.debug('Host successfully resolved: %s', self._ip)
        else:
            self._log.debug('Unable to resolve host')

        return self._ip

    def __repr__(self):
        return '<FireflyIRC Container: Hostmask("{h}")>'.format(h=self.hostmask)

    def __str__(self):
        return self.hostmask


class Message(object):

    # Message types
    MESSAGE = "message"
    NOTICE  = "notice"
    ACTION  = "action"

    # Mention regexes
    MENTION_START     = r'^(?P<nick>{nicks})(?P<separator>[^\w\s])?\s*(?P<message>.*)'
    MENTION_END       = r'^(?P<message>.+?)(?:(?P<separator>[^\w\s])\s*)*?(?P<nick>{nicks})(?P<ender>[^\w\s])?$'
    MENTION_ANYWHERE  = r'(?P<message>.*\s(?P<nick>{nicks})\W.*)'

    def __init__(self, message, destination, source, message_type=MESSAGE):
        """
        @type   message:        str

        @type   destination:    Destination
        @param  destination:    The message destination

        @type   source:         Hostmask
        @param  source:         The source (user) that sent the message

        @type   message_type:   str
        @param  message_type:   The message type. Either message, notice or action
        """
        self._log        = logging.getLogger('firefly.message')
        self.raw         = message.strip()
        self.stripped    = unstyle(message).strip()
        self.destination = destination
        self.source      = source
        self.type        = message_type

        self._command = []

    def get_mentions(self, nicks, location=MENTION_START):
        """
        Test to see if someone has been mentioned in this message

        @type   nicks:  list or tuple
        @param  nicks:  The nicks to match against

        @type   location:   str
        @param  location:   The location regex to use for matching. Must contain at least a nick and message group.

        @rtype:     tuple of (str, str, re._sre.SRE_Match) or None
        @return:    Tuple of nick, message, match on success, None on failure
        """
        # Format our regex
        nicks = [re.escape(nick) for nick in nicks]
        regex = location.format(nicks='|'.join(nicks))

        # Test for a match
        match = re.match(regex, self.stripped, re.IGNORECASE)
        if not match:
            return None

        # Return the parts
        return match.group('nick'), match.group('message'), match

    @property
    def is_command(self):
        """
        Message is calling a command
        @type: C{bool}
        """
        # Make sure we actually have a command prefix set
        command_prefix = self.destination.firefly.server.command_prefix
        if not command_prefix:
            self._log.debug('Server has no command prefix defined, unable to check for command status')
            return False

        return self.stripped.startswith(command_prefix)

    @property
    def command_parts(self):
        if not self.is_command:
            raise ValueError('Message does not contain a valid command')

        command_prefix = self.destination.firefly.server.command_prefix
        command = self.stripped[len(command_prefix):].strip()
        parts = shlex.split(command)

        if len(parts) < 2:
            raise TypeError('Command strings must contain at least a plugin name and command name')

        # Plugin Name, Command Name, Args
        return parts[0], parts[1], parts[2:]

    @property
    def is_message(self):
        """
        Message type is message.
        @rtype: C{bool}
        """
        return self.type == self.MESSAGE

    @property
    def is_notice(self):
        """
        Message type is notice.
        @rtype: C{bool}
        """
        return self.type == self.NOTICE

    @property
    def is_action(self):
        """
        Message type is action.
        @rtype: C{bool}
        """
        return self.type == self.ACTION

    def __repr__(self):
        return '<FireflyIRC Container: Message("{m}", Destination(firefly, "{d}"), Hostmask("{h}"), "{t}")>'.format(
            m=self.stripped.replace('"', '\\"'),
            d=self.destination.raw,
            h=self.source.hostmask,
            t=self.type
        )

    def __str__(self):
        return self.stripped


class Response(object):

    DEST_CHANNEL = 'channel'
    DEST_USER    = 'user'

    def __init__(self, irc, request, user, channel=None, destination=None):
        """
        @type   irc:            firefly.FireflyIRC

        @type   request:        Message
        @param  request:        The message we are responding to.

        @param  user:           The user that sent the message we're responding to.
        @type   user:           Hostmask

        @param  channel:        The channel (if we're responding to a message sent in a channel)
        @type   channel:        Destination or None

        @param  destination:    The default destination. If we're replying to a query, it's the user, otherwise channel.
        @type   destination:    str or None
        """
        self._log         = logging.getLogger('firefly.response')
        self.firefly      = irc
        self.request      = request
        self.channel      = channel
        self.user         = user
        self._messages    = []
        self._delivered   = []
        self._destination = destination or (
            self.DEST_CHANNEL if self.request and self.request.destination.is_channel else self.DEST_USER
        )
        self.block        = False  # Set to True to stop any further event calls, this should be used with great care.
        self.sent         = False  # Becomes True after all messages in the queue have been delivered.

    def add_message(self, message, destination=None):
        """
        Add a message to the queue

        @type   message:        str

        @type   destination:    str
        @param  destination:    Either user or channel. If None, will use the default specified destination.
        """
        self._log.debug('Adding new response message')
        self._messages.append(('message', message, destination))

    def add_action(self, action, destination=None):
        """
        Add an action to the queue

        @type   action: str

        @type   destination:    str
        @param  destination:    Either user or channel. If None, will use the default specified destination.
        """
        self._log.debug('Adding new response action')
        self._messages.append(('action', action, destination))

    def add_notice(self, notice, destination=None):
        """
        Add a notice to the queue

        @type   notice: str

        @type   destination:    str
        @param  destination:    Either user or channel. If None, will use the default specified destination.
        """
        self._log.debug('Adding new response notice')
        self._messages.append(('notice', notice, destination))

    def send(self):
        """
        Send all queued messages
        """
        self._log.debug('Delivering all queued messages')

        for msg_type, msg, dest in self._messages:
            try:
                if msg_type == 'message':
                    self._log.info('Delivering message')
                    self.firefly.msg(self.get_destination(dest) if dest else self.destination, msg)
                    self._delivered.append((msg_type, msg, arrow.now()))
                    continue

                if msg_type == 'action':
                    self._log.info('Performing action')
                    self.firefly.describe(self.get_destination(dest) if dest else self.destination, msg)
                    self._delivered.append((msg_type, msg, arrow.now()))
                    continue

                if msg_type == 'notice':
                    self._log.info('Delivering notice')
                    self.firefly.notice(self.get_destination(dest) if dest else self.destination, msg)
                    self._delivered.append((msg_type, msg, arrow.now()))
                    continue
            except ValueError:
                self._log.exception('An error occurred while attempting to process a message for delivery')
                continue

            # raise ValueError('Unexpected message type: %s', msg_type)
            self._log.error('Unexpected message type: %s', msg_type)
            continue

        self._log.info('All queued messages delivered')
        self.sent = True
        self.clear()

    def clear(self):
        """
        Clear all message in the queue
        """
        self._log.info('Clearing all queued response messages')
        self._messages = []

    def get_destination(self, dest_type):
        """
        Get the destination of the specified type. To get the default destination, use the destination property instead.

        @param  dest_type:  Either channel or user.
        @type   dest_type:  str

        @rtype:     Destination, Hostmask or None
        @return:    The channel or user. If we're responding to a query and channel is requested, will return None.

        @raise  ValueError: Raised if the supplied destination type is invalid. Use class constants to prevent this.
        """
        if dest_type == self.DEST_CHANNEL:
            return self.channel

        if dest_type == self.DEST_USER:
            return self.user

        raise ValueError('Unrecognized destination type: %s', dest_type)

    @property
    def queue(self):
        return self._messages

    @property
    def messages(self):
        return [msg for msg_type, msg, __ in self._messages if msg_type == 'message']

    @property
    def actions(self):
        return [msg for msg_type, msg, __ in self._messages if msg_type == 'action']

    @property
    def notices(self):
        return [msg for msg_type, msg, __ in self._messages if msg_type == 'notice']

    @property
    def destination(self):
        if self._destination == self.DEST_CHANNEL:
            return self.channel

        if self._destination == self.DEST_USER:
            return self.user

        raise ValueError('Unrecognized destination type: %s', self._destination)

    @destination.setter
    def destination(self, value):
        if value not in (self.DEST_CHANNEL, self.DEST_USER):
            raise ValueError('Unrecognized destination type: %s', value)

        self._destination = value

    def __repr__(self):
        return '<FireflyIRC Container: Response(firefly, Destination(firefly, "{d}"))>'.format(d=self.destination.raw)


class ChannelLog(object):

    def __init__(self, channel, maxlen=100):
        """
        @type   channel:    Channel
        @param  channel:    The channel being logged

        @type   maxlen:     int
        @param  maxlen:     The maximum length of the channel log. Old messages are dropped after this limit is reached.
        """
        self._log       = logging.getLogger('firefly.channel_log')
        self._log.info('Instantiating a new channel logger for %s with a length limit of %d', channel.name, maxlen)

        self.channel    = channel
        self.messages   = deque(maxlen=maxlen)

    def add_message(self, message):
        """
        Add a message to the channel log
        @type   message:    Message
        """
        self._log.info('Logging new %s channel message', self.channel.name)
        self.messages.appendleft((time(), message))

    def get_last(self, messages=1):
        """
        Get the last XX logged messages

        @type   messages:   int

        @return:    Returns a single tuple if messages is 1, otherwise a list of tuples
        @rtype      tuple or list of tuple
        """
        if messages == 1:
            return self.messages[0]

        return list(itertools.islice(self.messages, 0, messages - 1))

    def get_first(self, messages=1):
        """
        Get the first XX logged messages

        @type   messages:   int

        @return:    Returns a single tuple if messages is 1, otherwise a list of tuples
        @rtype      tuple or list of tuple
        """
        if messages == 1:
            return self.messages[len(self.messages) - 1]

        return list(itertools.islice(self.messages, len(self.messages), messages - 1))
