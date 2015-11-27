import re
from ConfigParser import ConfigParser

import click
import os

from firefly import FireflyIRC
from firefly.cli.config import pass_context, Context


@click.command('create')
@click.option('-h', '--host', prompt='Server hostname', help='Server hostname.')
@click.option('-p', '--port', default=6667, prompt='Server port number', help='Server port number.')
@click.option('--auto/--no-auto', default=True, prompt='Automatically connect to this server on startup?',
              help='Automatically connect to this server. (Default: True)')
@click.option('-n', '--nick', default='Firefly', prompt='Nick', help='Nickname')
@click.option('-u', '--username', default='Firefly', prompt='Username', help='Username')
@click.option('-r', '--realname', default='Firefly Alpha', prompt='Realname', help='Real name')
@click.option('--ssl/--no-ssl', help='Enable SSL on this server. (Default: False)', default=False)
@click.option('--password', help='Server password')
@click.option('-c', '--channels', prompt='Channels to autojoin (separated by commas)',
              help='Comma separated list of channels to autojoin.')
@click.option('-f', '--force', is_flag=True, help='Overwrite any existing configuration files.')
@pass_context
def cli(ctx, host, port, auto, nick, user, realname, ssl, password, channels, force):
    """
    Start Firefly
    """
    assert isinstance(ctx, Context)

    # Make sure the server doesn't already exist in our servers configuration
    servers_config = FireflyIRC.load_configuration('servers')
    server_cfg_path = os.path.join(FireflyIRC.CONFIG_DIR, 'config', 'servers.cfg')
    if host in servers_config.sections():
        ctx.log.info('Configuration for %s already exists', host)
        if not force:
            raise click.ClickException('Configuration for {h} already exists'.format(h=host))
        servers_config.remove_section(host)

    # Make sure a configuration file for this server doesn't already exist
    hostname_fn = '{h}.cfg'.format(h=re.sub('\s', '_', host))
    host_cfg_path = os.path.join(FireflyIRC.CONFIG_DIR, 'config', 'servers', hostname_fn)

    if os.path.exists(host_cfg_path):
        ctx.log.info('Server configuration file %s already exists', hostname_fn)
        if not force:
            raise click.ClickException('Server configuration file {h_fn} already exists'.format(h_fn=host))

    # Populate servers.cfg
    servers_config.add_section(host)
    servers_config.set(host, 'Enabled', True)
    servers_config.set(host, 'Autoconnect', auto)
    servers_config.set(host, 'Nick', nick)
    servers_config.set(host, 'Username', user)
    servers_config.set(host, 'Realname', realname)
    servers_config.set(host, 'Password', password)
    servers_config.set(host, 'Port', port)
    servers_config.set(host, 'SSL', ssl)

    with open(server_cfg_path, 'w') as cf:
        servers_config.write(cf)

    # Create a server configuration file
    channels = [c.strip() for c in channels.split(',')] if channels else []

    host_config = ConfigParser()
    for channel in channels:
        host_config.add_section(channel)
        host_config.set(channel, 'Autojoin', True)
        host_config.set(channel, 'Password', '')

    with open(host_cfg_path, 'w') as cf:
        host_config.write(cf)
