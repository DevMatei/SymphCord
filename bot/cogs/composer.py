import asyncio
import logging
from typing import Iterable, List

import discord
from discord import app_commands
from discord.ext import commands

from bot.music.note_mapper import notes_from_messages
from bot.music.synthesis import render_notes_to_wav


class Composer(commands.Cog):
    """Slash commands that turn messages into short songs."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.log = logging.getLogger("symphcord.composer")

    @app_commands.command(name="compose", description="Turn the last 100 messages into music.")
    async def compose(self, interaction: discord.Interaction) -> None:
        if not interaction.channel:
            await interaction.response.send_message("I need a channel to work with.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        history = await self._fetch_history(interaction.channel)
        events = notes_from_messages(history)
        if not events:
            await interaction.followup.send("Nothing melodic to build yet, try chatting a bit more!")
            return

        try:
            buffer, duration = await asyncio.to_thread(render_notes_to_wav, events)
        except Exception as exc:  # pydub can raise many things, keep message friendly
            self.log.exception("Failed to render composition")
            await interaction.followup.send(f"Couldn't render that tune ({exc}).")
            return

        file = discord.File(buffer, filename="symphcord_composition.wav")
        embed = discord.Embed(
            title="SymphCord Composition",
            description="100 recent messages, one melodic moment.",
            colour=discord.Colour.blurple(),
        )
        embed.add_field(name="Notes", value=str(len(events)))
        embed.add_field(name="Length", value=f"{duration:.1f} seconds")
        embed.set_footer(text="Generated with pydub oscillators")

        await interaction.followup.send(embed=embed, file=file)

    async def _fetch_history(self, channel: discord.abc.Messageable) -> List[discord.Message]:
        messages: List[discord.Message] = []
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
            return messages

        async for message in channel.history(limit=100, oldest_first=True):
            messages.append(message)
        return messages


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Composer(bot))
