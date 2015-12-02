import re

import arrow
import random
from ircmessage import style
from boltons.jsonutils import reverse_iter_lines

from firefly import PluginAbstract, irc


class Seen(PluginAbstract):

    DEFAULT_PATTERNS = [
        re.compile('^\[(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] <(?P<name>\S+?)> (?P<message>.+)$'),
        re.compile('^\[(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \* (?P<name>\S+?) (?P<message>.+)$')
    ]

    NOT_SEEN_RESPONSES = [
        "Hmm.. I don't think I've ever seen {name}.",
        "I have never seen {name} before.",
        "{name}? Who is that?",
        "{name}? What a funny name! I've never seen them before.",
        "{name}? That name's not familiar to me, sorry!"
    ]

    def __init__(self, firefly):
        """
        @type   firefly:    firefly.FireflyIRC
        """
        super(Seen, self).__init__(firefly)

        self._logger = None
        self.message_patterns = self.DEFAULT_PATTERNS

    def _iterate_logfile(self, name, logfile):
        """
        @type   name:       str
        @param  name:       The name/nick to search for.

        @type   logfile:    _io.TextIOWrapper
        @param  logfile:    The opened logfile

        @rtype: tuple of (str, str, str)
        """
        for line in logfile:
            # Loop through our message patterns and attempt to find a match
            for pattern in self.message_patterns:
                match = pattern.match(line)
                if match:
                    break
            else:
                continue

            # If we have a match, get the attributes from it
            line_datetime = match.group('datetime')
            line_name     = match.group('name')
            line_message  = match.group('message')

            # Does our name match?
            if line_name.lower() == name.lower():
                self._log.info('Match found for {name}'.format(name=name))
                break
            continue
        else:
            return None

        return line_datetime, line_name, line_message

    def _first_logging(self, args, response):
        """
        Get the first message by a user from a log file.
        @type   response:   firefly.containers.Response
        """
        try:
            with self.logger.read(response.channel.raw) as log:
                line = self._iterate_logfile(args.nick, log)
        except KeyError:
            return None

        # Make sure we got a result
        if not line:
            return None

        # Parse the datetime string
        date, name, message = line
        date = arrow.get(date, 'YYYY-MM-DD HH:mm:ss')

        return date, name, message

    # noinspection PyMethodMayBeStatic
    def _first_fallback(self, args, response):
        """
        Get the first message by a user from the server ChannelLogger object.
        @type   response:   firefly.containers.Response
        """
        messages = reversed(response.firefly.server.channels[response.channel.raw].message_log.messages)
        """@type: list of (int, firefly.containers.Message)"""
        for timestamp, message in messages:
            if message.source.nick.lower() == args.nick.lower():
                return arrow.Arrow.fromtimestamp(timestamp), message.source.nick, message.raw

    @irc.command()
    def first(self, args):
        """
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Searches for when the specified nick was first seen in the current channel.'
        args.add_argument('nick', help='The nick to search for.')
        args.add_argument('-r', '--relative', action='store_true', help='Display the date in relative format.')
        args.add_argument('-m', '--message', action='store_true', help='Display the first message the user sent.')

        def _first(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            print self.firefly.registry.plugins
            reply = self._first_logging(args, response) if self.logger else self._first_fallback(args, response)
            if not reply:
                response.add_message(random.choice(self.NOT_SEEN_RESPONSES).format(name=args.nick.title()))
                return

            date, nick, message = reply
            bits = []

            # Get the formatted date string
            date_string = date.humanize() if args.relative else date.format('MMMM DD, YYYY - HH:mm A ZZ')
            bits.append(style(date_string, bold=args.message))

            if args.message:
                bits.append(': <{nick}> {msg}'.format(nick=nick, msg=message))

            response.add_message(''.join(bits))

        return _first

    def _last_logging(self, args, response):
        """
        Get the first message by a user from a log file.
        @type   response:   firefly.containers.Response
        """
        try:
            with self.logger.read(response.channel.raw) as log:
                line = self._iterate_logfile(args.nick, reverse_iter_lines(log))
        except KeyError:
            return None

        # Make sure we got a result
        if not line:
            return None

        # Parse the datetime string
        date, name, message = line
        date = arrow.get(date, 'YYYY-MM-DD HH:mm:ss')

        return date, name, message

    # noinspection PyMethodMayBeStatic
    def _last_fallback(self, args, response):
        """
        Get the first message by a user from the server ChannelLogger object.
        @type   response:   firefly.containers.Response
        """
        messages = response.firefly.server.channels[response.channel.raw].message_log.messages
        """@type: list of (int, firefly.containers.Message)"""
        for timestamp, message in messages:
            if message.source.nick.lower() == args.nick.lower():
                return arrow.Arrow.fromtimestamp(timestamp), message.source.nick, message.raw

    @irc.command()
    def last(self, args):
        """
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Searches for when the specified nick was last seen in the current channel.'
        args.add_argument('nick', help='The nick to search for.')
        args.add_argument('-r', '--relative', action='store_true', help='Display the date in relative format.')
        args.add_argument('-m', '--message', action='store_true', help='Display the last message the user sent.')

        def _last(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            reply = self._last_logging(args, response) if self.logger else self._last_fallback(args, response)
            if not reply:
                response.add_message(random.choice(self.NOT_SEEN_RESPONSES).format(name=args.nick.title()))
                return

            date, nick, message = reply
            bits = []

            # Get the formatted date string
            date_string = date.humanize() if args.relative else date.format('MMMM DD, YYYY - HH:mm A ZZ')
            bits.append(style(date_string, bold=args.message))

            if args.message:
                bits.append(': <{nick}> {msg}'.format(nick=nick, msg=message))

            response.add_message(''.join(bits))

        return _last

    @property
    def logger(self):
        """
        We should use the logging plugin if it's available. If it's not, we will fall back to searching any available
        ChannelLogger containers.
        @rtype: firefly.plugins.logging.Logger or bool
        """
        if self._logger is None:
            self._log.debug('Logger plugin instance found')
            self._logger = self.firefly.registry.plugins['logger'] if 'logger' in self.firefly.registry.plugins \
                else False

        return self._logger
