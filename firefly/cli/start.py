import logging

import click
import os
from twisted.internet import protocol, reactor

from firefly import FireflyIRC
from firefly.cli import pass_context
from firefly.containers import Server


@click.command('start')
@pass_context
def cli(ctx):
    """
    Start Firefly
    """
    # Make sure we don't already have a PID stored
    if not os.path.exists(FireflyIRC.DATA_DIR):
        os.makedirs(FireflyIRC.DATA_DIR)

    pid_file = os.path.join(FireflyIRC.DATA_DIR, 'firefly.pid')
    if os.path.exists(pid_file):
        raise Exception('An instance of Firefly is already running. Even if you are sure this is not the case, please '
                        'run firefly stop and try again.')

    # Load our first server
    servers_config = FireflyIRC.load_configuration('servers')
    servers = []
    hostnames = servers_config.sections()
    for hostname in hostnames:
        if servers_config.getboolean(hostname, 'Enabled'):
            factory = FireflyFactory(Server(hostname, servers_config))
            servers.append(factory)
            reactor.connectTCP(factory.firefly.server.hostname, factory.firefly.server.port, factory)

    # Write our PID file
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    # Run
    try:
        reactor.run()
    except Exception:
        if os.path.exists(pid_file):
            os.remove(pid_file)
        raise

    if os.path.exists(pid_file):
        os.remove(pid_file)


class FireflyFactory(protocol.ClientFactory):
    """
    A factory for generating Firefly connections.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, server):
        self.firefly = FireflyIRC(server)

    def buildProtocol(self, addr):
        self.firefly.factory = self
        return self.firefly

    def clientConnectionLost(self, connector, reason):
        """
        If we get disconnected, reconnect to server.
        """
        logging.getLogger('firefly.factory').warn('Lost connection to server: %s', reason)
        logging.getLogger('firefly.factory').warn('Reconnecting to server: %s', repr(connector))
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        logging.getLogger('firefly.factory').error('Connection failed: %s (%s)', reason, repr(connector))
        reactor.stop()
