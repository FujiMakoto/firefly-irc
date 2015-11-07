import importlib
import logging
import os
from ConfigParser import ConfigParser
import pkg_resources
import sys
from twisted.internet import reactor, protocol
from twisted.words.protocols.irc import IRCClient
import venusian
from ene_irc import plugins, irc
from ene_irc.containers import ServerInfo
from appdirs import user_config_dir, user_data_dir
from errors import LanguageImportError, PluginCommandExistsError, PluginError

__author__     = "Makoto Fujimoto"
__copyright__  = 'Copyright 2015, Makoto Fujimoto'
__license__    = "MIT"
__version__    = "0.1"
__maintainer__ = "Makoto Fujimoto"


# noinspection PyAbstractClass,PyPep8Naming
class EneIRC(IRCClient):
    """
    Ene IRC client.
    """
    # Default nick
    nickname = "Ene"

    def __init__(self, language='aml', log_level=logging.DEBUG):
        """
        @type   language:   C{str}
        @param  language:   The language engine to use for this instance.

        @type   log_level:  C{int}
        @param  log_level:  logging log level
        """
        # Set up logging
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

        self.registry = _Registry(self)
        self.server_info = ServerInfo()
        self._setup()

        self.plugins = pkg_resources.get_entry_map('ene_irc', 'ene_irc.plugins')
        scanner = venusian.Scanner(ene=self)
        scanner.scan(plugins)

    def _load_language_interface(self, language):
        """
        Load and instantiate the specific language engine.

        @type   language:   C{str}
        """
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
        """
        Run generic setup tasks.
        """
        # Load language files
        lang_dir = os.path.join(self.config_dir, 'language')
        if os.path.isdir(lang_dir):
            self.language.load_directory(lang_dir)

    def _fire_event(self, event_name, **kwargs):
        """
        Fire an IRC event.

        @type   event_name: C{str}
        @param  event_name: Name of the event to fire, see ene_irc.irc for a list of event constants

        @param  kwargs:     Arbitrary event arguments
        """
        self._log.info('Firing event: %s', event_name)
        events = self.registry.get_events(event_name)

        for cls, func, params in events:
            self._log.info('Firing event: %s (%s); Params: %s', str(cls), str(func), str(params))
            func(cls, **kwargs)

    ################################
    # High-level IRC Events        #
    ################################

    def created(self, when):
        """
        Called with creation date information about the server, usually at logon.

        @type   when: C{str}
        @param  when: A string describing when the server was created, probably.
        """
        self._fire_event(irc.on_created, when=when)

    def yourHost(self, info):
        """
        Called with daemon information about the server, usually at logon.

        @param  info: A string describing what software the server is running, probably.
        @type   info: C{str}
        """
        self._fire_event(irc.on_server_host, info=info)

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
        self._fire_event(irc.on_client_info, server_name=server_name, version=version,
                         umodes=umodes, cmodes=cmodes)

    def luserClient(self, info):
        """
        Called with information about the number of connections, usually at logon.

        @type   info: C{str}
        @param  info: A description of the number of clients and servers connected to the network, probably.
        """
        self._fire_event(irc.on_luser_client, info=info)

    def bounce(self, info):
        """
        Called with information about where the client should reconnect.

        @type   info: C{str}
        @param  info: A plaintext description of the address that should be connected to.
        """
        self._fire_event(irc.on_bounce, info=info)

    def isupport(self, options):
        """
        Called with various information about what the server supports.

        @type   options: C{list} of C{str}
        @param  options: Descriptions of features or limits of the server, possibly in the form "NAME=VALUE".
        """
        self.server_info.parse_supports(options)
        self._fire_event(irc.on_server_supports, options=options)

    def luserChannels(self, channels):
        """
        Called with the number of channels existent on the server.

        @type channels: C{int}
        """
        self._fire_event(irc.on_luser_channels, channels=channels)

    def luserOp(self, ops):
        """
        Called with the number of ops logged on to the server.

        @type ops: C{int}
        """
        self._fire_event(irc.on_luser_ops, ops=ops)

    def luserMe(self, info):
        """
        Called with information about the server connected to.

        @type info: C{str}
        @param info: A plaintext string describing the number of users and servers
        connected to this server.
        """
        self._fire_event(irc.on_luser_connection, info=info)

    def privmsg(self, user, channel, message):
        """
        Called when I have a message from a user to me or a channel.
        TODO: Route to custom events
        """
        self._fire_event(irc.on_message, user=user, channel=channel, message=message)

    def joined(self, channel):
        """
        Called when I finish joining a channel.

        channel has the starting character (C{'#'}, C{'&'}, C{'!'}, or C{'+'}) intact.
        """
        self._fire_event(irc.on_client_join, channel=channel)
        self.ping('Makoto')

    def left(self, channel):
        """
        Called when I have left a channel.

        channel has the starting character (C{'#'}, C{'&'}, C{'!'}, or C{'+'}) intact.
        """
        self._fire_event(irc.on_client_part)

    def noticed(self, user, channel, message):
        """
        Called when I have a notice from a user to me or a channel.
        TODO: Route to custom events

        If the client makes any automated replies, it must not do so in response to a NOTICE message, per the RFC::

            The difference between NOTICE and PRIVMSG is that
            automatic replies MUST NEVER be sent in response to a
            NOTICE message. [...] The object of this rule is to avoid
            loops between clients automatically sending something in
            response to something it received.
        """
        self._fire_event(irc.on_notice, user=user, channel=channel, message=message)

    def modeChanged(self, user, channel, set, modes, args):
        """
        Called when users or channel's modes are changed.

        @type   user: C{str}
        @param  user: The user and hostmask which instigated this change.

        @type   channel: C{str}
        @param  channel: The channel where the modes are changed. If args is empty the channel for which the modes
        are changing. If the changes are at server level it could be equal to C{user}.

        @type   set: C{bool} or C{int}
        @param  set: True if the mode(s) is being added, False if it is being removed. If some modes are added and
        others removed at the same time this function will be called twice, the first time with all the added modes,
        the second with the removed ones. (To change this behaviour override the irc_MODE method)

        @type   modes: C{str}
        @param  modes: The mode or modes which are being changed.

        @type   args: C{tuple}
        @param  args: Any additional information required for the mode change.
        """
        self._fire_event(irc.on_mode_changed, user=user, channel=channel, set=set,modes=modes, args=args)

    def pong(self, user, secs):
        """
        Called with the results of a CTCP PING query.

        @type   user: C{str}
        @param  user: The user and hostmask.

        @type   secs: C{float}
        @param  secs: Ping latency
        """
        self._fire_event(irc.on_pong, user=user, secs=secs)

    def signedOn(self):
        """
        Called after successfully signing on to the server.
        """
        self._fire_event(irc.on_client_signed_on)
        self.join('#homestead')

    def kickedFrom(self, channel, kicker, message):
        """
        Called when I am kicked from a channel.

        @type   channel:    C{str}
        @param  channel:    The channel we were kicked from.

        @type   kicker:     C{str}
        @param  kicker:     The user that kicked us.

        @type   message:    C{str}
        @param  message:    The kick message.
        """
        self._fire_event(irc.on_client_kicked, channel=channel, kicker=kicker, message=message)

    def nickChanged(self, nick):
        """
        Called when my nick has been changed.

        @type   nick:   C{str}
        @param  nick:   Our new nick
        """
        self.nickname = nick
        self._fire_event(irc.on_client_nick, nick=nick)

    def userJoined(self, user, channel):
        """
        Called when I see another user joining a channel.

        @type   user:       C{str}
        @param  user:       The user joining the channel.

        @type   channel:    C{str}
        @param  channel:    The channel being joined.
        """
        self._fire_event(irc.on_channel_join, user=user, channel=channel)

    def userLeft(self, user, channel):
        """
        Called when I see another user leaving a channel.

        @type   user:       C{str}
        @param  user:       The user parting the channel.

        @type   channel:    C{str}
        @param  channel:    The channel being parted.
        """
        self._fire_event(irc.on_channel_part, user=user, channel=channel)

    def userQuit(self, user, quitMessage):
        """
        Called when I see another user disconnect from the network.

        @type   user:           C{str}
        @param  user:           The user quitting the network.

        @type   quitMessage:    C{str}
        @param  quitMessage:    The quit message.
        """
        self._fire_event(irc.on_user_quit, user=user, quit_message=quitMessage)

    def userKicked(self, kickee, channel, kicker, message):
        """
        Called when I observe someone else being kicked from a channel.

        @type   kickee:     C{str}
        @param  kickee:     The user being kicked.

        @type   channel:    C{str}
        @param  channel:    The channel the user is being kicked from.

        @type   kicker:     C{str}
        @param  kicker:     The user that is kicking.

        @type   message:    C{str}
        @param  message:    The kick message.
        """
        self._fire_event(irc.on_channel_kick, kickee=kickee, channel=channel, kicker=kicker, message=message)

    def action(self, user, channel, data):
        """
        Called when I see a user perform an ACTION on a channel.
        @TODO: Route to custom events

        @type   user:       C{str}
        @param  user:       The user performing the action.

        @type   channel:    C{str}
        @param  channel:    The user performing the action.

        @type   data:       C{str}
        @param  data:       The action being performed.
        """
        self._fire_event(irc.on_action, user=user, channel=channel, data=data)

    def topicUpdated(self, user, channel, newTopic):
        """
        In channel, user changed the topic to newTopic.
        Also called when first joining a channel.

        @type   user:       C{str} or C{None}
        @param  user:       The user updating the topic, if relevant.

        @type   channel:    C{str}
        @param  channel:    The channel the topic is being changed on.

        @type   newTopic:   C{str}
        @param  newTopic:   The updated topic.
        """
        self._fire_event(irc.on_channel_topic_updated, user=user, channel=channel, new_topic=newTopic)

    def userRenamed(self, oldname, newname):
        """
        A user changed their name from oldname to newname.

        @type   oldname:    C{str}
        @param  oldname:    The users old nick.

        @type   newname:    C{str}
        @param  newname:    The users new nick.
        """
        self._fire_event(irc.on_user_nick_changed, old_nick=oldname, new_nick=newname)

    def receivedMOTD(self, motd):
        """
        I received a message-of-the-day banner from the server.

        motd is a list of strings, where each string was sent as a separate
        message from the server. To display, you might want to use::

            '\\n'.join(motd)

        to get a nicely formatted string.

        @type   motd:   C{list}
        """
        self._fire_event(irc.on_server_motd, motd=motd)

    ################################
    # Low-level IRC Events         #
    ################################

    def irc_ERR_NICKNAMEINUSE(self, prefix, params):
        """
        Called when we try to register or change to a nickname that is already
        taken.
        """
        IRCClient.irc_ERR_NICKNAMEINUSE(self, prefix, params)
        self._fire_event(irc.on_err_nick_in_use, prefix=prefix, params=params)

    def irc_ERR_ERRONEUSNICKNAME(self, prefix, params):
        """
        Called when we try to register or change to an illegal nickname.

        The server should send this reply when the nickname contains any
        disallowed characters.  The bot will stall, waiting for RPL_WELCOME, if
        we don't handle this during sign-on.

        @note: The method uses the spelling I{erroneus}, as it appears in
            the RFC, section 6.1.
        """
        IRCClient.irc_ERR_ERRONEUSNICKNAME(self, prefix, params)
        self._fire_event(irc.on_err_nick_in_use, prefix=prefix, params=params)

    def irc_ERR_PASSWDMISMATCH(self, prefix, params):
        """
        Called when the login was incorrect.
        """
        IRCClient.irc_ERR_PASSWDMISMATCH(self, prefix, params)
        self._fire_event(irc.on_err_bad_password, prefix=prefix, params=params)

    def irc_RPL_WELCOME(self, prefix, params):
        """
        Called when we have received the welcome from the server.
        """
        IRCClient.irc_RPL_WELCOME(self, prefix, params)
        self._fire_event(irc.on_server_welcome, prefix=prefix, params=params)

    def irc_unknown(self, prefix, command, params):
        self._fire_event(irc.on_unknown, prefix=prefix, command=command, params=params)

    def ctcpQuery(self, user, channel, messages):
        """
        Dispatch method for any CTCP queries received.

        Duplicated CTCP queries are ignored and no dispatch is
        made. Unrecognized CTCP queries invoke L{IRCClient.ctcpUnknownQuery}.
        """
        self._fire_event(irc.on_ctcp, user=user, channel=channel, messages=messages)
        IRCClient.ctcpQuery(self, user, channel, messages)

    def ctcpQuery_PING(self, user, channel, data):
        self._fire_event(irc.on_ctcp_ping, user=user, channel=channel, data=data)
        IRCClient.ctcpQuery_PING(self, user, channel, data)

    def ctcpQuery_FINGER(self, user, channel, data):
        self._fire_event(irc.on_ctcp_finger, user=user, channel=channel, data=data)
        IRCClient.ctcpQuery_FINGER(self, user, channel, data)

    def ctcpQuery_VERSION(self, user, channel, data):
        self._fire_event(irc.on_ctcp_version, user=user, channel=channel, data=data)

    def ctcpQuery_SOURCE(self, user, channel, data):
        self._fire_event(irc.on_ctcp_source, user=user, channel=channel, data=data)

    def ctcpQuery_USERINFO(self, user, channel, data):
        self._fire_event(irc.on_ctcp_userinfo, user=user, channel=channel, data=data)
        IRCClient.ctcpQuery_USERINFO(self, user, channel, data)

    def ctcpQuery_TIME(self, user, channel, data):
        self._fire_event(irc.on_ctcp_time, user=user, channel=channel, data=data)
        IRCClient.ctcpQuery_TIME(self, user, channel, data)


class PluginAbstract(object):
    """
    Plugin abstract class.

    This is the class that all third-party plugins should extend.
    """
    __ENE_IRC_PLUGIN_NAME__ = None
    __ENE_IRC_PLUGIN_DEFAULT_PERMISSION__ = 'guest'

    def __init__(self, ene):
        """
        @type   ene:    C{ene_irc.EneIRC}
        """
        self.log = logging.getLogger('ene_irc.plugins.{0}'.format(type(self).__name__.lower()))
        self.ene = ene
        class_path = sys.modules.get(self.__class__.__module__).__file__
        self.plugin_path = os.path.dirname(os.path.realpath(class_path))
        self.config = ConfigParser()
        self._load_configuration()

    def _load_configuration(self):
        config_path = os.path.join(self.plugin_path, 'plugin.cfg')
        self.log.debug('Attempting to load plugin configuration: %s', config_path)

        if os.path.isfile(config_path):
            self.config = ConfigParser()
            self.config.read(config_path)
            self.log.info('Successfully loaded plugin configuration')
            return

        self.log.info('No plugin configuration file could be found')


# noinspection PyMethodMayBeStatic
class _Registry(object):
    """
    Plugin commands / events registry.

    This class is used to contain bindings to plugin classes as well as command and event functions.
    """
    def __init__(self, ene):
        self.ene = ene

        self._commands = {}
        self._events = {}
        self._plugins = {}
        self._log = logging.getLogger('ene_irc.registry')

    def _get_plugin(self, cls):
        """
        Get the plugin name and loaded class object.

        @param  cls:    The plugin class.

        @raise  PluginError:    Raised if the plugin class is not a sub-class of PluginAbstract.
        @rtype: C{tuple of (str, object)}
        """
        # Make sure we have a valid plugin class
        if not issubclass(cls, PluginAbstract):
            raise PluginError('Plugin class must extend ene_irc.PluginAbstract')

        name = cls.__ENE_IRC_PLUGIN_NAME__ or cls.__name__
        obj  = self._plugins[name] if name in self._plugins else cls(self.ene)

        return name, obj

    def bind_command(self, name, cls, func, params):
        """
        Bind a command to the registry.

        @type   name:   C{str}
        @param  name:   Name of the command.

        @param  cls:    The plugin class.

        @param  func:   The command function.

        @type   params: dict
        @param  params: Arbitrary command configuration attributes.

        @raise  PluginCommandExistsError:   Raised if this plugin has already been mapped
        """
        self._log.info('Binding new plugin command %s to %s (%s)', name, str(cls), str(func))

        # Get our plugin data
        plugin_name, plugin_obj = self._get_plugin(cls)

        if plugin_name not in self._commands:
            self._commands[plugin_name] = {}

        # Make sure this plugin has not already been mapped
        if name in self._commands[plugin_name]:
            raise PluginCommandExistsError('%s has already been bound by %s', name,
                                           str(self._commands[plugin_name][name][0]))

        # Map the command
        self._commands[plugin_name][name] = (plugin_obj, func, params)

    def get_command(self, name):
        pass

    def bind_event(self, name, cls, func, params):
        """
        Bind an event to the registry.

        @type   name:   str
        @param  name:   Name of the event.

        @param  cls:    The plugin class.

        @param  func:   The command function.

        @type   params: dict
        @param  params: Arbitrary command configuration attributes.

        @raise  PluginCommandExistsError:   Raised if this plugin has already been mapped.
        """
        self._log.info('Binding new plugin event %s to %s (%s)', name, str(cls), str(func))

        # Get our plugin data
        plugin_name, plugin_obj = self._get_plugin(cls)

        if plugin_name not in self._events:
            self._log.debug('Creating new event entry for plugin: %s', plugin_name)
            self._events[plugin_name] = {}

        if name not in self._events[plugin_name]:
            self._log.debug('Creating new entry for event: %s', name)
            self._events[plugin_name][name] = []

        # Map the command
        self._events[plugin_name][name].append((plugin_obj, func, params))

    def get_events(self, name):
        """
        Get all bound events.

        @type   name:   C{str}
        @param  name:   Name of the event to retrieve bindings for.

        @rtype: C{list}
        """
        self._log.debug('Retrieving events: %s', name)
        all_events = []

        # Iterate our plugins and search for matching events
        for plugin, events in self._events.iteritems():
            self._log.debug('Searching plugin %s...', plugin)

            # Does this plugin have events we want?
            if name not in events:
                self._log.debug('No events found in the %s plugin', plugin)
                continue

            # Append our events and continue
            self._log.debug('%d events matched', len(events[name]))
            all_events += events[name]

        return all_events


class TestFactory(protocol.ClientFactory):
    """
    A factory for generating test connections.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel):
        self.channel = channel

    def buildProtocol(self, addr):
        p = EneIRC()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        raise Exception('Lost connection')

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()
