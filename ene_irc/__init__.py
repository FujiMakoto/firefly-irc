import importlib
import logging
import os
import shutil
import sys
from ConfigParser import ConfigParser

import appdirs
import pkg_resources
import venusian
from ircmessage import style
from twisted.internet import reactor, protocol
from twisted.words.protocols.irc import IRCClient

from ene_irc import plugins, irc
from ene_irc.args import ArgumentParser
from ene_irc.containers import ServerInfo, Destination, Hostmask, Message
from errors import LanguageImportError, PluginCommandExistsError, PluginError, NoSuchPluginError, NoSuchCommandError, \
    ArgumentParserError

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

    # Path constants
    CONFIG_DIR = os.path.join(appdirs.user_config_dir('ene'), 'irc')
    DATA_DIR   = os.path.join(appdirs.user_data_dir('ene'), 'irc')
    LOG_DIR    = os.path.join(appdirs.user_log_dir('ene'), 'irc')

    def __init__(self, server, language='aml'):
        """
        @type   language:   C{str}
        @param  language:   The language engine to use for this instance.
        """
        # Set up logging
        self._log = logging.getLogger('ene_irc')

        self.language = None
        """@type : ene_irc.languages.interface.LanguageInterface"""
        self._load_language_interface(language)

        # Set up our registry and server containers, then run setup
        self.registry = _Registry(self)
        self.server_info = ServerInfo()
        self.server = server
        self._setup()
        self._load_core_language_files()

        # Finally, now that everything is set up, load our plugins
        self.plugins = pkg_resources.get_entry_map('ene_irc', 'ene_irc.plugins')
        scanner = venusian.Scanner(ene=self)
        scanner.scan(plugins)

    @staticmethod
    def load_configuration(name, plugin=None, basedir=None, default=None):
        """
        Load a single configuration file.

        @type   name:       str
        @param  name:       Name of the configuration file *WITHOUT* the .cfg file extension

        @type   plugin:     PluginAbstract or None
        @param  plugin:     Plugin to load a configuration file from, or None to load a system configuration file.

        @type   basedir:    str or None
        @param  basedir:    Optional config path prefix

        @type   default:    str or None
        @param  default:    Name of the default configuration file. Defaults to the name argument.

        @raise  ValueError: Raised if the supplied configuration file does not exist

        @rtype: ConfigParser
        """
        log = logging.getLogger('ene_irc')
        paths = []

        ################################
        # Default Configuration        #
        ################################

        app_path = plugin.plugin_path if plugin else os.path.dirname(os.path.realpath(__file__))
        app_path = os.path.join(app_path, 'config')

        if basedir:
            app_path = os.path.join(app_path, basedir)

        app_path = os.path.join(app_path, '{fn}.cfg'.format(fn=default or name))

        # Make sure the configuration file actually exists
        if not os.path.isfile(app_path):
            raise ValueError('Default configuration file %s does not exist', app_path)

        paths.append(app_path)

        ################################
        # User Configuration           #
        ################################

        user_path = os.path.join(EneIRC.CONFIG_DIR, 'config')
        if plugin:
            user_path = os.path.join(user_path, 'plugins', plugin.name)
        if basedir:
            user_path = os.path.join(user_path, basedir)

        # Make sure the directory exists
        if not os.path.isdir(user_path):
            log.info('Creating user configuration directory: %s', user_path)
            os.makedirs(user_path, 0o755)

        user_path = os.path.join(user_path, '{fn}.cfg'.format(fn=name))
        log.debug('Attempting to load user configuration file: %s', user_path)

        if not os.path.isfile(user_path):
            if default:
                raise ValueError('User configuration file %s does not exist', app_path)  # TODO: Ambiguous exceptions

            log.debug('User configuration file does not exist, attempting to create it')

            # Load the base system path
            shutil.copyfile(app_path, user_path)

        paths.append(user_path)

        # Load the configuration files
        config = ConfigParser()
        log.debug('Attempting to load configuration files: %s', str(paths))
        result = config.read(paths)
        log.debug('Configuration files loaded: %s', str(result))
        return config

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

    def _load_core_language_files(self):
        """
        Load any core language files
        """
        lang_dir = os.path.join(self.CONFIG_DIR, 'lang', self.server.identity.container)
        if not os.path.exists(lang_dir):
            self._log.debug('Creating new language path: %s', lang_dir)
            os.makedirs(lang_dir, 0o755)

        self.language.load_directory(lang_dir)

    def _setup(self):
        """
        Run generic setup tasks.
        """
        # Load language files
        lang_dir = os.path.join(self.CONFIG_DIR, 'language')
        if os.path.isdir(lang_dir):
            self.language.load_directory(lang_dir)

        # Make sure our configuration and data directories exist
        if not os.path.isdir(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR, 0o755)

        if not os.path.isdir(self.DATA_DIR):
            os.makedirs(self.DATA_DIR, 0o755)

    def _fire_event(self, event_name, has_reply=False, is_command=False, **kwargs):
        """
        Fire an IRC event.

        @type   event_name: C{str}
        @param  event_name: Name of the event to fire, see ene_irc.irc for a list of event constants

        @type   has_reply:  bool
        @param  has_reply:  Indicates that this event triggered a language response before firing

        @type   is_command: bool
        @param  is_command: Indicates that this event triggered a command before firing

        @param  kwargs:     Arbitrary event arguments
        """
        self._log.info('Firing event: %s', event_name)
        events = self.registry.get_events(event_name)

        for cls, func, params in events:
            # Commands ok?
            if is_command and not params['command_ok']:
                self._log.info('Event is not responding to command triggers, skipping')
                continue

            # Replies ok?
            if has_reply and not params['reply_ok']:
                self._log.info('Event is not responding to language triggers, skipping')
                continue

            self._log.info('Firing event: %s (%s); Params: %s', str(cls), str(func), str(params))
            func(cls, **kwargs)

    def _fire_command(self, plugin, name, cmd_args, message):
        """
        Fire an IRC command.

        @type   plugin:     str
        @param  plugin:     Name of the command plugin

        @type   name:       str
        @param  name:       Name of the command

        @type   cmd_args:   list of str
        @param  cmd_args:   List of command arguments

        @type   message:    Message
        @param  message:    Command message container
        """
        self._log.info('Firing command: %s %s (%s)', plugin, name, str(cmd_args))
        cls, func, argparse = self.registry.get_command(plugin, name)

        try:
            response = func(argparse.parse_args(cmd_args), message)
            self._log.info('Command response: %s', str(response))

            if isinstance(response, tuple):
                response = '\n'.join(response)
            elif isinstance(response, list):
                response = '\n'.join(response)

            if message.destination.is_user:
                self.msg(message.source, response)
            else:
                self.msg(message.destination, response)
        except ArgumentParserError as e:
            self._log.info('Argument parser error: %s', e.message)

            usage    = style(argparse.format_usage().strip(), bold=True)
            desc     = ' -- {desc}'.format(desc=argparse.description.strip()) if argparse.description else ''
            help_msg = '({usage}){desc}'.format(usage=usage, desc=desc)

            # If this command was sent in a query, return the error now
            if message.destination.is_user:
                self.msg(message.source, e.message)
                self.msg(message.source, help_msg)
                return

            # Otherwise, check if we should send the messages as a notice or channel message
            if self.server.public_errors:
                self.msg(message.destination, e.message)
                self.msg(message.destination, help_msg)
            else:
                self.notice(message.source, e.message)
                self.notice(message.source, help_msg)

    def msg(self, user, message, length=None):
        if isinstance(user, Destination):
            self._log.debug('Implicitly converting Destination to raw format for message delivery: %s --> %s',
                            repr(user), user.raw)
            user = user.raw

        if isinstance(user, Hostmask):
            self._log.debug('Implicitly converting Hostmask to nick format for message delivery: %s --> %s',
                            repr(user), user.nick)
            user = user.nick

        self._log.debug('Delivering message to %s : %s', user, (message[:35] + '..') if len(message) > 35 else message)
        IRCClient.msg(self, user, message, length)
        
    def notice(self, user, message):
        """
        Send a notice to a user.

        Notices are like normal message, but should never get automated
        replies.

        @type   user:   Destination, Hostmask or str
        @param  user:   The user or channel to send a notice to.
        
        @type   message: str
        @param  message: The contents of the notice to send.
        """
        if isinstance(user, Destination):
            self._log.debug('Implicitly converting Destination to raw format for notice delivery: %s --> %s',
                            repr(user), user.raw)
            user = user.raw

        if isinstance(user, Hostmask):
            self._log.debug('Implicitly converting Hostmask to nick format for notice delivery: %s --> %s',
                            repr(user), user.nick)
            user = user.nick

        IRCClient.notice(self, user, message)
        
    def describe(self, channel, action):
        """
        Strike a pose.

        @type   channel:    Destination, Hostmask or str
        @param  channel:    The user or channel to perform an action in.

        @type   action: str
        @param  action: The action to preform.
        """
        if isinstance(channel, Destination):
            self._log.debug('Implicitly converting Destination to raw format for action performance: %s --> %s',
                            repr(channel), channel.raw)
            channel = channel.raw

        if isinstance(channel, Hostmask):
            self._log.debug('Implicitly converting Hostmask to nick format for action performance: %s --> %s',
                            repr(channel), channel.nick)
            channel = channel.nick
        
        IRCClient.describe(self, channel, action)

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
        # TODO: Consider integrating into ServerInfo container

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

        @type   user:       C{str}
        @param  user:       Hostmask of the sender.

        @type   channel:    C{str}
        @param  channel:    Name of the source channel or user nick.

        @type   message:    C{str}
        """
        hostmask    = Hostmask(user)
        destination = Destination(self, channel)
        message     = Message(message, destination, hostmask)
        is_command  = False
        has_reply   = False
        reply_dest  = destination
        groups = set()

        # Is the message a command?
        if message.is_command:
            self._log.debug('Message registered as a command: %s', repr(message))
            is_command = True
            groups.add('command')

            command_plugin, command_name, command_args = message.command_parts
            self._fire_command(command_plugin, command_name, command_args, message)

        # Is this a private message?
        if message.destination.is_user:
            groups.add(None)
            groups.add('private')
            reply_dest = hostmask

        # Have we been mentioned in this message?
        nicks = self.server.identity.nicks
        try:
            nick, raw_message, match = message.get_mentions(nicks)
            groups.add(None)
        except TypeError:
            self._log.debug('Message has no mentions at the beginning')

            try:
                nick, raw_message, match = message.get_mentions(nicks, message.MENTION_END)
                groups.add(None)
            except TypeError:
                self._log.debug('Message has no mentions at the end')
                nick = self.nickname
                raw_message = message.stripped
                match = False
                if message.destination.is_channel:
                    groups.add('public')

        # Do we have a language response?
        reply = self.language.get_reply(raw_message, groups=groups)
        if reply:
            self._log.debug('Reply matched: %s', reply)
            has_reply = True

            self.msg(reply_dest, reply)

        # Fire global event
        self._fire_event(irc.on_message, has_reply, is_command, message=message)

        # Fire custom events
        if message.destination.is_channel:
            self.channelMessage(message, has_reply, is_command)
        elif message.destination.is_user:
            self.privateMessage(message, has_reply, is_command)

    def joined(self, channel):
        """
        Called when I finish joining a channel.

        @type   channel:    C{str}
        @param  channel:    Name of the channel.
        """
        self._fire_event(irc.on_client_join, channel=Destination(self, channel))

    def left(self, channel):
        """
        Called when I have left a channel.

        @type   channel:    C{str}
        @param  channel:    Name of the channel.
        """
        self._fire_event(irc.on_client_part, channel=Destination(self, channel))

    def noticed(self, user, channel, message):
        """
        Called when I have a notice from a user to me or a channel.

        If the client makes any automated replies, it must not do so in response to a NOTICE message, per the RFC::

            The difference between NOTICE and PRIVMSG is that
            automatic replies MUST NEVER be sent in response to a
            NOTICE message. [...] The object of this rule is to avoid
            loops between clients automatically sending something in
            response to something it received.

        @type   user:       C{str}
        @param  user:       Hostmask of the sender.

        @type   channel:    C{str}
        @param  channel:    Name of the source channel or user nick.

        @type   message:    C{str}
        """
        notice = Message(message, Destination(self, channel), Hostmask(user), Message.NOTICE)
        self._fire_event(irc.on_notice, notice=notice)

        # Fire custom events
        if notice.destination.is_channel:
            self.channelNotice(notice)
        elif notice.destination.is_user:
            self.privateNotice(notice)

    def modeChanged(self, user, channel, set, modes, args):
        """
        Called when users or channel's modes are changed.
        TODO

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
        self._fire_event(irc.on_mode_changed, user=Hostmask(user), source=Destination(self, channel), set=set, modes=modes, args=args)

    def pong(self, user, secs):
        """
        Called with the results of a CTCP PING query.

        @type   user: C{str}
        @param  user: The user and hostmask.

        @type   secs: C{float}
        @param  secs: Ping latency
        """
        self._fire_event(irc.on_pong, user=Hostmask(user), secs=secs)

    def signedOn(self):
        """
        Called after successfully signing on to the server.
        """
        # Connect to our autojoin channels
        for channel in self.server.channels:
            if channel.autojoin:
                self.join(channel.name)

        self._fire_event(irc.on_client_signed_on)

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
        self._fire_event(irc.on_channel_join, user=Hostmask(user), channel=channel)

    def userLeft(self, user, channel):
        """
        Called when I see another user leaving a channel.

        @type   user:       C{str}
        @param  user:       The user parting the channel.

        @type   channel:    C{str}
        @param  channel:    The channel being parted.
        """
        self._fire_event(irc.on_channel_part, user=Hostmask(user), channel=channel)

    def userQuit(self, user, quitMessage):
        """
        Called when I see another user disconnect from the network.

        @type   user:           C{str}
        @param  user:           The user quitting the network.

        @type   quitMessage:    C{str}
        @param  quitMessage:    The quit message.
        """
        self._fire_event(irc.on_user_quit, user=Hostmask(user), quit_message=quitMessage)

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

        @type   user:       C{str}
        @param  user:       The user performing the action.

        @type   channel:    C{str}
        @param  channel:    The user or channel.

        @type   data:       C{str}
        @param  data:       The action being performed.
        """
        action = Message(data, Destination(self, channel), Hostmask(user), Message.ACTION)
        self._fire_event(irc.on_action, action=action)

        if action.destination.is_channel:
            self.channelAction(action, False)
        elif action.destination.is_user:
            self.privateAction(action, False)

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
        self._fire_event(irc.on_channel_topic_updated, user=Hostmask(user), channel=channel, new_topic=newTopic)

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
    # Custom IRC Events            #
    ################################

    def channelMessage(self, message, has_reply, is_command):
        """
        Called when I have a message from a user to a channel.

        @type   message:    Message
        @param  message:    The message container object.

        @type   has_reply:  bool
        @param  has_reply:  Indicates that this event triggered a language response before firing

        @type   is_command: bool
        @param  is_command: Indicates that this event triggered a command before firing
        """
        self._fire_event(irc.on_channel_message, has_reply, is_command, message=message)

    def privateMessage(self, message, has_reply, is_command):
        """
        Called when I have a message from a user to me.

        @type   message:    Message
        @param  message:    The message container object.

        @type   has_reply:  bool
        @param  has_reply:  Indicates that this event triggered a language response before firing

        @type   is_command: bool
        @param  is_command: Indicates that this event triggered a command before firing
        """
        self._fire_event(irc.on_private_message, has_reply, is_command, message=message)

    def channelNotice(self, notice):
        """
        Called when I have a notice from a user to a channel.

        @type   notice: Message
        @param  notice: The notice (message) container object.
        """
        self._fire_event(irc.on_channel_notice, notice=notice)

    def privateNotice(self, notice):
        """
        Called when I have a notice from a user to me.

        @type   notice: Message
        @param  notice: The notice (message) container object.
        """
        self._fire_event(irc.on_private_notice, notice=notice)

    def channelAction(self, action, has_reply):
        """
        Called when I see a user perform an ACTION on a channel.

        @type   action: Message
        @param  action: The action (message) container object.

        @type   has_reply:  bool
        @param  has_reply:  Indicates that this event triggered a language response before firing
        """
        self._fire_event(irc.on_channel_action, has_reply, action=action)

    def privateAction(self, action, has_reply):
        """
        Called when I see a user perform an ACTION to me.

        @type   action: Message
        @param  action: The action (message) container object.

        @type   has_reply:  bool
        @param  has_reply:  Indicates that this event triggered a language response before firing
        """
        self._fire_event(irc.on_private_action, has_reply, action=action)

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
        self._log.debug('Unknown IRC event: ({pr} {c} {pa})'.format(pr=str(prefix), c=str(command), pa=str(params)))
        self._fire_event(irc.on_unknown, prefix=prefix, command=command, params=params)

    def ctcpQuery(self, user, channel, messages):
        """
        Dispatch method for any CTCP queries received.

        Duplicated CTCP queries are ignored and no dispatch is
        made. Unrecognized CTCP queries invoke L{IRCClient.ctcpUnknownQuery}.
        """
        self._fire_event(irc.on_ctcp, user=Hostmask(user), channel=channel, messages=messages)
        IRCClient.ctcpQuery(self, user, channel, messages)

    def ctcpQuery_PING(self, user, channel, data):
        self._fire_event(irc.on_ctcp_ping, user=Hostmask(user), channel=channel, data=data)
        IRCClient.ctcpQuery_PING(self, user, channel, data)

    def ctcpQuery_FINGER(self, user, channel, data):
        self._fire_event(irc.on_ctcp_finger, user=Hostmask(user), channel=channel, data=data)
        IRCClient.ctcpQuery_FINGER(self, user, channel, data)

    def ctcpQuery_VERSION(self, user, channel, data):
        self._fire_event(irc.on_ctcp_version, user=Hostmask(user), channel=channel, data=data)

    def ctcpQuery_SOURCE(self, user, channel, data):
        self._fire_event(irc.on_ctcp_source, user=Hostmask(user), channel=channel, data=data)

    def ctcpQuery_USERINFO(self, user, channel, data):
        self._fire_event(irc.on_ctcp_userinfo, user=Hostmask(user), channel=channel, data=data)
        IRCClient.ctcpQuery_USERINFO(self, user, channel, data)

    def ctcpQuery_TIME(self, user, channel, data):
        self._fire_event(irc.on_ctcp_time, user=Hostmask(user), channel=channel, data=data)
        IRCClient.ctcpQuery_TIME(self, user, channel, data)


class PluginAbstract(object):
    """
    Plugin abstract class.

    This is the class that all third-party plugins should extend.
    """
    # This is the name of the plugin. If None, the class name will be used instead.
    ENE_IRC_PLUGIN_NAME = None

    # This is the default permission set required for commands and events.
    ENE_IRC_PLUGIN_DEFAULT_PERMISSION = 'guest'

    # This is a list of configuration files to load into the plugins default configuration object (self.config)
    ENE_IRC_PLUGIN_CONFIG = 'plugin'
    ENE_IRC_PLUGIN_CONFIG_BASEDIR = None
    ENE_IRC_PLUGIN_CONFIG_DEFAULT = None  # Only used when PLUGIN_CONFIG contains a single config file

    # When True, the plugin class will be instantiated on demand instead of immediately on startup.
    ENE_IRC_LAZY_LOAD = False  # TODO: Currently has no effect

    ENE_STRICT = False

    def __init__(self, ene):
        """
        @type   ene:    C{ene_irc.EneIRC}
        """
        self.name = self.ENE_IRC_PLUGIN_NAME or type(self).__name__.lower()
        self._log = logging.getLogger('ene_irc.plugins.{0}'.format(self.name))
        self.ene = ene

        class_path = sys.modules.get(self.__class__.__module__).__file__
        self.plugin_path = os.path.dirname(os.path.realpath(class_path))

        self.config = NotImplemented
        self._load_configuration()

    # noinspection PyUnresolvedReferences
    def _load_configuration(self):
        """
        Load plugin configuration files.

        @raise  ValueError: Re-raised if strict mode is enabled and a configuration file can not be loaded
        """
        if not self.ENE_IRC_PLUGIN_CONFIG:
            self._log.info('Plugin configuration has been explicitly disabled')

        basedir = self.ENE_IRC_PLUGIN_CONFIG_BASEDIR
        default = self.ENE_IRC_PLUGIN_CONFIG_DEFAULT

        # Do we just have a single configuration file?
        if isinstance(self.ENE_IRC_PLUGIN_CONFIG, basestring):
            name = self.ENE_IRC_PLUGIN_CONFIG
            if name.endswith('.cfg'):
                name = name[:-4]

            try:
                self.config = EneIRC.load_configuration(name, self, basedir, default)
            except ValueError:
                err_msg = 'No plugin configuration file found. Please set ENE_IRC_PLUGIN_CONFIG to None if you wish ' \
                          'to explicitly disable configuration files for this plugin'

                # Re-throw exception if strict mode is enabled
                if self.ENE_STRICT:
                    self._log.error(err_msg)
                    raise

                self._log.warn(err_msg)

            self._log.debug('Loaded plugin configuration file %s.cfg', name)
            return

        # Construct a dictionary to store config instances in
        self.config = {}

        for name in self.ENE_IRC_PLUGIN_CONFIG:
            # MAke sure our configuration file has the proper extension
            if name.endswith('.cfg'):
                name = name[:-4]

            try:
                self.config[name] = EneIRC.load_configuration(name, self, basedir)
            except ValueError:
                err_msg = 'Unable to load plugin configuration file {n}.cfg'.format(n=name)

                # Unless strict mode is enabled, just log the error as a warning and continue
                if not self.ENE_STRICT:
                    self._log.warn(err_msg)
                    continue

                self._log.error(err_msg)
                raise

            self._log.debug('Loaded plugin configuration file %s.cfg', name)


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

        name = cls.ENE_IRC_PLUGIN_NAME or cls.__name__
        name = name.lower().strip()
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
        name = name.lower().strip().replace(' ', '_')
        self._log.info('Binding new plugin command %s to %s (%s)', name, str(cls), str(func))

        # Get our plugin data
        plugin_name, plugin_obj = self._get_plugin(cls)

        if plugin_name not in self._commands:
            self._commands[plugin_name] = {}

        # Make sure this plugin has not already been mapped
        if name in self._commands[plugin_name]:
            raise PluginCommandExistsError('%s has already been bound by %s', name,
                                           str(self._commands[plugin_name][name][0]))

        # Set up an ArgumentParser for this command
        ap = ArgumentParser(name)

        # Get our decorated plugin function
        dec_func = func(plugin_obj, ap)

        # Map the command
        self._commands[plugin_name][name] = (plugin_obj, dec_func, ap)

    def get_command(self, plugin, name):
        """
        Get a bound command.

        @type   plugin: str
        @param  plugin: Name of the plugin to retrieve a command from.

        @type   name:   str
        @param  name:   Name of the command to retrieve.

        @rtype: tuple
        @raise  NoSuchPluginError:  Raised if the requested plugin does not exist.
        @raise  NoSuchCommandError: Raised if the requested command does not exist.
        """
        plugin = plugin.lower().strip()
        name = name.lower().strip()

        if plugin not in self._commands:
            self._log.info('Attempted to retrieve a command from a non-existent plugin: %s', plugin)
            print(str(self._commands))
            raise NoSuchPluginError('Requested plugin {p} does not exist'.format(p=plugin))

        if name not in self._commands[plugin]:
            self._log.info('Attempted to retrieve a non-existent command from the %s plugin: %s', plugin, name)
            raise NoSuchCommandError('Requested command {c} does not exist for the {p} plugin'.format(c=name, p=plugin))

        return self._commands[plugin][name]

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

    def __init__(self, server):
        self.ene = EneIRC(server)

    def buildProtocol(self, addr):
        self.ene.factory = self
        return self.ene

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        raise Exception('Lost connection')

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()
