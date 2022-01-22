import discord


def simple_message(title, content, user):
    embed = discord.Embed(title=title, description=content)
    embed.set_footer(text=user.name, icon_url=user.avatar_url)
    return embed
