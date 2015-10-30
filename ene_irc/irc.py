# noinspection PyPep8Naming
class event(object):

    def __init__(self, event_name='', permission='guest'):
        self.event = event_name
        self.permission = permission

    def __call__(self, f):
        """
        If there are decorator arguments, __call__() is only called
        once, as part of the decoration process! You can only give
        it a single argument, which is the function object.
        """
        f.ene.bind_event(self.event, f)


on_created                  = 'created'
on_server_host              = 'yourHost'
on_client_info              = 'myInfo'
on_luser_client             = 'luserClient'
on_bounce                   = 'bounce'
on_server_supports          = 'isupport'
on_luser_channels           = 'luserChannels'
on_luser_ops                = 'luserOp'
on_luser_connection         = 'luserMe'
on_channel_message          = 'channelMessage'  # custom event
on_private_message          = 'privateMessage'  # custom event
on_client_join              = 'joined'
on_client_part              = 'left'
on_channel_notice           = 'channelNotice'  # custom event
on_private_notice           = 'privateNotice'  # custom event
on_channel_mode_changed     = 'channelModeChanged'  # custom event
on_client_mode_changed      = 'clientModeChanged'  # custom event
on_pong                     = 'pong'
on_client_signed_on         = 'signedOn'
on_client_kicked            = 'kickedFrom'
on_client_nick              = 'nickChanged'
on_channel_join             = 'userJoined'
on_channel_part             = 'userLeft'
on_user_quit                = 'userQuit'
on_channel_kick             = 'userKicked'
on_channel_action           = 'channelAction'  # custom event
on_private_action           = 'privateAction'  # custom event
on_channel_topic_updated    = 'topicUpdated'
on_user_nick_changed        = 'userRenamed'
on_server_motd              = 'receivedMOTD'
on_err_nick_in_use          = 'irc_ERR_NICKNAMEINUSE'
on_err_bad_password         = 'irc_ERR_PASSWDMISMATCH'
on_server_welcome           = 'irc_RPL_WELCOME'
on_ctcp                     = 'ctcpQuery'
on_ctcp_action              = 'ctcpQuery_ACTION'
on_ctcp_ping                = 'ctcpQuery_PING'
on_ctcp_finger              = 'ctcpQuery_FINGER'
on_ctcp_version             = 'ctcpQuery_VERSION'
on_ctcp_source              = 'ctcpQuery_SOURCE'
on_ctcp_userinfo            = 'ctcpQuery_USERINFO'
on_ctcp_time                = 'ctcpQuery_TIME'

