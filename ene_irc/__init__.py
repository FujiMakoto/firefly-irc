import importlib
import logging
import os
from appdirs import user_config_dir, user_data_dir
from errors import LanguageImportError

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
        
        self.commands = []
        self.events = []

        self._setup()

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

    def bind_event(self, name, callback):
        pass

    def call_event(self, name):
        pass
