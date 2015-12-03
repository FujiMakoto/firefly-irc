import click
import os

from firefly import FireflyIRC
from firefly.cli.config import pass_context, Context


@click.command('userdel')
@click.argument('email')
@click.option('--no-prompt', help='Skip the safety deletion prompt', is_flag=True)
@pass_context
def cli(ctx, email, no_prompt):
    """
    Deletes a user account
    """
    assert isinstance(ctx, Context)

    # Make sure this user actually exists in our configuration
    users_config = FireflyIRC.load_configuration('users')
    users_cfg_path = os.path.join(FireflyIRC.CONFIG_DIR, 'config', 'users.cfg')
    if email not in users_config.sections():
        ctx.log.error('No configuration for %s exists', email)
        raise click.ClickException('No such user: {e}'.format(e=email))

    # Confirm
    if not no_prompt:
        click.confirm('You are about to delete the user account {e} ({n})\nAre you sure you want to do this?'
                      .format(e=email, n=users_config.get(email, 'Nick')), abort=True)

    # Remove the host from servers.cfg
    users_config.remove_section(email)
    with open(users_cfg_path, 'w') as cf:
        users_config.write(cf)

    click.secho('Deleted user account {e}'.format(e=email), bold=True)
