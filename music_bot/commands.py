import logging
import time

import discord
import discord_components as dc

import embeds
import search


class Commands:
    def __init__(self, client, prefix):
        self.client = client
        self.prefix = prefix
        self.commands = [
            CommandType("help", self.help, "list available commands"),
            CommandType("join", self.join, "connects to authors voice channel"),
            CommandType("leave", self.leave, "disconnects from current voice channel"),
            CommandType("search", self.search, "searches on youtube for the query after the command, "
                                               "and lets you select out of 8 results"),
            CommandType("play", self.play, "plays query after command from youtube, first search result, "
                                           "you have to be in a voice channel"),
        ]
        self.active_searches = []

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
                voice_client = await author.voice.channel.connect()
                await message.channel.send(
                    embed=embeds.simple_message("Joined",
                                                f"Joined, {author.name} in {author.voice.channel.name}",
                                                self.client.user),
                    delete_after=10
                )
                return voice_client
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

    async def search(self, message):
        search_query = message.content.replace(f"{self.prefix}search ", "")
        search_results = search.youtube_search(search_query)
        custom_id = f"song_search_{int(time.time())}"
        await message.channel.send(embed=embeds.search_results_message("Search",
                                                                       f"Search for: {search_query}",
                                                                       search_results,
                                                                       self.client.user),
                                   components=[
                                      dc.Select(
                                           placeholder="Select Search result",
                                           options=[
                                               dc.SelectOption(label=search_result.title,
                                                               value=search_result.url,
                                                               description=f"({search_result.url}) "
                                                                           f"{search_result.duration}")
                                               for search_result in search_results
                                           ],
                                           custom_id=custom_id,
                                       )
                                  ],
                                   delete_after=120)
        self.active_searches.append(ActiveSearchType(custom_id, message, search_results))

    async def play(self, message, search_result=None):
        if not message.author.voice:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Author not in any voice channel",
                                            self.client.user),
                delete_after=10
            )
            return
        else:
            active_voice_clients = list(filter(lambda voice_client:
                                               voice_client.channel == message.author.voice.channel,
                                               self.client.voice_clients))
        if len(active_voice_clients) == 1:
            active_voice_client = active_voice_clients[0]
        else:
            active_voice_client = await self.join(message)
        if not search_result:
            search_query = message.content.replace(f"{self.prefix}search ", "")
            search_result = search.simple_search(search_query)
        song = self.client.storage_manager.request_song(search_result)  # TODO show download progress
        source = await discord.FFmpegOpusAudio.from_probe(song.filename,
                                                          # pipe=True,  # TODO do volume over pipe
                                                          options=f'-vf "volume=1.0, loudnorm"',  # TODO get volume
                                                          method='fallback')
        await message.channel.send(
            embed=embeds.search_results_message("Playing",
                                                f"",
                                                [song],
                                                self.client.user),
            delete_after=30  # NOTE maybe after song duration
        )
        if active_voice_client.is_playing():
            active_voice_client.stop()
        active_voice_client.play(source)  # TODO add to list of playing and callback
        return


class CommandType:
    def __init__(self, command, function, description):
        self.command = command
        self.function = function
        self.description = description


class ActiveSearchType:
    def __init__(self, custom_id, message, search_elements):
        self.id = custom_id
        self.message = message
        self.search_elements = search_elements
