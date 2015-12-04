import logging
import re

from agentml import AgentML, errors
from ircmessage import style

from firefly import ArgumentParserError
from firefly.containers import Message, Response
from firefly.languages.interface import LanguageInterface
from .tags import Command


class FireflyAgentML(AgentML):

    def __init__(self, firefly):
        """
        @type   firefly:    firefly.FireflyIRC
        """
        AgentML.__init__(self, logging.getLogger('firefly').level)
        self.firefly = firefly


class AgentMLLanguage(LanguageInterface):

    def __init__(self, firefly):
        """
        @type   firefly:    firefly.FireflyIRC
        """
        self._log = logging.getLogger('firefly.languages.agentml')
        super(AgentMLLanguage, self).__init__()

        self.firefly = firefly
        self.aml = FireflyAgentML(firefly)
        self.command_regex = re.compile(r'<#COMMAND#(?P<return>\d)#(?P<command>.+)#>')

        self.aml.set_tag('command', Command)

    def get_reply(self, message):
        """
        @type   message:    firefly.containers.Message
        @rtype  str or None
        """
        groups = set()

        # Is this a private message?
        if message.destination.is_user:
            groups.add(None)
            groups.add('private')

        # Have we been mentioned in this message?
        nicks = self.firefly.server.identity.nicks
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
                nick = self.firefly.nickname
                raw_message = message.stripped
                match = False
                if message.destination.is_channel:
                    groups.add('public')

        # Get our reply
        reply = None
        try:
            reply = self.aml.get_reply(message.source.host, unicode(raw_message, 'utf-8'), groups)
        except errors.AgentMLError as e:
            self._log.info(e.message)

        if not reply:
            return

        # Replace any command patterns
        def _replace_command(match):
            """
            Method used to replace command patterns with
            @type   match:  _sre.SRE_Match
            @rtype: str
            """
            replace = int(match.group('return'))
            command = match.group('command')

            msg = '{pre}{cmd}'.format(pre=self.firefly.server.command_prefix, cmd=command)
            msg = Message(msg, message.destination, message.source)
            try:
                plugin, command, params = msg.command_parts
            except ValueError:
                self._log.warn('An error occurred when trying to execute a language command: %s', msg.raw)
                return ''

            cmd_replacement = self._fire_command(plugin, command, params, msg)
            if cmd_replacement is False:
                return 'NOPERMISSION'

            if not replace:
                return ''

            return cmd_replacement

        return self.command_regex.sub(_replace_command, reply)

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

        @rtype  list or bool
        """
        self._log.info('Firing language nested command: %s %s (%s)', plugin, name, str(cmd_args))
        cls, func, argparse, params = self.firefly.registry.get_command(plugin, name)

        # Make sure we have permission
        perm = params['permission']
        user = self.firefly.auth.check(message.source)

        if (perm != 'guest') and not user:
            return False

        if (perm == 'admin') and not user.is_admin:
            return False

        # Execute the command
        try:
            response = Response(
                self.firefly, message, message.source, message.destination if message.destination.is_channel else None
            )

            func(argparse.parse_args(cmd_args), response)
            return response.messages[0] if response.messages else ''
        except ArgumentParserError as e:
            self._log.info('Argument parser error: %s', e.message)

            usage    = style(argparse.format_usage().strip(), bold=True)
            desc     = ' -- {desc}'.format(desc=argparse.description.strip()) if argparse.description else ''
            help_msg = '({usage}){desc}'.format(usage=usage, desc=desc)

            # If this command was sent in a query, return the error now
            if message.destination.is_user:
                self.firefly.msg(message.source, e.message)
                self.firefly.msg(message.source, help_msg)
                return

            # Otherwise, check if we should send the messages as a notice or channel message
            if self.firefly.server.public_errors:
                self.firefly.msg(message.destination, e.message)
                self.firefly.msg(message.destination, help_msg)
            else:
                self.firefly.notice(message.source, e.message)
                self.firefly.notice(message.source, help_msg)

    def load_file(self, file_path):
        self._log.debug('Loading file: %s', file_path)
        self.aml.load_file(file_path)

    def load_directory(self, dir_path):
        self._log.debug('Loading directory: %s', dir_path)
        self.aml.load_directory(dir_path)


LANGUAGE_CLASS = AgentMLLanguage
