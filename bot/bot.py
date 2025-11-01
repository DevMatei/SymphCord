import logging
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


class SymphCordBot(commands.Bot):
    """Discord bot that turns channel history into a short composition."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),  # fallback prefix
            intents=intents,
            application_id=self._load_application_id(),
        )
        self._sync_guild: Optional[int] = self._load_sync_guild()
        self._log = logging.getLogger("symphcord.bot")

    @staticmethod
    def _load_application_id() -> Optional[int]:
        raw_id = os.getenv("DISCORD_APPLICATION_ID")
        return int(raw_id) if raw_id else None

    @staticmethod
    def _load_sync_guild() -> Optional[int]:
        raw_guild = os.getenv("DISCORD_SYNC_GUILD_ID")
        return int(raw_guild) if raw_guild else None

    async def setup_hook(self) -> None:
        await self.load_extension("bot.cogs.composer")
        if self._sync_guild:
            guild = discord.Object(id=self._sync_guild)
            self._log.info("Syncing commands to guild %s", self._sync_guild)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            self._log.info("Syncing commands globally (can take up to an hour).")
            await self.tree.sync()

