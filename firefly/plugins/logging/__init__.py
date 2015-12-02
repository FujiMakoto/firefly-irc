import os
import errno

import time

from firefly import FireflyIRC, irc, PluginAbstract


# noinspection PyUnresolvedReferences,PyTypeChecker
class Logger(PluginAbstract):

    TYPE_CHANNEL = 'channels'
    TYPE_QUERY   = 'queries'

    def __init__(self, firefly):
        """
        @type   firefly:    FireflyIRC
        """
        PluginAbstract.__init__(self, firefly)

        # Define our logging flags
        self.log_channels   = self.config.getboolean('Logging', 'Log_Channels')
        self.log_queries    = self.config.getboolean('Logging', 'Log_Queries')
        self.log_method     = self.config.get('Logging', 'Log_Method')

        # Ready our paths
        self.basedir        = None
        self.server_path    = None
        self.channel_path   = None
        self.query_path     = None
        self._load_paths()

        # Load our logging templates
        self.timestamp_format = '[%Y-%m-%d %H:%M:%S]'
        self.templates = {
            'channel': {
                'message':  self.config.get('Channel', 'Message'),
                'action':   self.config.get('Channel', 'Action'),
                'notice':   self.config.get('Channel', 'Notice'),
                'join':     self.config.get('Channel', 'Join'),
                'part':     self.config.get('Channel', 'Part'),
                'quit':     self.config.get('Channel', 'Quit'),
                'ignored':  self.config.get('Channel', 'Ignored_Nicks').split(',')
            },
            'query': {
                'message':  self.config.get('Query', 'Message'),
                'action':   self.config.get('Query', 'Action'),
                'notice':   self.config.get('Query', 'Notice'),
                'join':     self.config.get('Query', 'Join'),
                'part':     self.config.get('Query', 'Part'),
                'quit':     self.config.get('Query', 'Quit'),
                'ignored':  self.config.get('Query', 'Ignored_Nicks').split(',')
            }
        }

        self._logs = {
            self.TYPE_CHANNEL: {},
            self.TYPE_QUERY:  {}
        }

    def _load_paths(self):
        """
        Load the configured log paths.
        """
        self._log.debug('Loading paths...')
        self.basedir        = os.path.join(FireflyIRC.CONFIG_DIR, self.config.get('Paths', 'Basedir'))
        self.server_path    = os.path.join(FireflyIRC.CONFIG_DIR, self.config.get('Paths', 'Server'))
        self.channel_path   = os.path.join(FireflyIRC.CONFIG_DIR, self.config.get('Paths', 'Channel'))
        self.query_path     = os.path.join(FireflyIRC.CONFIG_DIR, self.config.get('Paths', 'Query'))

        for path in (self.basedir, self.server_path, self.channel_path, self.query_path):
            # Skip empty paths
            if not path:
                self._log.debug('Skipping unset path')
                continue

            # Try and create the directory. If it already exists and is a dir, continue. If it exists as a file, raise.
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    self._log.error('Failed to make path directory: %s', path)
                    raise

        self._log.debug('Basedir: %s', self.basedir)
        self._log.debug('Servers: %s', self.server_path)
        self._log.debug('Channels: %s', self.channel_path)
        self._log.debug('Queries: %s', self.query_path)

    def _get_timestamp(self):
        """
        Get the current timestamp string
        @rtype: str
        """
        # Make sure timestamps are enabled
        if not self.timestamp_format:
            return ''

        return time.strftime(self.timestamp_format, time.localtime(time.time()))

    @staticmethod
    def sanitize_filename(fn):
        """
        Sanitize characters in a filename
        @type   fn: str
        @rtype: str
        """
        return '_'.join(fn.replace('/', '_').replace('\\', '_').split())

    def _get_path(self, name, log_type):
        """
        Get the filesystem path to the logfile.

        @type   name:   str or None
        @param  name:   The name of the channel or user.

        @type   log_type:   str
        @param  log_type:   Either Logging.TYPE_CHANNEL or Logging.TYPE_QUERY

        @rtype: str

        @raise  ValueError: Raised if an invalid log_type is provided.
        """
        # Make sure we have a valid log type
        if log_type not in [self.TYPE_CHANNEL, self.TYPE_QUERY]:
            raise ValueError('Unrecognized log type: %s', log_type)

        # Get our path
        base_path = self.channel_path if (log_type == self.TYPE_CHANNEL) else self.query_path
        filename  = self.sanitize_filename(name)

        return os.path.join(base_path, '{fn}.log'.format(fn=filename))

    def _open_logfile(self, name, log_type=TYPE_CHANNEL):
        """
        Open a log file.

        @type   name:       str or None
        @param  name:       The name of the channel or user.

        @type   log_type:   str
        @param  log_type:   Either Logging.TYPE_CHANNEL or Logging.TYPE_QUERY
        """
        # Make sure we have a valid name
        if not name:
            self._log.debug('Not logging messages from an unrecognized host')
            return

        # Make sure our logfile isn't already open
        path = self._get_path(name, log_type)
        if name in self._logs[log_type]:
            self._log.warn('Logfile already open for %s (type: %s)', name, log_type)
            return

        self._logs[log_type][name] = open(path, 'a+')
        self._log.info('New logfile opened: %s', path)

    def _close_logfile(self, name, log_type=TYPE_CHANNEL):
        """
        Close an open log file.

        @type   name:   str or None
        @param  name:   The name of the channel or user.

        @type   log_type:   str
        @param  log_type:   Either Logging.TYPE_CHANNEL or Logging.TYPE_QUERY

        @raise  ValueError: Raised if an invalid log_type is provided.
        """
        # Make sure we have a valid log type
        if log_type not in [self.TYPE_CHANNEL, self.TYPE_QUERY]:
            raise ValueError('Unrecognized log type: %s', log_type)

        # Make sure our logfile is actually open
        if name in self._logs[log_type]:
            self._log.warn('No logfile has been opened for %s (type: %s)', name, log_type)
            return

        path = self._logs[log_type][name].name
        self._logs[log_type][name].close()
        del self._logs[log_type][name]

        self._log.info('Logfile closed: %s', path)

    def flush(self, name=None, log_type=None):
        """
        Flush a single logfile (or all log files)

        @type   name:   str or None
        @param  name:   The name of the channel or user. If None, will flush *all* log files under the requested type.

        @type   log_type:   str
        @param  log_type:   Logger.TYPE_CHANNEL or Logger.TYPE_QUERY. If None, and name is None will flush all channel
        and query logfiles. If None and name is *not* none, defaults to Logger.TYPE_CHANNEL

        @raise  ValueError: Raised if an invalid log_type is provided.
        """
        # Make sure we have a valid log type
        if not log_type or log_type not in [self.TYPE_CHANNEL, self.TYPE_QUERY]:
            raise ValueError('Unrecognized log type: %s', log_type)

        if name and not log_type:
            log_type = self.TYPE_CHANNEL

        # Flushing a single logfile?
        if name:
            # Make sure it exists
            if name not in self._logs[log_type]:
                self._log.warn('Unable to flush logfile, log not open')
                return

            # Flush
            self._logs[log_type][name].flush()

            self._log.debug('Flushed log file: %s', self._logs[log_type][name].name)
            return

        # Flush all channels
        if not log_type or (log_type == self.TYPE_CHANNEL):
            for name, log in self._logs[self.TYPE_CHANNEL].iteritems():
                log.flush()
                self._log.debug('Flushed log file: %s', log.name)

        # Flush all queries
        if not log_type or (log_type == self.TYPE_QUERY):
            for name, log in self._logs[self.TYPE_QUERY].iteritems():
                log.flush()
                self._log.debug('Flushed log file: %s', log.name)

    def read(self, name, log_type=TYPE_CHANNEL):
        """
        Open a logfile for reading

        @type   name:   str or None
        @param  name:   The name of the channel or user.

        @type   log_type:   str
        @param  log_type:   Either Logging.TYPE_CHANNEL or Logging.TYPE_QUERY

        @rtype: _io.TextIOWrapper

        @raise  KeyError:   Raised if the requested logfile does not exist or has not been opened yet.
        """
        if name not in self._logs[log_type]:
            self._log.info('No logfile has been opened for %s (type: %s)', name, log_type)
            raise KeyError('No logfile has been opened for {n} (type: {t})'.format(n=name, t=log_type))

        # Flush the logfile before opening it
        self._logs[log_type][name].flush()
        return open(self._logs[log_type][name].name)

    def write(self, message, template):
        """
        Write an entry to the logfile

        @type   message:    firefly.containers.Message
        @param  message:    The message to log.

        @type   template:   str
        @param  template:   The message template.
        """
        # Are we ignoring messages from this user?
        ignored = self.templates['channel']['ignored'] if message.destination.is_channel else \
            self.templates['query']['ignored']

        if message.source.nick in ignored:
            self._log.info('Ignoring message from %s', message.source.nick)
            return

        if message.destination.is_channel:
            log_type = self.TYPE_CHANNEL
            source   = message.destination.raw
        else:
            log_type = self.TYPE_QUERY
            source   = message.source.nick

        if source not in self._logs[log_type]:
            self._log.debug('Logging not enabled for %s (type: %s)', source, log_type)
            return

        log_line = template.format(nick=message.source.nick, hostmask=message.source.hostmask,
                                   message=message.stripped, channel=source)
        line = '{ts} {log}\n'.format(ts=self._get_timestamp(), log=log_line)

        self._logs[log_type][source].write(line)

    @irc.event(irc.on_client_join)
    def start_logging_channel(self, response, channel):
        self._open_logfile(channel.raw)

    @irc.event(irc.on_client_part)
    def stop_logging_channel(self, response, channel):
        self._close_logfile(channel.raw)

    ################################
    # Logging events               #
    ################################

    @irc.event(irc.on_channel_message)
    def channel_message(self, response, message):
        self.write(message, self.templates['channel']['message'])

    @irc.event(irc.on_channel_action)
    def channel_action(self, response, action):
        self.write(action, self.templates['channel']['action'])

    @irc.event(irc.on_channel_notice)
    def channel_notice(self, response, notice):
        self.write(notice, self.templates['channel']['notice'])

    @irc.event(irc.on_channel_join)
    def channel_join(self, response, message):
        self.write(message, self.templates['channel']['join'])

    @irc.event(irc.on_channel_part)
    def channel_part(self, response, message):
        self.write(message, self.templates['channel']['part'])

    @irc.event(irc.on_user_quit)
    def user_quit(self, response, message):
        # Only log quits if we have an open log session for them
        if message.source.nick in self._logs[self.TYPE_QUERY]:
            self.write(message, self.templates['query']['quit'])
            self._close_logfile(message.source.nick, self.TYPE_QUERY)

    @irc.event(irc.on_private_message)
    def private_message(self, response, message):
        if message.source.nick not in self._logs[self.TYPE_QUERY]:
            self._open_logfile(message.source.nick, self.TYPE_QUERY)

        self.write(message, self.templates['query']['message'])

    @irc.event(irc.on_private_action)
    def private_action(self, response, action):
        if action.source.nick not in self._logs[self.TYPE_QUERY]:
            self._open_logfile(action.source.nick, self.TYPE_QUERY)

        self.write(action, self.templates['query']['action'])

    @irc.event(irc.on_private_notice)
    def private_notice(self, response, notice):
        if notice.source.nick not in self._logs[self.TYPE_QUERY]:
            self._open_logfile(notice.source.nick, self.TYPE_QUERY)

        self.write(notice, self.templates['query']['notice'])
