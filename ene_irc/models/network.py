from voluptuous import Schema, Required, Optional, All, Length, Range, Match
from ene_irc.models import DbSession
from ene_irc.models.base import ProtocolIrcNetwork as NetworkModel
from ene_irc.validator import Validator


class Network:
    """
    Create, modify, delete and retrieve IRC Networks from the database
    """
    # Attributes
    NAME = "name"
    HOST = "host"
    PORT = "port"
    NICK = "nick"
    AUTOJOIN = "autojoin"
    HAS_SERVICES = "has_services"
    AUTH_METHOD = "auth_method"
    USER_PASS = "user_password"
    SERV_PASS = "server_password"

    validAttributes = [NAME, HOST, PORT, NICK, AUTOJOIN, HAS_SERVICES, AUTH_METHOD, USER_PASS, SERV_PASS]

    # Auth methods
    AUTH_NICKSERV = "NICKSERV"
    AUTH_SERVPASS = "SERVPASS"

    validAuthMethods = [AUTH_NICKSERV, AUTH_SERVPASS]

    def __init__(self):
        """
        Initialize a new Network instance
        """
        self.dbs = DbSession()
        self.validate = NetworkValidators()

    def all(self, autojoin_only=True):
        """
        Return networks we should automatically join by default, or all networks when autojoin_only is False
        Args:
            autojoin_only(bool, optional): Return only the networks we should autojoin on startup. Defaults to True
        Returns:
            list
        """
        query = self.dbs.query(NetworkModel)

        if autojoin_only:
            query.filter(NetworkModel.autojoin == True)

        return query.all()

    def exists(self, name=None, host=None):
        """
        Check whether a network by the specified name -OR- host exists
        Args:
            name(str, optional): The name/alias for the network
            host(str, optional): The networks host
        Returns:
            bool
        Raises:
            MissingArgumentsError: Neither the network name or host were passed as arguments
        """
        if name:
            return bool(self.dbs.query(NetworkModel).filter(NetworkModel.name == name).count())

        if host:
            return bool(self.dbs.query(NetworkModel).filter(NetworkModel.host == host).count())

        raise MissingArgumentsError("You must specify either a network name or host to check")

    def get(self, db_id=None, name=None, host=None):
        """
        Retrieve a network by its name or host
        Args:
            id(int, optional): The database ID of the network
            name(str, optional): The name/alias of the network
            host(str, optional): The networks host
        Returns:
            database.models.Network
        Raises:
            MissingArgumentsError: Neither the network name or host were passed as arguments
            NetworkNotFoundError: The requested network could not be found
        """
        network = None
        if db_id:
            network = self.dbs.query(NetworkModel).filter(NetworkModel.id == db_id).first()
        elif name:
            network = self.dbs.query(NetworkModel).filter(NetworkModel.name == name).first()
        elif host:
            network = self.dbs.query(NetworkModel).filter(NetworkModel.host == host).first()
        else:
            raise MissingArgumentsError("You must specify either a network ID, name or host to retrieve")

        if not network:
            raise NetworkNotFoundError

        return network

    def create(self, name, host, **kwargs):
        """
        Create a new network
        Args:
            name(str): The name/alias for the network
            host(str): The host to connect to
            port(int, optional): The port number to connect to. Defaults to 6667
            server_password(str, optional): The server password (if required). Defaults to None
            nick(str, optional): A custom IRC nick to use on this server. Defaults to None
            nick_password(str, optional): The password used to identify to network services. Defaults to None
            has_services(bool, optional): Whether or not the network has a services engine. Defaults to True
            user_password(str, optional): NickServ account password
            auth_method(str or None, optional): The NickServ authentication method
            autojoin(bool, optional): Should we automatically join this network on startup? Defaults to True
        Returns:
            database.models.Network
        """
        # Set arguments
        kwargs = dict(name=name, host=host, **kwargs)
        kwargs = dict((key, value) for key, value in kwargs.items() if value)

        # Validate input
        self.validate.creation(**kwargs)

        # Set up a new Network Model
        new_network = NetworkModel(**kwargs)

        # Insert the new network into our database
        self.dbs.add(new_network)
        self.dbs.commit()

        return new_network

    def remove(self, network):
        """
        Delete an existing network
        Args:
            network(database.models.Network): The Network to remove
        """
        self.dbs.delete(network)
        self.dbs.commit()


class NetworkValidators(Validator):
    def __init__(self):
        # Run our parent Validator constructor
        super(NetworkValidators, self).__init__()

        # Set our validation rules
        self.rules = {
            'name': All(str, Length(max=255), Match(r'^\S+$')),
            'host': All(str, Length(max=255), Match(r'^(?=.{1,255}$)[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?'
                                                    r'(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*\.?$')),
            'port': All(int, Range(1, 65535)),
            'server_password': All(str, Length(max=255)),
            'nick': All(str, Length(max=50), Match(r'^[a-zA-Z\^_`{|}][0-9a-zA-Z\^_`{|}]*$')),
            'has_services': All(bool),
            'user_password': All(str, Length(max=255)),
            'auth_method': All(str, Length(max=25)),
            'autojoin': All(bool)
        }

        # Set our validation messages
        self.messages = {
            'name': "The network name you provided is invalid. The network name should not contain any spaces and can "
                    "be up to 255 characters in length.",
            'host': "The hostname you provided is not valid. Please check your input and try again.",
            'port': "The port number you provided is not valid. The port number must be an integer between 1 and 65535",
            'server_password': "The server password you provided is not valid. The server password may contain a "
                               "maximum of 255 characters",
            'nick': "The IRC nick you provided is invalid. Nicks may be up to 50 characters in length, can not start "
                    "with a number and may only contain the following characters: 0-9 a-z A-Z ^ _ ` { | }",
            'has_services': "Has services must contain a valid boolean value (True or False)",
            'user_password': "The user password you provided is invalid. The user password may be up to 255 characters "
                             "in length.",
            'auth_method': "The auth method you provided was invalid.",
            'autojoin': "Autojoin must contain a valid boolean value (True or False)"
        }

    def creation(self, **kwargs):
        schema = Schema({
            Required('name'): self.rules['name'],
            Required('host'): self.rules['host'],
            Required('port'): self.rules['port'],
            Optional('server_password'): self.rules['server_password'],
            Optional('nick'): self.rules['nick'],
            Optional('has_services'): self.rules['has_services'],
            Optional('user_password'): self.rules['user_password'],
            Optional('auth_method'): self.rules['auth_method'],
            Optional('autojoin'): self.rules['autojoin']
        })

        self.validate(schema, **kwargs)

    def editing(self, **kwargs):
        schema = Schema({
            Optional('name'): self.rules['name'],
            Optional('host'): self.rules['host'],
            Optional('port'): self.rules['port'],
            Optional('server_password'): self.rules['server_password'],
            Optional('nick'): self.rules['nick'],
            Optional('has_services'): self.rules['has_services'],
            Optional('user_password'): self.rules['user_password'],
            Optional('auth_method'): self.rules['auth_method'],
            Optional('autojoin'): self.rules['autojoin']
        })

        self.validate(schema, **kwargs)


# Exceptions
class MissingArgumentsError(Exception):
    pass


class NetworkNotFoundError(Exception):
    pass
