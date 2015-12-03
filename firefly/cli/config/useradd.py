import click
import os
from passlib.hash import bcrypt

from firefly import FireflyIRC
from firefly.cli.config import pass_context, Context


@click.command('useradd')
@click.option('-e', '--email', prompt='Email', help='Account e-mail address / login')
@click.password_option(help='Account password')
@click.option('-g', '--group', prompt='User group', help='Account group / access level',
              type=click.Choice(['user', 'admin']))
@click.option('-n', '--nick', prompt='Nickname', help='Nickname / alias')
@click.option('-d', '--display-name', prompt='Display name', help='Full name')
@click.option('-f', '--force', is_flag=True, help='Overwrite any existing user configuration')
@pass_context
def cli(ctx, email, password, group, nick, display_name, force):
    """
    Creates a new user account
    """
    assert isinstance(ctx, Context)

    # Make sure our configuration directory exists
    config_dir = os.path.join(FireflyIRC.CONFIG_DIR, 'config')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, 0o755)

    # Make sure the user doesn't already exist in our servers configuration
    users_config = FireflyIRC.load_configuration('users')
    users_cfg_path = os.path.join(config_dir, 'users.cfg')
    if email in users_config.sections():
        ctx.log.info('Configuration for %s already exists', email)
        if not force:
            raise click.ClickException('Configuration for {e} already exists'.format(e=email))
        users_config.remove_section(email)

    # Populate users.cfg
    users_config.add_section(email)
    users_config.set(email, 'Password', bcrypt.encrypt(password))
    users_config.set(email, 'Group', group)
    users_config.set(email, 'Nick', nick)
    users_config.set(email, 'DisplayName', display_name)

    # Write to our users configuration file
    with open(users_cfg_path, 'w') as cf:
        users_config.write(cf)

    click.secho('Configuration for user {e} successfully generated'.format(e=email), bold=True)
    click.secho('Users configuration path: {sp}'.format(sp=users_cfg_path), bold=True)
