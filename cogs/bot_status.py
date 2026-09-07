import logging

import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import responses
from discord_utils.dynamic_bass_boost import get_guild_current_bass_boost
from discord_utils.dynamic_volume import get_guild_current_volume
from utils import get_full_version_info

logger = logging.getLogger('PianoNicsMusic')


class BotStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        guild = await db_utils.get_guild(ctx.guild.id)

        embed = discord.Embed(title="🎵 Bot Status", color=0x282841)

        if voice_client and voice_client.is_connected():
            channel_name = getattr(voice_client.channel, 'name', 'Unknown')
            embed.add_field(name="🔊 Voice Status", value=f"Connected to: `{channel_name}`", inline=True)

            if voice_client.is_playing():
                embed.add_field(name="▶️ Playback", value="Playing", inline=True)
            elif voice_client.is_paused():
                embed.add_field(name="⏸️ Playback", value="Paused", inline=True)
            else:
                embed.add_field(name="⏹️ Playback", value="Stopped", inline=True)
        else:
            embed.add_field(name="🔇 Voice Status", value="Not connected", inline=True)
            embed.add_field(name="⏹️ Playback", value="Inactive", inline=True)

        if guild:
            remaining = len([entry for entry in guild.queue if not entry.already_played])

            volume = get_guild_current_volume(ctx.guild.id)
            if volume is None:
                volume = guild.volume

            bass_boost = get_guild_current_bass_boost(ctx.guild.id)
            if bass_boost is None:
                bass_boost = guild.bass_boost

            embed.add_field(name="📝 Queue", value=f"{remaining} remaining / {len(guild.queue)} total", inline=True)
            embed.add_field(name="Loop", value="🔄 On" if guild.loop_queue else "⏹️ Off", inline=True)
            embed.add_field(name="Shuffle", value="🔀 On" if guild.shuffle_queue else "➡️ Off", inline=True)
            embed.add_field(name="Volume", value=f"🔊 {int(volume * 100)}%", inline=True)
            embed.add_field(name="Bass Boost", value=f"🎸 {int(bass_boost * 100)}%", inline=True)
            embed.add_field(name="Earrape", value="📢 On" if guild.earrape else "🔇 Off", inline=True)
        else:
            embed.add_field(name="📝 Queue", value="No active session", inline=True)
            embed.add_field(name="Loop", value="⏹️ Off", inline=True)
            embed.add_field(name="Shuffle", value="➡️ Off", inline=True)
            embed.add_field(name="Volume", value="🔊 100%", inline=True)
            embed.add_field(name="Bass Boost", value="🎸 100%", inline=True)
            embed.add_field(name="Earrape", value="🔇 Off", inline=True)

        embed.add_field(name="📡 Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.set_footer(text=get_full_version_info())

        await responses.reply(ctx, embed)

    @commands.command(name='bot_status', aliases=['status', 'current', 'now_playing'])
    async def status(self, ctx):
        await self.run(ctx)

    @discord.slash_command(name="bot_status", description="Shows current bot and queue status")
    async def status_slash(self, ctx):
        await self.run(ctx)


def setup(bot):
    bot.add_cog(BotStatus(bot))
