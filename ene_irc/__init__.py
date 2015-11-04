import importlib
import logging
import os
import pkg_resources
import venusian
from ene_irc import plugins
from appdirs import user_config_dir, user_data_dir
from errors import LanguageImportError, PluginCommandExistsError, PluginError

__author__     = "Makoto Fujimoto"
__copyright__  = 'Copyright 2015, Makoto Fujimoto'
__license__    = "MIT"
__version__    = "0.1"
__maintainer__ = "Makoto Fujimoto"


class EneIRC:

    def __init__(self, language='aml'):
        self.log = logging.getLogger('ene-irc')

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
        self.log.info('Loading language interface: {lang}'.format(lang=language))
        try:
            module = importlib.import_module('ene_irc.languages.{module}'.format(module=language))
            self.language = module.__LANGUAGE_CLASS__()
        except ImportError as e:
            self.log.error('ImportError raised when loading language')
            raise LanguageImportError('Unable to import language engine "{lang}": {err}'
                                      .format(lang=language, err=e.message))
        except AttributeError:
            self.log.error('Language module does not contain a specified language class, load failed')
            raise LanguageImportError('Language "{lang}" does not have a defined __LANGUAGE_CLASS__'
                                      .format(lang=language))

    def _setup(self):
        # Load language files
        lang_dir = os.path.join(self.config_dir, 'language')
        if os.path.isdir(lang_dir):
            self.language.load_directory(lang_dir)


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
        self._log.info('Binding new plugin command: %s', name)

        # Make sure we have a valid plugin class
        if not issubclass(cls, PluginAbstract):
            raise PluginError('Plugin class must extend ene_irc.PluginAbstract')

        # Make sure an entry for our plugin exists
        plugin_name = cls.__ENE_IRC_PLUGIN_NAME__ or cls.__name__

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
        pass

    def get_event(self, name):
        pass
