import argparse

from ircmessage import style

from firefly import irc, PluginAbstract
from .webster import CollegiateDictionary, WordNotFoundException, InvalidAPIKeyException


class Dictionary(PluginAbstract):
    """
    If you don't know what a dictionary is, look it up in the dictionary
    """
    def __init__(self, firefly):
        """
        @type   firefly:    firefly.FireflyIRC
        """
        super(Dictionary, self).__init__(firefly)
        self.api_key = self.config.get('MerriamWebster', 'APIKey')
        self.max_default = self.config.getint('Dictionary', 'DefaultMaxDefinitions')
        self.max_results = self.config.getint('Dictionary', 'MaxDefinitions')
        self.dictionary = CollegiateDictionary(self.api_key)

    def _get_definitions(self, word, max_definitions=3):
        """
        Fetch definitions for the specified word

        Args:
            word(str): The word to define
            max_definitions(int): The maximum number of definitions to retrieve. Defaults to 3

        Returns:
            list
        """
        self._log.info('Looking up the definition of: ' + word)
        # Attempt to fetch the words definition
        try:
            definitions = []
            for entry in self.dictionary.lookup(word):
                for definition, examples in entry.senses:
                    definitions.append((entry.word, entry.function, definition))
        except WordNotFoundException:
            self._log.info('No definition for {word} found'.format(word=word))
            definitions = []
        except InvalidAPIKeyException:
            self._log.error('Invalid API key defined in Dictionary configuration')
            definitions = []

        return definitions[:max_definitions]

    @irc.command()
    def define(self, args):
        """
        Looks up the definition of a word using the Merriam Webster dictionary
        @type   args:   firefly.args.ArgumentParser
        """
        args.description = 'Looks up the definition of a word using the Merriam Webster dictionary.'
        args.add_argument('word', help='The word to look up.')
        args.add_argument('-r', '--results', type=self.validate_results_range, default=self.max_default,
                          help='The number of results to return.')

        def _define(args, response):
            """
            @type   args:       argparse.Namespace
            @type   response:   firefly.containers.Response
            """
            # Fetch our definitions
            self._log.info('Fetching up to {max} definitions for the word {word}'
                           .format(max=args.results, word=args.word))
            definitions = self._get_definitions(args.word, args.results)

            if not definitions:
                response.add_message(
                    "Sorry, I couldn't find any definitions for {word}.".format(word=style(args.word, bold=True))
                )

            # Format our definitions
            formatted_definitions = []
            for index, definition in enumerate(definitions):
                if not formatted_definitions:
                    formatted_definitions.append("{word} ({pos}) {key} {definition}"
                                                 .format(word=style(args.word, bold=True),
                                                         pos=style(definition[1], italics=True),
                                                         key=style('1:', bold=True), definition=definition[2]))
                else:
                    formatted_definitions.append("{key} {definition}"
                                                 .format(key=style(str(index + 1), bold=True),
                                                         definition=definition[2]))

            self._log.debug('Returning %d definitions', len(formatted_definitions))
            response.add_message(' '.join(formatted_definitions))

        return _define

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
