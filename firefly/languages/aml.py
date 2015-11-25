import logging
from agentml import AgentML
from .interface import LanguageInterface


class AgentMLLanguage(LanguageInterface):

    def __init__(self):
        self._log = logging.getLogger('firefly.language.aml')
        self.aml = AgentML()
        super(AgentMLLanguage, self).__init__()

    def get_reply(self, message, client='localhost', groups=None):
        return self.aml.get_reply(client, message, groups)

    def load_file(self, file_path):
        self._log.debug('Loading file: %s', file_path)
        self.aml.load_file(file_path)

    def load_directory(self, dir_path):
        self._log.debug('Loading directory: %s', dir_path)
        self.aml.load_directory(dir_path)


__LANGUAGE_CLASS__ = AgentMLLanguage
