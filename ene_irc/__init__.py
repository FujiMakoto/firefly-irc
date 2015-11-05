import importlib
import logging
import os
import pkg_resources
from twisted.words.protocols.irc import IRCClient
import venusian
from ene_irc import plugins
from appdirs import user_config_dir, user_data_dir
from errors import LanguageImportError, PluginCommandExistsError, PluginError

__author__     = "Makoto Fujimoto"
__copyright__  = 'Copyright 2015, Makoto Fujimoto'
__license__    = "MIT"
__version__    = "0.1"
__maintainer__ = "Makoto Fujimoto"


class EneIRC(IRCClient):

    def __init__(self, language='aml', log_level=logging.DEBUG):
        self._log = logging.getLogger('ene_irc')
        self._log.setLevel(log_level)
        log_formatter = logging.Formatter("[%(asctime)s] %(levelname)s.%(name)s: %(message)s")
        console_logger = logging.StreamHandler()
        console_logger.setLevel(log_level)
        console_logger.setFormatter(log_formatter)
        self._log.addHandler(console_logger)

        # Ready our paths
        self.config_dir = user_config_dir('Ene', 'Makoto', __version__)
        self.data_dir = user_data_dir('Ene', 'Makoto', __version__)

        self.language = None
        """@type : ene_irc.languages.interface.LanguageInterface"""
        self._load_language_interface(language)

        self.registry = _Registry()
        self._setup()

        self.plugins = pkg_resources.get_entry_map('ene_irc', 'ene_irc.plugins')
        scanner = venusian.Scanner(ene=self)
        scanner.scan(plugins)

    def _load_language_interface(self, language):
        self._log.info('Loading language interface: {lang}'.format(lang=language))
        try:
            module = importlib.import_module('ene_irc.languages.{module}'.format(module=language))
            self.language = module.__LANGUAGE_CLASS__()
        except ImportError as e:
            self._log.error('ImportError raised when loading language')
            raise LanguageImportError('Unable to import language engine "{lang}": {err}'
                                      .format(lang=language, err=e.message))
        except AttributeError:
            self._log.error('Language module does not contain a specified language class, load failed')
            raise LanguageImportError('Language "{lang}" does not have a defined __LANGUAGE_CLASS__'
                                      .format(lang=language))

    def _setup(self):
        # Load language files
        lang_dir = os.path.join(self.config_dir, 'language')
        if os.path.isdir(lang_dir):
            self.language.load_directory(lang_dir)

    def _fire_event(self, event_name, **kwargs):
        pass

    ################################
    # IRC Events                   #
    ################################

    def created(self, when):
        """
        Called with creation date information about the server, usually at logon.

        @type   when: C{str}
        @param  when: A string describing when the server was created, probably.
        """
        self._fire_event('created', when=when)

    def yourHost(self, info):
        """
        Called with daemon information about the server, usually at logon.

        @param  info: A string describing what software the server is running, probably.
        @type   info: C{str}
        """
        self._fire_event('yourHost', info=info)

    def myInfo(self, server_name, version, umodes, cmodes):
        """
        Called with information about the server, usually at logon.

        @type   server_name: C{str}
        @param  server_name: The hostname of this server.

        @type   version: C{str}
        @param  version: A description of what software this server runs.

        @type   umodes: C{str}
        @param  umodes: All the available user modes.

        @type   cmodes: C{str}
        @param  cmodes: All the available channel modes.
        """
        self._fire_event('myInfo', server_name=server_name, version=version,
                         umodes=umodes, cmodes=cmodes)

    def lineReceived(self, line):
        pass

    def dccSend(self, user, file):
        pass

    def rawDataReceived(self, data):
        pass


class PluginAbstract(object):

    __ENE_IRC_PLUGIN_NAME__ = None
    __ENE_IRC_PLUGIN_DEFAULT_PERMISSION__ = 'guest'

    def __init__(self, ene):
        """
        DateTime plugin
        @type ene:  ene_irc.EneIRC
        """
        self.ene = ene


class _Registry(object):

    def __init__(self):
        self._commands = {}
        self._events = {}
        self._log = logging.getLogger('ene_irc.registry')

    # noinspection PyMethodMayBeStatic
    def _get_plugin_name(self, cls):
        """
        Get the plugin name from its class
        @param  cls:    Plugin class
        @raise  PluginError: Raised if the plugin class is not a sub-class of PluginAbstract
        @return: str
        """
        # Make sure we have a valid plugin class
        if not issubclass(cls, PluginAbstract):
            raise PluginError('Plugin class must extend ene_irc.PluginAbstract')

        return cls.__ENE_IRC_PLUGIN_NAME__ or cls.__name__

    def bind_command(self, name, cls, func, params):
        """
        Bind a command to the registry
        @param  name:   Name of the command
        @type   name:   str
        @param  cls:    Plugin class
        @param  func:   Command function
        @param  params: Arbitrary command configuration attributes
        @type   params: dict
        @raise  PluginCommandExistsError: Raised if this plugin has already been mapped
        """
        self._log.info('Binding new plugin command %s to %s (%s)', name, str(cls), str(func))

        # Make sure an entry for our plugin exists
        plugin_name = self._get_plugin_name(cls)

        if plugin_name not in self._commands:
            self._commands[plugin_name] = {}

        # Make sure this plugin has not already been mapped
        if name in self._commands[plugin_name]:
            raise PluginCommandExistsError('%s has already been bound by %s', name,
                                           str(self._commands[plugin_name][name][0]))

        # Map the command
        self._commands[plugin_name][name] = (cls, func, params)

    def get_command(self, name):
        pass

    def bind_event(self, name, cls, func, params):
        """
        Bind a command to the registry
        @param  name:   Name of the event
        @type   name:   str
        @param  cls:    Plugin class
        @param  func:   Command function
        @param  params: Arbitrary command configuration attributes
        @type   params: dict
        @raise  PluginCommandExistsError: Raised if this plugin has already been mapped
        """
        self._log.info('Binding new plugin event %s to %s (%s)', name, str(cls), str(func))

        # Make sure an entry for our plugin exists
        plugin_name = self._get_plugin_name(cls)

        if plugin_name not in self._events:
            self._log.debug('Creating new event entry for plugin: %s', plugin_name)
            self._events[plugin_name] = {}

        if name not in self._events[plugin_name]:
            self._log.debug('Creating new entry for event: %s', name)
            self._events[plugin_name][name] = []

        # Map the command
        self._events[plugin_name][name].append((cls, func, params))

    def get_event(self, name):
        pass
