import os
import click
import logging
from firefly import __version__, FireflyIRC

CONTEXT_SETTINGS = dict(auto_envvar_prefix='FIREFLY-CONFIG', max_content_width=100)


class Context(object):
    """
    CLI Context
    """
    def __init__(self):
        self.log = logging.getLogger('firefly.cli-config')
        self.servers = []


pass_context  = click.make_pass_decorator(Context, ensure=True)
plugin_folder = os.path.dirname(__file__)


class FireflyConfigCLI(click.MultiCommand):

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(plugin_folder):
            if filename.endswith('.py') and not filename.startswith('_'):
                rv.append(filename[:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        ns = {}
        fn = os.path.join(plugin_folder, name + '.py')
        with open(fn) as f:
            code = compile(f.read(), fn, 'exec')
            eval(code, ns, ns)
        return ns['cli']


@click.command(cls=FireflyConfigCLI, context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True, default=1,
              help='-v|vv|vvv Increase the verbosity of messages: 1 for normal output, 2 for more verbose output and '
                   '3 for debug')
@click.version_option(__version__)
@pass_context
def cli(ctx, verbose):
    """
    Firefly IRC configuration management utility
    """
    assert isinstance(ctx, Context)

    # Set up the logger
    verbose = verbose if (verbose <= 3) else 3
    log_levels = {1: logging.WARN, 2: logging.INFO, 3: logging.DEBUG}
    log_level = log_levels[verbose]

    ctx.log = logging.getLogger('firefly')
    ctx.log.setLevel(log_level)

    # Console logger
    console_format = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(console_format)
    ctx.log.addHandler(ch)

    # File logger
    if not os.path.exists(FireflyIRC.LOG_DIR):
        os.makedirs(FireflyIRC.LOG_DIR)

    file_format = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    file_logger = logging.FileHandler(os.path.join(FireflyIRC.LOG_DIR, 'firefly.log'))
    file_logger.setLevel(log_level)
    file_logger.setFormatter(file_format)
    ctx.log.addHandler(file_logger)
