import re

import click
import os

from firefly import FireflyIRC
from firefly.cli.config import pass_context, Context


@click.command('delete')
@click.argument('host')
@click.option('--no-prompt', help='Skip the safety deletion prompt.', is_flag=True)
@pass_context
def cli(ctx, host, no_prompt):
    """
    Deletes an existing server from the configuration
    """
    assert isinstance(ctx, Context)

    # Make sure this host actually exists in our configuration
    servers_config = FireflyIRC.load_configuration('servers')
    server_cfg_path = os.path.join(FireflyIRC.CONFIG_DIR, 'config', 'servers.cfg')
    if host not in servers_config.sections():
        ctx.log.error('No configuration for %s exists', host)
        raise click.ClickException('No configuration for {h} exists'.format(h=host))

    # Confirm
    if not no_prompt:
        click.confirm('You are about to delete the IRC configuration files for {hn}\nAre you sure you want to do this?'
                      .format(hn=host), abort=True)

    # Remove the host from servers.cfg
    servers_config.remove_section(host)
    with open(server_cfg_path, 'w') as cf:
        servers_config.write(cf)

    # Remove the server configuration file if it exists
    hostname_fn = '{h}.cfg'.format(h=re.sub('\s', '_', host))
    host_cfg_path = os.path.join(FireflyIRC.CONFIG_DIR, 'config', 'servers', hostname_fn)
    if os.path.exists(host_cfg_path):
        os.remove(host_cfg_path)

    click.secho('{h} configuration files and server setting attributes removed'.format(h=host), color='red', bold=True)
