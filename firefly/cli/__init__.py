import os
import click
import logging
from firefly import __version__, FireflyIRC

CONTEXT_SETTINGS = dict(auto_envvar_prefix='FIREFLY', max_content_width=100)


class Context(object):
    """
    CLI Context
    """
    def __init__(self):
        self.basedir = os.path.join(os.path.dirname(os.path.realpath(__file__)))


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True, default=1,
              help='-v|vv|vvv Increase the verbosity of messages: 1 for normal output, 2 for more verbose output and '
                   '3 for debug')
@click.version_option(__version__)
@pass_context
def cli(ctx, verbose):
    """
    IPS Vagrant Management Utility
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
