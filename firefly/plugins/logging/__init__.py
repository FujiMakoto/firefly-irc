import os
import errno
from firefly import irc, PluginAbstract


class Logger(PluginAbstract):

    def __init__(self, firefly):
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

    def _load_paths(self):
        self._log.debug('Loading paths...')
        self.basedir    = self.config.get('Paths', 'Basedir')
        self.server     = self.config.get('Paths', 'Server')
        self.channel    = self.config.get('Paths', 'Channel')
        self.query      = self.config.get('Paths', 'Query')

        self.basedir    = os.path.abspath(self.basedir) if self.basedir else None
        self.server     = os.path.abspath(self.server)  if self.server  else None
        self.channel    = os.path.abspath(self.channel) if self.channel else None
        self.query      = os.path.abspath(self.query)   if self.query   else None

        for path in (self.basedir, self.server, self.channel, self.query):
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
        self._log.debug('Servers: %s', self.server)
        self._log.debug('Channels: %s', self.channel)
        self._log.debug('Queries: %s', self.query)

    @irc.event(irc.on_client_signed_on)
    def ping(self):
        print('Ping')
