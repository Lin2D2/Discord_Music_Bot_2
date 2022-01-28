import logging
import time

import discord
import discord_components as dc

import music_bot.embeds as embeds

from music_bot.search import SearchHandler


class CommandHandler:
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
                                           "you have to be in a voice channel, or resumes if there ist not query"),
            CommandType("pause", self.resume_pause, "pause current song"),
            CommandType("resume", self.resume_pause, "resume current song"),
            CommandType("stop", self.stop, "stop current song"),
        ]
        self.active_searches = []
        self.search_handler = SearchHandler()

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
        if not message.author.voice:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Author in any voice channels",
                                            self.client.user),
                delete_after=10
            )
            return
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

    async def leave(self, message):
        # NOTE filter for current author
        if not message.author.voice:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Author in any voice channels",
                                            self.client.user),
                delete_after=10
            )
            return
        result_list = list(filter(lambda voice_client: voice_client.channel == message.author.voice.channel,
                                  self.client.voice_clients))
        # NOTE filter for current server
        result_list = list(filter(lambda voice_client: voice_client.guild.name == message.guild.name, result_list))
        if len(result_list) == 0:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Bot not in any voice channels",
                                            self.client.user),
                delete_after=10
            )
            return
        result = result_list[0]
        if not result:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Bot not in any voice channels",
                                            self.client.user),
                delete_after=10
            )
            return
        await result.disconnect()
        await message.channel.send(
            embed=embeds.simple_message("Disconnected",
                                        f"Disconnected from {result.channel.name}",
                                        self.client.user),
            delete_after=10
        )
        return

    async def search(self, message):
        search_query = message.content.replace(f"{self.prefix}search ", "")
        await  message.channel.send(embed=embeds.simple_message("Searching",
                                                                "Searching, just a moment",
                                                                self.client.user),
                                    delete_after=5,
                                    )
        search_results = self.search_handler.youtube_search(search_query)
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
                                   # delete_after=120  # TODO do this different and delete from self.active_searches
                                   # TODO delete after interaction
                                   )
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
            active_voice_client = self.join(message)
        if not search_result:
            search_query = message.content.replace(f"{self.prefix}search", "").replace(f"{self.prefix}play", "").strip()
            if len(search_query) == 0:
                await self.resume_pause(message)
                return
            search_result = self.search_handler.simple_search(search_query)

        source = discord.FFmpegOpusAudio.from_probe(search_result.play_url, method='fallback')
        if len(active_voice_clients) == 0:
            active_voice_client = await active_voice_client
        message_send = message.channel.send(
            embed=embeds.search_results_message(
                "Playing",
                f"",
                [search_result],
                self.client.user),
            components=[
                dc.Button(label="play/pause",
                          custom_id=f"play_pause_button_{active_voice_client.channel.id}"),

                dc.Button(label="stop",
                          custom_id=f"stop_button_{active_voice_client.channel.id}"),
            ],
            # TODO delete after song is done
        )
        if active_voice_client.is_playing():
            active_voice_client.stop()
        active_voice_client.play(await source)
        await message_send
        return

    async def resume_pause(self, message, interaction=None):
        if message:
            active_voice_clients = list(filter(lambda voice_client:
                                               voice_client.channel == message.author.voice.channel,
                                               self.client.voice_clients))
            if len(active_voice_clients) == 0:
                await message.channel.send(
                    embed=embeds.simple_message("ERROR",
                                                "Author not in any voice channel",
                                                self.client.user),
                    delete_after=10
                )
                return
        elif interaction:
            active_voice_clients = list(filter(lambda voice_client: interaction.custom_id.
                                               find(str(voice_client.channel.id)) != -1,
                                               self.client.voice_clients))
            if len(active_voice_clients) == 0:
                await interaction.respond(
                    embed=embeds.simple_message("ERROR",
                                                "Author not in any voice channel",
                                                self.client.user),
                )
                return
        else:
            logging.warning("unexpected Event in resume")
            return
        if active_voice_clients[0].is_paused():
            active_voice_clients[0].resume()
            if message:
                await message.channel.send(
                    embed=embeds.simple_message("Resumed",
                                                "",
                                                self.client.user),
                )
                return
            if interaction:
                await interaction.respond(
                    embed=embeds.simple_message("Resumed",
                                                "",
                                                self.client.user),
                )
                return
        if active_voice_clients[0].is_playing():
            active_voice_clients[0].pause()
            if message:
                await message.channel.send(
                    embed=embeds.simple_message("Paused",
                                                "",
                                                self.client.user),
                    delete_after=10
                )
                return
            if interaction:
                await interaction.respond(
                    embed=embeds.simple_message("Paused",
                                                "",
                                                self.client.user),
                )
                return
        if message:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Nothing to resume or pause",
                                            self.client.user),
                delete_after=10
            )
            return
        if interaction:
            await interaction.respond(
                embed=embeds.simple_message("ERROR",
                                            "Nothing to resume or pause",
                                            self.client.user),
            )
            return
        return

    async def stop(self, message, interaction=None):
        if message:
            active_voice_clients = list(
                filter(lambda voice_client: voice_client.channel == message.author.voice.channel,
                       self.client.voice_clients))
            if len(active_voice_clients) == 0:
                await message.channel.send(
                    embed=embeds.simple_message("ERROR",
                                                "Author not in any voice channel",
                                                self.client.user),
                    delete_after=10
                )
                return
        elif interaction:
            active_voice_clients = list(filter(lambda voice_client: interaction.custom_id.
                                               find(str(voice_client.channel.id)) != -1,
                                               self.client.voice_clients))
            if len(active_voice_clients) == 0:
                await interaction.respond(
                    embed=embeds.simple_message("ERROR",
                                                "Author not in any voice channel",
                                                self.client.user),
                )
                return
        else:
            logging.warning("unexpected Event in stop")
            return
        if active_voice_clients[0].is_playing() or active_voice_clients[0].is_paused():
            active_voice_clients[0].stop()
            if message:
                await message.channel.send(
                    embed=embeds.simple_message("Stopped",
                                                "",
                                                self.client.user),
                    delete_after=10
                )
                return
            if interaction:
                await interaction.respond(
                    embed=embeds.simple_message("Stopped",
                                                "",
                                                self.client.user),
                )
                return
        if message:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            "Nothing to stop",
                                            self.client.user),
                delete_after=10
            )
            return
        if interaction:
            await interaction.respond(
                embed=embeds.simple_message("ERROR",
                                            "Nothing to stop",
                                            self.client.user),
            )
            return
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
