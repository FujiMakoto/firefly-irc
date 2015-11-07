import re
import logging


class ServerInfo(object):
    """
    Server information container.

    This object is used to store various information about a server, such as supported modes and limits.

    Items are parsed according in accordance to IRC specification,
    U{http://www.irc.org/tech_docs/005.html}
    """
    def __init__(self):
        self._log = logging.getLogger('ene_irc.server_info')

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

        @type   value:  C{str}

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


class Source(object):
    """
    Message source container.
    """
    # Type constants
    CHANNEL = 'channel'
    USER    = 'user'

    def __init__(self, ene, source):
        """
        @type   ene:    ene_irc.EneIRC
        @type   source: str
        """
        self.ene = ene
        self.source = source
        self._log = logging.getLogger('ene_irc.source')

        # Source type, either channel or user.
        self.type = None

        # Only applicable to channels; contains the prefix used by the channel.
        self.prefix = None

        # The name of the source. Either the users name, or the name of the channel without its prefix.
        self.name = None

        self._parse_source()

    def _parse_source(self):
        """
        Parse the source and determine if it's from a user or a channel
        """
        chan_types = self.ene.server_info.channel_types or ['#']

        for chan_type in chan_types:
            if self.source.startswith(chan_type):
                self.type   = self.CHANNEL
                self.prefix = chan_type

                # Note that we intentionally strip all instances of the prefix here. This means both #foo and ##foo
                # will result in the name "foo" being returned. Please be sure you account for this.
                self.name   = self.source.lstrip(chan_type)

                self._log.debug('Registering source %s as a channel (Name: %s - Prefix: %s)',
                                self.source, self.name, self.prefix)
                break
        else:
            self.type = self.USER
            self.name = self.source

            self._log.debug('Registering source %s as a user', self.source)

    @property
    def is_channel(self):
        """
        Source is a channel
        @rtype: bool
        """
        return self.type == self.CHANNEL

    @property
    def is_user(self):
        """
        Source is a user
        @rtype: bool
        """
        return self.type == self.USER
