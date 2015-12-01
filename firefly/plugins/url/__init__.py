# coding=utf-8
from .url import UrlParser
from firefly import irc, PluginAbstract


class Url(PluginAbstract):

    def __init__(self, firefly):
        PluginAbstract.__init__(self, firefly)

        self.auto_parse = self.config.getboolean('URL', 'AutoParseUrls')
        self.url_parser = UrlParser()

    @irc.command()
    def title(self, args):
        """
        Returns the title of the specific website.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Returns the title of the specific website.'
        args.add_argument('url', help='The URL to fetch the title from.')

        def _title(args, response):
            """
            @type   response:   firefly.containers.Response
            """
            title = self.url_parser.get_title_from_url(args.url)
            message = title or "Sorry, I couldn't retrieve a valid web page title for the URL you gave me."
            response.add_message(message)

        return _title

    @irc.event(irc.on_channel_message)
    def parse_message(self, response, message):
        """
        @type   response:   firefly.Response
        @type   message:    firefly.containers.Message
        """
        if not self.auto_parse:
            self._log.debug('URL parsing disabled')
            return

        self._log.debug('Parsing message for URLs')
        title = self.url_parser.get_title_from_message(message.stripped)
        if title:
            self._log.info('Title matched: %s', title)
            response.add_message(title)
