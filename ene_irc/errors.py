class LanguageImportError(ImportError):
    pass


###############################
# Plugin Errors               #
###############################

class PluginError(Exception):
    pass


class PluginCommandExistsError(PluginError):
    """
    Raised when naming conflicts occur between loaded commands
    """
    pass
