import logging

import discord
from discord.ext import commands

import db_utils.db_utils as db_utils
from discord_utils import embed_generator, player, responses
from media import resolver
from media.resolver import ArgonFetchError

logger = logging.getLogger('PianoNicsMusic')


async def resolve_tracks(ctx, query):
    try:
        return await resolver.get_tracks(query)
    except ArgonFetchError as error:
        await responses.fail(ctx, "Error", str(error))
    except Exception as error:
        logger.error(f"Error resolving {query}: {error}")
        await responses.fail(ctx, "Error", "Failed to process your request. Please try again.")

    return None, 0


class Play(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def run(self, ctx, query):
        if getattr(ctx, "message", None) and ctx.message.attachments:
            query = ctx.message.attachments[0].url

        if not query:
            await responses.fail(ctx, "Missing Input", "Please provide a query or attach a file.")
            return

        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        user_channel = ctx.author.voice.channel if ctx.author.voice else None

        if voice_client and voice_client.channel:
            if not user_channel or user_channel.id != voice_client.channel.id:
                await responses.fail(
                    ctx,
                    "Channel Conflict",
                    f"Bot is already playing music in another voice channel: "
                    f"`{voice_client.channel.name}`. Please join that channel to queue music.",
                )
                return

        tracks, dropped = await resolve_tracks(ctx, query)

        if not tracks:
            return

        guild = await db_utils.get_guild(ctx.guild.id)

        if not guild:
            if not user_channel:
                await responses.fail(
                    ctx, "Voice Channel Required", "You must be in a voice channel to use this command!"
                )
                return

            await db_utils.create_new_guild(ctx.guild.id)

            try:
                await user_channel.connect()
            except discord.errors.ClientException as error:
                logger.warning(f"Voice connection error: {error}")
                await db_utils.delete_guild(ctx.guild.id)
                await responses.fail(
                    ctx, "Connection Failed", "Failed to connect to voice channel. The bot might already be connected elsewhere."
                )
                return
            except Exception as error:
                logger.error(f"Unexpected voice connection error: {error}")
                await db_utils.delete_guild(ctx.guild.id)
                await responses.fail(
                    ctx, "Connection Error", "An error occurred while connecting to the voice channel. Please try again."
                )
                return

        was_empty = (await db_utils.get_queue_total_entries(ctx.guild.id)) == 0

        await db_utils.add_to_queue(ctx.guild.id, tracks)

        if dropped:
            await responses.reply(
                ctx,
                await embed_generator.create_embed(
                    "Queue", f"Added **{len(tracks)}** Songs to the Queue. **{dropped}** more were left out."
                ),
            )
            if not was_empty:
                return
        elif len(tracks) > 1:
            await responses.reply(
                ctx, await embed_generator.create_embed("Queue", f"Added **{len(tracks)}** Songs to the Queue")
            )
            if not was_empty:
                return
        elif not was_empty:
            await responses.confirm(ctx, "📥", "Added", "Added to the queue")
            return

        await self.play_queue(ctx)

    async def play_queue(self, ctx):
        try:
            while True:
                url = await db_utils.get_queue_entry(ctx.guild.id)

                if not url:
                    break

                try:
                    await player.play(ctx, url)
                except Exception as error:
                    logger.error(f"Error playing song {url}: {error}")
                    try:
                        await responses.reply(
                            ctx, await embed_generator.create_embed("Error", "Failed to play a song. Skipping to next...")
                        )
                    except Exception as send_error:
                        logger.error(f"Failed to send error message: {send_error}")
        except Exception as error:
            logger.critical(f"Critical error in play loop: {error}")
        finally:
            voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

            if voice_client:
                try:
                    await voice_client.disconnect()
                except Exception as error:
                    logger.error(f"Error disconnecting voice client: {error}")

            try:
                await db_utils.delete_guild(ctx.guild.id)
            except Exception as error:
                logger.error(f"Error cleaning up guild data: {error}")

    @commands.command(name='play', aliases=['p', 'pl', 'play_song', 'add', 'enqueue'])
    async def play(self, ctx, *, query=None):
        await self.run(ctx, query)

    @discord.slash_command(name="play", description="Plays the provided audio")
    async def play_slash(self, ctx, query: str = None, file: discord.Attachment = None):
        await ctx.defer()

        if file:
            query = file.url

        await self.run(ctx, query)


def setup(bot):
    bot.add_cog(Play(bot))
