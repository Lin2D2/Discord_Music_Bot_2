import discord


def simple_message(title, content, user):
    embed = discord.Embed(title=title, description=content)
    embed.set_footer(text=user.name, icon_url=user.avatar_url)
    return embed


def search_results_message(title, content, search_results, user):
    embed = discord.Embed(title=title, description=content)

    for index, search_result in enumerate(search_results):
        embed.add_field(name=f"[{search_result.title}]",
                        value=f'> (https://www.youtube.com/watch?v={search_result.id}) '
                              f'{search_result.duration}...',
                        inline=False)

    embed.set_footer(text=user.name, icon_url=user.avatar_url)
    return embed
