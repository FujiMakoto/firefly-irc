import click
import os

import signal

from firefly import FireflyIRC
from firefly.cli import pass_context


@click.command('start')
@pass_context
def cli(ctx):
    """
    Stop Firefly
    """
    # Make sure we have a PID file
    pid_file = os.path.join(FireflyIRC.DATA_DIR, 'firefly.pid')
    if not os.path.exists(pid_file):
        raise Exception('No Firefly PID file could be found.')

    # Load our PID number
    with open(pid_file, "r") as f:
        pid = f.read().replace('\n', '')

    os.remove(pid_file)

    # Terminate the process
    os.kill(int(pid), signal.SIGTERM)
