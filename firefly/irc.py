import venusian
import logging


################################
# Event constants              #
################################

on_created                  = 'created'
on_server_host              = 'yourHost'
on_client_info              = 'myInfo'
on_luser_client             = 'luserClient'
on_bounce                   = 'bounce'
on_server_supports          = 'isupport'
on_luser_channels           = 'luserChannels'
on_luser_ops                = 'luserOp'
on_luser_connection         = 'luserMe'
on_message                  = 'privmsg'
on_channel_message          = 'channelMessage'  # custom event
on_private_message          = 'privateMessage'  # custom event
on_client_join              = 'joined'
on_client_part              = 'left'
on_notice                   = 'noticed'
on_channel_notice           = 'channelNotice'  # custom event
on_private_notice           = 'privateNotice'  # custom event
on_mode_changed             = 'modeChanged'
# on_channel_mode_changed     = 'channelModeChanged'  # custom event
# on_client_mode_changed      = 'clientModeChanged'  # custom event
on_pong                     = 'pong'
on_client_signed_on         = 'signedOn'
on_client_kicked            = 'kickedFrom'
on_client_nick              = 'nickChanged'
on_channel_join             = 'userJoined'
on_channel_part             = 'userLeft'
on_user_quit                = 'userQuit'
on_channel_kick             = 'userKicked'
on_action                   = 'action'
on_channel_action           = 'channelAction'  # custom event
on_private_action           = 'privateAction'  # custom event
on_channel_topic_updated    = 'topicUpdated'
on_user_nick_changed        = 'userRenamed'
on_server_motd              = 'receivedMOTD'
on_err_nick_in_use          = 'irc_ERR_NICKNAMEINUSE'
on_err_bad_password         = 'irc_ERR_PASSWDMISMATCH'
on_server_welcome           = 'irc_RPL_WELCOME'
on_unknown                  = 'irc_unknown'
on_ctcp                     = 'ctcpQuery'
on_ctcp_ping                = 'ctcpQuery_PING'
on_ctcp_finger              = 'ctcpQuery_FINGER'
on_ctcp_version             = 'ctcpQuery_VERSION'
on_ctcp_source              = 'ctcpQuery_SOURCE'
on_ctcp_userinfo            = 'ctcpQuery_USERINFO'
on_ctcp_time                = 'ctcpQuery_TIME'


################################
# Plugin decorators            #
################################

# noinspection PyPep8Naming
class event(object):
    """
    IRC event decorator.
    """
    def __init__(self, event_name=None, permission=None, **kwargs):
        """
        @type   event_name: C{str} or C{None}
        @param  event_name: Name of the event. If None, uses the name of the function.
        When using the name of the function, the function should be named after the constant KEY, *NOT* value.
        For example, an event function should be named C{on_channel_join} instead of C{userJoined}.

        @type   permission: C{str} or C{None}
        @param  permission: The minimum user permission level required to trigger this event.
        """
        self.event_name = event_name
        self.permission = permission.strip().lower() if permission else 'guest'
        self.command_ok = kwargs.get('command_ok', False)
        self.reply_ok   = kwargs.get('reply_ok', False)

    def __call__(self, func):
        """
        @param  func:   The event function.

        @return:    The decorated function.
        """
        logging.getLogger('firefly.event').debug('Decorating event function: %s (%s)', self.event_name, str(func))

        def callback(scanner, name, ob):
            event_name = self.event_name or func.__name__
            params = {
                'name': event_name,
                'permission': self.permission,
                'command_ok': self.command_ok,
                'reply_ok': self.reply_ok
            }

            scanner.firefly.registry.bind_event(event_name, ob, func, params)
            return func

        venusian.attach(func, callback, category='events')
        return func


# noinspection PyPep8Naming
class command(object):
    """
    IRC command decorator.
    """
    def __init__(self, command_name=None, permission=None, **kwargs):
        """
        @type   command_name:   C{str} or C{None}
        @param  command_name:   Name of the command. If None, uses the name of the function.

        @type   permission: C{str} or C{None}
        @param  permission: The minimum user permission level required to call this command.
        """
        self.command_name = command_name
        self.permission = permission.strip().lower() if permission else 'guest'

    def __call__(self, func):
        """
        @param  func:   The command function.

        @return:    The decorated function.
        """
        logging.getLogger('firefly.command').debug('Decorating command function: %s (%s)', self.command_name, str(func))

        def callback(scanner, name, ob):
            command_name = self.command_name or func.__name__
            command_name = command_name.lower().strip().replace(' ', '_')
            params = {'name': command_name, 'permission': self.permission}

            scanner.firefly.registry.bind_command(command_name, ob, func, params)
            return func

        venusian.attach(func, callback, category='commands')
        return func
