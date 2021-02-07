"""
Created by Epic at 12/31/20
"""
from .types import Cog

from importlib import import_module
from logging import getLogger
from speedcord.http import Route


class CommandHandler:
    def __init__(self, client, client_id, *, prefix=None, cogs_directory="cogs", guild_id=None):
        self.client = client
        self.client_id = client_id
        self.logger = getLogger("speedian.command_handler")
        self.loop = client.loop
        self.prefix = prefix
        self.allow_text_commands = self.prefix is not None
        self.cogs_directory = cogs_directory
        self.cogs = []
        self.commands = []
        self.guild_id = guild_id
        self.to_be_added = []
        self.client.event_dispatcher.register("INTERACTION_CREATE", self.interaction_create)

    def load_extension(self, extension_name):
        self.loop.create_task(self._load_extension(extension_name))

    async def _load_extension(self, extension_name):
        extension = import_module("." + extension_name, self.cogs_directory)
        for cog_attr_name in dir(extension):
            cog_attr = getattr(extension, cog_attr_name)
            if Cog in getattr(cog_attr, "__bases__", []):
                self.logger.debug("Adding cog \"%s\"" % cog_attr.__name__)
                await self.add_cog(cog_attr)

    async def add_cog(self, cog_uninitialized):
        cog = cog_uninitialized(self.client)
        self.cogs.append(cog)
        for command in cog.commands:
            self.commands.append(command)
            self.create_command(command)
        await self.push_commands()

    def create_command(self, command):
        data = command.export_slash_command()
        self.logger.debug("Adding slash command with data %s" % data)
        self.to_be_added.append(data)

    async def push_commands(self):
        await self.client.connected.wait()
        if self.guild_id is None:
            r = Route("PUT", "/applications/{application_id}/commands", application_id=self.client_id)
        else:
            r = Route("PUT", "/applications/{application_id}/guilds/{guild_id}/commands", application_id=self.client_id,
                      guild_id=self.guild_id)
        self.logger.debug("Pushing commands")
        r = await self.client.http.request(r, json=self.to_be_added)
        self.logger.debug(await r.json())

    def get_command(self, command_name):
        for command in self.commands:
            if command.name == command_name:
                return command

    async def interaction_create(self, data, shard):
        self.logger.debug("Received interaction data %s" % data)
        token = data["token"]
        interaction_id = data["id"]
        command = self.get_command(data["data"]["name"])

        if not command.silent:
            r = Route("POST", "/interactions/{interaction_id}/{interaction_token}/callback",
                      interaction_id=interaction_id, interaction_token=token)
            await self.client.http.request(r, json={"type": 5})
