"""
Created by Epic at 12/31/20
"""
from logging import getLogger
from speedcord.ext.typing.context import MessageContext
from speedcord.http import Route


class Cog:
    def __init__(self, client):
        self.client = client
        self.logger = getLogger("speedian.cogs.%s" % self.__module__)
        self.commands = []
        self.event_listeners = []

        for attribute_name in dir(self):
            attr = getattr(self, attribute_name)
            if isinstance(attr, Command):
                attr.cog = self
                self.commands.append(attr)


class Command:
    def __init__(self, func, name=None, *, description="\u200B", silent=False, default_permission=True):
        self.func = func
        self.cog = None  # Gets filled in by Cog
        self.name = name or func.__name__
        self.description = description

        self.data = {}
        self.options = getattr(func, "options", [])
        self.options.reverse()
        self.silent = silent
        self.default_permission = default_permission

    def export_slash_command(self):
        return {
            "name": self.name,
            "description": self.description,
            "options": [i.export() for i in self.options],
            "default_permission": self.default_permission
        }

    def get_option(self, name):
        for opt in self.options:
            if opt.name == name:
                return opt


class CommandContext:
    def __init__(self, **params):
        self.command = params["command"]
        self.is_slash_command = params["token"] is not None
        self.token = params["token"]
        self.params = params["params"]
        self.client = params["client"]
        self.disable_mentions = params["disable_mentions"]
        self.client_id = params["client_id"]
        self.interaction_id = params["interaction_id"]

        self.message = MessageContext(self.client, params["data"])

    async def send(self, content=None, **kwargs):
        if content is not None:
            kwargs["content"] = content
        if self.disable_mentions and "allowed_mentions" not in kwargs.keys():
            kwargs["allowed_mentions"] = {"parse": ["users"]}

        if self.command.silent:
            kwargs["flags"] = 64
        self.client.logger.info(kwargs)
        r = Route("POST", "/interactions/{interaction_id}/{interaction_token}/callback", interaction_id=self.interaction_id,
                  interaction_token=self.token)
        return await self.client.http.request(r, json={"type": 4, "data": kwargs})


class Option:
    def __init__(self, name, option_type, *, description, choices, default, required):
        if choices is not None:
            self.choices = [{"name": choice, "value": index} for index, choice in enumerate(choices)]
        else:
            self.choices = None
        self.name = name
        self.description = description
        self.required = required
        self.default = default

        if required and default:
            raise TypeError("Default has to be optional.")
        if option_type not in OPTION_TYPES:
            raise TypeError("Invalid option type")
        self.type = OPTION_TYPES[option_type]

    def export(self):
        data = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default
        }
        if self.choices:
            data["choices"] = self.choices
        return data


# Option types
class UserType:
    pass


class ChannelType:
    pass


class RoleType:
    pass


OPTION_TYPES = {
    str: 3,
    int: 4,
    bool: 5,
    UserType: 6,
    ChannelType: 7,
    RoleType: 8
}
