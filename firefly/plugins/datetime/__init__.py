import arrow

from firefly import irc, PluginAbstract


class DateTime(PluginAbstract):

    @irc.command()
    def date(self, args):
        """
        Returns the current date.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Returns the current date.'
        args.add_argument('--iso', action='store_true', help='Format the date string in ISO-8601 format.')

        def _date(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            msg = arrow.now().format('YYYY-MM-DD') if args.iso else arrow.now().format('MMMM D, YYYY')
            response.add_message(msg)

        return _date

    @irc.command()
    def time(self, args):
        """
        Returns the current time.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Returns the current time.'
        args.add_argument('--iso', action='store_true', help='Format the time string in ISO-8601 format.')

        def _time(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            msg = arrow.now().format('HH:mm:ss ZZ') if args.iso else arrow.now().format('h:mm A ZZ')
            response.add_message(msg)

        return _time

    @irc.command()
    def datetime(self, args):
        """
        Returns the date and time.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Returns the current date and time.'
        args.add_argument('--iso', action='store_true', help='Format the datetime string in ISO-8601 format.')

        def _datetime(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            msg = arrow.now().isoformat() if args.iso else arrow.now().format('MMMM D, YYYY - h:mm A ZZ')
            response.add_message(msg)

        return _datetime

    @irc.command()
    def format(self, args):
        """
        Returns a custom formatted date(/time) string.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Returns a custom formatted date(/time) string. For a list of valid formatting tokens, ' \
                           'see: http://crsmithdev.com/arrow/#tokens'
        args.add_argument('format', help='The datetime string format.')

        def _format(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            msg = arrow.now().format(args.format)
            if msg:
                response.add_message(msg)

        return _format
