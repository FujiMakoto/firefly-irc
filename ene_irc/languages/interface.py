from abc import ABCMeta, abstractmethod


class LanguageInterface:

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def get_reply(self, message, client='localhost', groups=None):
        pass

    @abstractmethod
    def load_file(self, file_path):
        pass

    @abstractmethod
    def load_directory(self, dir_path):
        pass

