from ircmessage import style
from firefly import irc, PluginAbstract


class Test(PluginAbstract):

    @irc.command()
    def poke(self, args):
        """
        *poke*
        @type   args:   firefly.args.ArgumentParser
        """
        args.add_argument('times', type=int, help='How many times to poke')
        args.add_argument('--color', help='The color to use for the poke message')

        def _poke(args, response):
            """
            @type   args:       argparse.Namespace
            @type   response:    firefly.containers.Response
            """
            if args.times:
                for c in range(0, args.times):
                    response.add_message(style('poke', args.color))

            return response

        return _poke
