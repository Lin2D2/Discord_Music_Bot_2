import os
import logging
import sys
import asyncio

import discord
import discord_components as dc

from discord.ext import tasks

import music_bot.embeds as embeds

from music_bot.commandhandler import CommandHandler

root = logging.getLogger()
root.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)


# class Bot(discord.Client): # NOTE discord.Client not supports interactions, with buttons and selections
class Bot(dc.ComponentsBot):
    def __init__(self, **options):
        self.prefix = "?"
        super().__init__(self.prefix, **options)
        self.commands_handler = None

    async def on_ready(self):
        logging.info(f"{self.user} is ready")
        self.commands_handler = CommandHandler(self, self.prefix)
        self.check_activity_loop.start()
        self.cache_limit_check_loop.start()

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content == "":
            logging.warning(f"empty message from: {message.author}")
            return

        logging.info(f"{self.user} got message: \"{message.content}\", from: {message.author}")
        if message.content.startswith("?"):
            asyncio.create_task(self.commands_handler.command(message))

    async def on_select_option(self, interaction):
        if interaction.custom_id.find("song_search") != -1:
            current_value = interaction.values[0]
            await interaction.respond(content=f"{current_value} selected")
            active_searches = list(filter(lambda active_search: active_search.id == interaction.custom_id,
                                          self.commands_handler.active_searches))[0]
            search_result_selected = list(filter(lambda search_result: current_value.find(search_result.url) != -1,
                                                 active_searches.search_elements))[0]
            logging.info(f"{search_result_selected.title} selected")

            await self.commands_handler.play(active_searches.message, search_result_selected)
            await active_searches.send_message.delete()
            self.commands_handler.active_searches.pop(
                self.commands_handler.active_searches.index(active_searches)
            )

    async def on_button_click(self, interaction):
        # TODO delete interactions after some time or on next interaction
        if interaction.custom_id.find("play_pause_button") != -1:
            await self.commands_handler.resume_pause(None, interaction)
        elif interaction.custom_id.find("next_button") != -1:
            await self.commands_handler.next(interaction)
        elif interaction.custom_id.find("stop_button") != -1:
            await self.commands_handler.stop_command(None, interaction)
        elif interaction.custom_id.find("volume_up_button") != -1:
            await self.commands_handler.volume_up(None, interaction)
        elif interaction.custom_id.find("volume_down_button") != -1:
            await self.commands_handler.volume_down(None, interaction)
        else:
            await interaction.respond(
                embed=embeds.simple_message("ERROR", "unknown Command", self.user)
            )

    async def before_check_playing_loop(self, voice_client):
        while True:
            await asyncio.sleep(0.5)
            if voice_client.is_playing():
                break
        self.check_playing_loop.start()

    @tasks.loop(seconds=1)
    async def check_playing_loop(self):
        for voice_client in self.voice_clients:
            settings = list(filter(lambda settings_element: settings_element.voice_id == voice_client.session_id,
                                   self.commands_handler.guilds_voice_settings))[0]
            queue_index = settings.queue_index
            queue = settings.queue
            queue_element = queue[queue_index]
            # TODO use next command here somehow
            if voice_client.channel.id == queue_element.voice_client.channel.id:
                if not voice_client.is_paused() and not voice_client.is_playing():
                    logging.info("song ended")
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
                    if len(queue) - 1 > queue_index:
                        queue_index += 1
                        await self.commands_handler.play(None, None, queue_element)
                    else:
                        self.check_playing_loop.stop()
                        index = self.commands_handler.guilds_voice_settings.index(settings)
                        self.commands_handler.guilds_voice_settings[index].queue = []
                        self.commands_handler.guilds_voice_settings[index].queue_index = 0

    @tasks.loop(seconds=10)
    async def check_activity_loop(self):
        for voice_client in self.voice_clients:
            voice_states = voice_client.channel.voice_states
            if len(voice_states) == 1:
                logging.info("leaving do to inactivity")
                await self.commands_handler.stop(voice_client)
                await voice_client.disconnect()

    @tasks.loop(hours=1)
    async def cache_limit_check_loop(self):
        self.commands_handler.search_handler.cache_limit_check()


if __name__ == '__main__':
    from dotenv import load_dotenv

    import music_bot

    load_dotenv()
    music_bot.bot.run(os.getenv('DISCORD_TOKEN'))

# invite link for bot:
#   https://discord.com/api/oauth2/authorize?client_id=934479656671912036&permissions=36929088&scope=bot
