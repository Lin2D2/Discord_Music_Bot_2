import logging

import discord

import embeds


class Commands:
    def __init__(self, client, prefix):
        self.client = client
        self.prefix = prefix
        self.commands = [
            CommandType("help", self.help, "list available commands"),
            CommandType("join", self.join, "connects to authors voice channel"),
            CommandType("leave", self.leave, "disconnects from current voice channel")
        ]

    async def command(self, message):
        command = message.content.split(" ")[0].replace(self.prefix, "")
        result_list = list(filter(lambda command_type: command_type.command == command, self.commands))
        if len(result_list) == 1:
            result = result_list[0]
            await result.function(message)
            return
        if len(result_list) == 0:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            f"**Unknown Command:** \"{command}\"",
                                            self.client.user),
                delete_after=10
            )
            return
        await message.channel.send(
            embed=embeds.simple_message("ERROR",
                                        f"**Multiple Commands matched:** \"{command}\", {result_list}",
                                        self.client.user),
            delete_after=10
        )
        logging.warning(f"found multiple commands: {result_list}")
        return

    async def help(self, message):
        answer = "__**available commands**__:\n"
        for command in self.commands:
            answer += f"> **{self.prefix}{command.command}** :: {command.description}\n"
        await message.channel.send(embed=embeds.simple_message("Help", answer, self.client.user), delete_after=120)
        return

    async def join(self, message):
        author = message.author
        if author.voice.channel:
            try:
                await author.voice.channel.connect()
                await message.channel.send(
                    embed=embeds.simple_message("Joined",
                                                f"Joined, {author.name} in {author.voice.channel.name}",
                                                self.client.user),
                    delete_after=10
                )
            except discord.ClientException:
                await message.channel.send(
                    embed=embeds.simple_message("ERROR",
                                                "Bot already in voice channel",
                                                self.client.user),
                    delete_after=10
                )
            return
        await message.channel.send(
            embed=embeds.simple_message("ERROR",
                                        "Author not in any voice channel",
                                        self.client.user),
            delete_after=10
        )
        return

    async def leave(self, message):
        # NOTE filter for current author
        result_list = list(filter(lambda voice_client: voice_client.channel == message.author.voice.channel,
                                  self.client.voice_clients))
        if len(result_list) == 1:
            result = result_list[0]
            await result.disconnect()
            await message.channel.send(
                embed=embeds.simple_message("Disconnected",
                                            f"Disconnected from {result.channel.name}",
                                            self.client.user),
                delete_after=10
            )
            return
        # NOTE filter for current server
        result_list = list(filter(lambda voice_client: voice_client.guild.name == message.guid.name, result_list))
        if len(result_list) == 1:
            result = result_list[0]
            await result.disconnect()
            await message.channel.send(
                embed=embeds.simple_message("Disconnected",
                                            f"Disconnected from {result.channel.name}",
                                            self.client.user),
                delete_after=10
            )
            return
        await message.channel.send(
            embed=embeds.simple_message("ERROR",
                                        "Not in any voice channels",
                                        self.client.user),
            delete_after=10
        )
        return


class CommandType:
    def __init__(self, command, function, description):
        self.command = command
        self.function = function
        self.description = description
