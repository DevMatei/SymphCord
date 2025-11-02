import asyncio
import logging
import os
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
        events = notes_from_messages(history, beat=0.55)
        if not events:
            await interaction.followup.send("Nothing melodic to build yet, try chatting a bit more!")
            return

        try:
            buffer, duration = await asyncio.to_thread(
                render_notes_to_wav,
                events,
                20.0,
                35.0,
            )
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

    @app_commands.command(name="help", description="Show what SymphCord can do.")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="SymphCord Help",
            description="SymphCord turns message history into short, melodic clips.",
            colour=discord.Colour.blurple(),
        )
        embed.add_field(
            name="/compose",
            value="Fetch the latest 100 messages and return a 20–35 second composition.",
            inline=False,
        )
        embed.add_field(
            name="/creator",
            value="See who built this bot and where to find it.",
            inline=False,
        )
        embed.add_field(
            name="/purpose",
            value="Learn why the project exists and what inspired it.",
            inline=False,
        )
        embed.add_field(
            name="/ping",
            value="See if the bot is responsive and check the heartbeat latency.",
            inline=False,
        )
        embed.add_field(
            name="/botinfo",
            value="Version, uptime, and SoundFont status for this instance.",
            inline=False,
        )
        embed.set_footer(text="Need something else? Ping the project maintainers.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="creator", description="Who crafted SymphCord?")
    async def creator(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="SymphCord Creator",
            description=(
                "SymphCord was made by [DevMatei](https://github.com/DevMatei).\n"
                "Check out the source code on [GitHub](https://github.com/DevMatei/SymphCord)."
            ),
            colour=discord.Colour.green(),
        )
        embed.add_field(
            name="Tech Stack",
            value="discord.py · PyDub · PrettyMIDI · SoundFont rendering",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="purpose", description="Why does SymphCord exist?")
    async def purpose(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Why SymphCord?",
            description=(
                "idk i made it for a YSWS hackclub project\n"
                "Drop /compose to hear your server's rhythm!"
            ),
            colour=discord.Colour.gold(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check if SymphCord is alive.")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = self.bot.latency * 1000 if self.bot.latency else 0.0
        embed = discord.Embed(
            title="SymphCord Pong!",
            description="I'm here and listening.",
            colour=discord.Colour.teal(),
        )
        embed.add_field(name="WebSocket latency", value=f"{latency_ms:.1f} ms")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="botinfo", description="SymphCord version and runtime details.")
    async def botinfo(self, interaction: discord.Interaction) -> None:
        uptime = discord.utils.utcnow() - self.bot.start_time if hasattr(self.bot, "start_time") else None
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600:02}:{(uptime.seconds // 60) % 60:02}:{uptime.seconds % 60:02}" if uptime else "Unknown"
        soundfont = os.getenv("SOUNDFONT_PATH")
        embed = discord.Embed(
            title="SymphCord Info",
            colour=discord.Colour.purple(),
        )
        embed.add_field(name="Version", value=os.getenv("SYMPHCORD_VERSION", "dev-build"), inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="SoundFont", value=soundfont if soundfont else "Disabled", inline=False)
        embed.set_footer(text="Thanks for making SymphCord part of your server.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _fetch_history(self, channel: discord.abc.Messageable) -> List[discord.Message]:
        messages: List[discord.Message] = []
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
            return messages

        async for message in channel.history(limit=100, oldest_first=True):
            messages.append(message)
        return messages


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Composer(bot))
