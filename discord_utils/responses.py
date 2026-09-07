import discord

from discord_utils import embed_generator

NOT_CONNECTED = "Bot is not connected to a Voice channel"


def is_prefix(ctx) -> bool:
    return getattr(ctx, "message", None) is not None


async def reply(ctx, embed: discord.Embed):
    if is_prefix(ctx):
        return await ctx.send(embed=embed)
    return await ctx.respond(embed=embed)


async def confirm(ctx, emoji: str, title: str, message: str):
    if is_prefix(ctx):
        return await ctx.message.add_reaction(emoji)
    return await ctx.respond(embed=await embed_generator.create_success_embed(f"{emoji} {title}", message))


async def fail(ctx, title: str, message: str):
    return await reply(ctx, await embed_generator.create_error_embed(title, message))


async def not_connected(ctx):
    return await fail(ctx, "Error", NOT_CONNECTED)
