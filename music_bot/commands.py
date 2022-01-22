import logging

import discord

import embeds


class Commands:
    def __init__(self, user, prefix):
        self.user = user
        self.prefix = prefix
        self.commands = [
            CommandType("help", self.help, "list available commands"),
            CommandType("join", self.join, "join authors voice channel")
        ]

    async def command(self, message):
        command = message.content.split(" ")[0].replace(self.prefix, "")
        result_list = list(filter(lambda command_type: command_type.command == command, self.commands))
        if len(result_list) == 1:
            result = result_list[0]
            await result.function(message)
        elif len(result_list) == 0:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            f"**Unknown Command:** \"{command}\"",
                                            self.user),
                delete_after=10
            )
        else:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            f"**Multiple Commands matched:** \"{command}\", {result_list}",
                                            self.user),
                delete_after=10
            )
            logging.warning(f"found multiple commands: {result_list}")

    async def help(self, message):
        answer = "__**available commands**__:\n"
        for command in self.commands:
            answer += f"> **{self.prefix}{command.command}** :: {command.description}\n"
        await message.channel.send(embed=embeds.simple_message("Help", answer, self.user), delete_after=120)

    async def join(self, message):
        author = message.author
        if author.voice.channel:
            try:
                await author.voice.channel.connect()
                await message.channel.send(
                    embed=embeds.simple_message("Joined",
                                                f"Joined, {author.name} in {author.voice.channel.name}",
                                                self.user),
                    delete_after=10
                )
            except discord.ClientException:
                await message.channel.send(
                    embed=embeds.simple_message("ERROR",
                                                "Bot already in voice channel",
                                                self.user),
                    delete_after=10
                )
        else:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Author not in any voice channel",
                                            self.user),
                delete_after=10
            )


class CommandType:
    def __init__(self, command, function, description):
        self.command = command
        self.function = function
        self.description = description
