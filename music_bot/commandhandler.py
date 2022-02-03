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
            CommandType("join", self.join_command, "connects to authors voice channel"),
            CommandType("leave", self.leave, "disconnects from current voice channel"),
            CommandType("search", self.search, "searches on youtube for the query after the command, "
                                               "and lets you select out of 8 results"),
            CommandType("play", self.play, "plays query after command from youtube, first search result, "
                                           "you have to be in a voice channel, or resumes if there ist no query"),
            CommandType("next", self.next, "play next song in queue"),
            CommandType("pause", self.resume_pause, "pause current song"),
            CommandType("resume", self.resume_pause, "resume current song"),
            CommandType("stop", self.stop_command, "stop current song, and clears queue"),
            CommandType("volume up", self.volume_up, "global playback volume up"),
            CommandType("volume down", self.volume_down, "global playback volume down"),
        ]
        self.guilds_voice_settings = []
        self.active_searches = []
        self.search_handler = SearchHandler()

    @staticmethod
    async def switch_message_interaction(content=None, embed=None, delete_after=None, message=None, interaction=None):
        if message:
            await message.channel.send(
                content=content,
                embed=embed,
                delete_after=delete_after
            )
        elif interaction:
            await interaction.respond(
                content=content,
                embed=embed,
                # delete_after=delete_after
            )
        else:
            logging.warning("need message or interaction in switch_message_interaction")

    async def check_author_voice(self, author, message=None, interaction=None) -> bool:
        if author.voice:
            return True
        else:
            await self.switch_message_interaction(
                embed=embeds.simple_message("ERROR",
                                            f"author not in any voice channel",
                                            self.client.user),
                delete_after=10,
                message=message,
                interaction=interaction
            )
            return False

    async def get_current_voice(self, voice_channel) -> discord.VoiceClient:
        result_list_guild = list(filter(lambda voice_client: voice_client.guild.name == voice_channel.guild.name,
                                        self.client.voice_clients))
        if len(result_list_guild) == 0:
            return await self.join(voice_channel)
        result_list_channel = list(filter(lambda voice_client: voice_client.channel == voice_channel,
                                          result_list_guild))
        if len(result_list_channel) == 0:
            return await self.join(voice_channel)
        return result_list_channel[0]

    async def command(self, message):
        command = message.content.split(" ")[0].replace(self.prefix, "")
        result_list = list(filter(lambda command_type: command_type.command == command, self.commands))
        if len(result_list) == 1:
            result = result_list[0]
            await result.function(message)
            await message.delete()
        elif len(result_list) == 0:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            f"**Unknown Command:** \"{command}\"",
                                            self.client.user),
                delete_after=10
            )
        else:
            await message.channel.send(
                embed=embeds.simple_message("ERROR",
                                            f"**Multiple Commands matched:** \"{command}\", {result_list}",
                                            self.client.user),
                delete_after=10
            )
            logging.warning(f"found multiple commands: {result_list}")

    async def help(self, message):
        answer = "__**available commands**__:\n"
        for command in self.commands:
            answer += f"> **{self.prefix}{command.command}** :: {command.description}\n"
        await message.channel.send(embed=embeds.simple_message("Help", answer, self.client.user), delete_after=120)
        return

    async def join_command(self, message):
        if await self.check_author_voice(message.author, message, None):
            await self.join(message.author.voice.channel, message, None)

    async def join(self, voice_channel, message=None, interaction=None) -> discord.VoiceClient:
        voice_client = await voice_channel.connect()
        await self.switch_message_interaction(
            embed=embeds.simple_message("Joined",
                                        f"Joined {voice_channel.name}",
                                        self.client.user),
            delete_after=10,
            message=message,
            interaction=interaction
        )
        settings = list(filter(lambda settings_element: settings_element.guild_id == voice_channel.guild.id,
                               self.guilds_voice_settings))
        if len(settings) == 0:
            self.guilds_voice_settings.append(GuildVoiceSettings(voice_channel.guild.id, voice_client.session_id))
        else:
            settings[0].voice_id = voice_client.session_id
        return voice_client

    async def leave(self, message):
        if await self.check_author_voice(message.author, message, None):
            current_voice_client = await self.get_current_voice(message.author.voice.channel)
            await message.channel.send(
                embed=embeds.simple_message("Disconnected",
                                            f"Disconnected from {current_voice_client.channel.name}",
                                            self.client.user),
                delete_after=10
            )
            settings = list(filter(lambda settings_element: settings_element.guild_id == current_voice_client.guild.id,
                                   self.guilds_voice_settings))
            settings[0].voice_id = None
            await current_voice_client.disconnect()
            return

    async def search(self, message):
        if await self.check_author_voice(message.author, message, None):
            search_query = message.content.replace(f"{self.prefix}search ", "")
            await message.channel.send(embed=embeds.simple_message("Searching",
                                                                   "Searching, just a moment",
                                                                   self.client.user),
                                       delete_after=5,
                                       )
            search_results = self.search_handler.youtube_search(search_query)
            custom_id = f"song_search_{int(time.time())}"
            send_message = await message.channel.send(
                embed=embeds.search_results_message("Search",
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
            )
            self.active_searches.append(ActiveSearchType(custom_id, message, send_message, search_results))

    async def play(self, message, search_result=None, current_queue_element=None):
        if current_queue_element:
            search_result = current_queue_element.search_result
            active_voice_client = current_queue_element.voice_client
        else:
            if not search_result:
                search_query = message.content.replace(f"{self.prefix}search", ""). \
                    replace(f"{self.prefix}play", "").strip()
                if len(search_query) == 0:
                    await self.resume_pause(message)
                    return
                search_result = self.search_handler.simple_search(search_query)
            if await self.check_author_voice(message.author, message, None):
                active_voice_client = await self.get_current_voice(message.author.voice.channel)
            else:
                return
        settings = list(filter(lambda settings_element: settings_element.voice_id == active_voice_client.session_id,
                               self.guilds_voice_settings))[0]
        volume = settings.volume
        queue_index = settings.queue_index
        queue = settings.queue
        message_send_return = None
        info_message_send_return = None
        if not active_voice_client.is_playing():
            if not message:
                channel = current_queue_element.channel
            else:
                channel = message.channel
            if len(queue) == 0:
                queued_after = 0
            else:
                queued_after = len(queue) - (queue_index + 1)
            message_send = channel.send(
                embed=embeds.search_results_message(
                    "Playing",
                    f"Songs in queue after: {queued_after}",
                    [search_result],
                    self.client.user),
                components=[
                    dc.Button(label="play/pause",
                              custom_id=f"play_pause_button_{active_voice_client.channel.id}"),
                    dc.Button(label="next",
                              custom_id=f"next_button_{active_voice_client.channel.id}"),
                    dc.Button(label="volume up",
                              custom_id=f"volume_up_button_{active_voice_client.channel.id}"),
                    dc.Button(label="volume down",
                              custom_id=f"volume_down_button_{active_voice_client.channel.id}"),
                    dc.Button(label="stop",
                              custom_id=f"stop_button_{active_voice_client.channel.id}"),
                ],
            )
            source = discord.FFmpegPCMAudio(search_result.play_url)
            active_voice_client.play(discord.PCMVolumeTransformer(source, volume=volume / 100))
            message_send_return = await message_send
            if len(queue) - 1 >= queue_index:
                index = self.guilds_voice_settings.index(settings)
                self.guilds_voice_settings[index].queue.message = message_send_return
        else:
            info_message_send_return = await message.channel.send(
                embed=embeds.search_results_message(
                    f"Queued {search_result.title}",
                    f"Songs in queue after: {len(queue) - queue_index}",
                    [search_result],
                    self.client.user),
            )
            queue[queue_index - 1].info_message = info_message_send_return
        if not current_queue_element:
            logging.info(f"added {search_result.title} to queue")
            index = self.guilds_voice_settings.index(settings)
            self.guilds_voice_settings[index].queue.append(
                QueueType(search_result, message.channel, message_send_return,
                          info_message_send_return, active_voice_client))
        if len(queue) == 1:
            await self.client.before_check_playing_loop(active_voice_client)
        return

    async def next(self, interaction=None):
        settings = list(filter(lambda settings_element: settings_element.guild_id == interaction.guild.id,
                               self.guilds_voice_settings))[0]
        queue_index = settings.queue_index
        queue = settings.queue
        if len(queue) - 1 > queue_index:
            queue_element = queue[queue_index]
            queue_element.voice_client.stop()
            if queue_element.message is not None:
                try:
                    await queue_element.message.delete()
                except discord.errors.NotFound:
                    pass
            if queue_element.info_message is not None:
                try:
                    await queue_element.info_message.delete()
                except discord.errors.NotFound:
                    pass
            queue_index += 1
            if queue[queue_index].info_message is not None:
                try:
                    await queue[queue_index].info_message.delete()
                except discord.errors.NotFound:
                    pass
            await self.play(None, None, queue[queue_index])
            if interaction:
                await interaction.respond(
                    embed=embeds.simple_message(
                        f"Next",
                        f"",
                        self.client.user),
                )
        else:
            queue_element = queue[queue_index]
            await self.switch_message_interaction(
                embed=embeds.simple_message(
                    f"ERROR",
                    f"No more Songs in Queue",
                    self.client.user),
                delete_after=10,
                message=queue_element,
                interaction=interaction
            )

    async def resume_pause(self, message, interaction=None):
        if not await self.check_author_voice(message.author, message, interaction):
            return
        else:
            active_voice_client = await self.get_current_voice(message.author.voice.channel)
        if active_voice_client.is_paused():
            active_voice_client.resume()
            await self.switch_message_interaction(
                embed=embeds.simple_message("Resumed",
                                            "",
                                            self.client.user),
                delete_after=10,
                message=message,
                interaction=interaction
            )
        elif active_voice_client.is_playing():
            active_voice_client.pause()
            await self.switch_message_interaction(
                embed=embeds.simple_message("Paused",
                                            "",
                                            self.client.user),
                delete_after=10,
                message=message,
                interaction=interaction
            )
        else:
            await self.switch_message_interaction(
                embed=embeds.simple_message("ERROR",
                                            "Nothing to resume or pause",
                                            self.client.user),
                delete_after=10,
                message=message,
                interaction=interaction
            )

    async def stop_command(self, message, interaction=None):
        if not await self.check_author_voice(message.author if message else interaction.author, message, interaction):
            return
        else:
            active_voice_client = await self.get_current_voice(message.author.voice.channel
                                                               if message else interaction.author.voice.channel)
        await self.stop(active_voice_client, message, interaction)

    async def stop(self, voice_client, message=None, interaction=None):
        if voice_client.is_playing() or voice_client.is_paused():
            settings = list(filter(lambda settings_element: settings_element.voice_id == voice_client.session_id,
                                   self.guilds_voice_settings))[0]
            queue_index = settings.queue_index
            queue = settings.queue
            self.client.check_playing_loop.stop()
            queue_element = queue[queue_index]
            queue_element.voice_client.stop()
            if queue_element.message is not None:
                try:
                    await queue_element.message.delete()
                except discord.errors.NotFound:
                    pass
            if queue_element.info_message is not None:
                try:
                    await queue_element.info_message.delete()
                except discord.errors.NotFound:
                    pass
            index = self.guilds_voice_settings.index(settings)
            self.guilds_voice_settings[index].queue = []
            self.guilds_voice_settings[index].queue_index = 0
            await self.switch_message_interaction(
                embed=embeds.simple_message("Stopped",
                                            "",
                                            self.client.user),
                delete_after=10,
                message=message,
                interaction=interaction
            )
        else:
            await self.switch_message_interaction(
                embed=embeds.simple_message("ERROR",
                                            "Nothing to stop",
                                            self.client.user),
                delete_after=10,
                message=message,
                interaction=interaction
            )

    async def volume_set(self, message, interaction=None, value=0, status_message="Volume set"):
        if message:
            if not await self.check_author_voice(message.author, message, None):
                return
            else:
                active_voice_client = await self.get_current_voice(message.author.voice.channel)
        else:  # NOTE interaction
            if not await self.check_author_voice(interaction.author, None, interaction):
                return
            else:
                active_voice_client = await self.get_current_voice(interaction.author.voice.channel)
        settings = list(filter(lambda settings_element: settings_element.voice_id == active_voice_client.session_id,
                               self.guilds_voice_settings))[0]
        index = self.guilds_voice_settings.index(settings)
        self.guilds_voice_settings[index].volume += value
        volume = settings.volume
        active_voice_client.source.volume = volume / 100
        await self.switch_message_interaction(
            embed=embeds.simple_message(status_message,
                                        f"Volume: {int(volume)}%",
                                        self.client.user),
            delete_after=10,
            message=message,
            interaction=interaction
        )

    async def volume_up(self, message, interaction=None):
        await self.volume_set(message, interaction, 10, "Volume up")
        return

    async def volume_down(self, message, interaction=None):
        await self.volume_set(message, interaction, -10, "Volume down")
        return


class CommandType:
    def __init__(self, command, function, description):
        self.command = command
        self.function = function
        self.description = description


class ActiveSearchType:
    def __init__(self, custom_id, message, send_message, search_elements):
        self.id = custom_id
        self.message = message
        self.send_message = send_message
        self.search_elements = search_elements


class QueueType:
    def __init__(self, search_result, channel, message, info_message, voice_client):
        self.search_result = search_result
        self.channel = channel
        self.message = message
        self.info_message = info_message
        self.voice_client = voice_client


class GuildVoiceSettings:
    def __init__(self, guild_id, voice_id):
        self.guild_id = guild_id
        self.voice_id = voice_id
        self.volume = 30
        self.queue_index = 0
        self.queue = []
