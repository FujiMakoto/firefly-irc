import argparse

from ircmessage import style
from poogle import google_search
from poogle.errors import PoogleNoResultsError

from firefly import irc, PluginAbstract


class Google(PluginAbstract):

    def __init__(self, firefly):
        PluginAbstract.__init__(self, firefly)

        # Get our configuration attributes
        self.default_results    = self.config.getint('Google', 'Results')
        self.max_results        = self.config.getint('Google', 'MaxResults')
        self.template           = self.config.get('Google', 'Format')
        self.separator          = self.config.get('Google', 'Separator').strip() + ' '

    @irc.command()
    def search(self, args):
        """
        Searches Google for the given query.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Searches Google for the given query.'
        args.add_argument('-r', '--results', type=self.validate_results_range, default=self.default_results,
                          help='The number of results to retrieve')
        args.add_argument('query', help='The search query', nargs='+')

        def _search(args, response):
            """
            @type   args:       argparse.Namespace
            @type   response:   firefly.containers.Response
            """
            try:
                query = ' '.join(args.query)
                results = google_search(query, args.results)
            except PoogleNoResultsError:
                message = "Sorry, I couldn't find anything for {q}".format(q=style(query, bold=True))
                response.add_message(message)
                return

            formatted_results = []
            for result in results:
                formatted_results.append(
                    self.template.format(title=style(result.title, bold=True), url=result.url.as_string())
                )

            response.add_message(
                self.separator.join(formatted_results)
            )

        return _search

    @irc.command()
    def lucky(self, args):
        """
        Searches Google for the given query.
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Searches Google for the given query and returns the top result.'
        args.add_argument('query', help='The search query', nargs='+')

        def _lucky(args, response):
            """
            @type   args:       argparse.Namespace
            @type   response:   firefly.containers.Response
            """
            try:
                query = ' '.join(args.query)
                results = google_search(query, 1)
            except PoogleNoResultsError:
                message = "Sorry, I couldn't find anything for {q}".format(q=style(query, bold=True))
                response.add_message(message)
                return

            response.add_message(results[0].url.as_string())

        return _lucky

    def validate_results_range(self, value):
        """
        Validate a results option.

        @type   value:  int

        @rtype  int
        @raise  argparse.ArgumentTypeError: Raised if the supplied value fails validation
        """
        value = int(value)

        if (value < 1) or (value > self.max_results):
            raise argparse.ArgumentTypeError("Must contain a valid integer between {min} and {max}"
                                             .format(min=1, max=self.max_results))

        return value
