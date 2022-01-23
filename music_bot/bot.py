import os
import logging
import sys
import asyncio

# import discord
import discord_components as dc

from discord.ext import tasks

import embeds

from commands import Commands

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
        self.commands_handler = Commands(self, self.prefix)
        # self.check_activity_loop.start()

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

    async def on_button_click(self, interaction):
        # TODO join pause and resume button
        if interaction.custom_id.find("pause_button") != -1:
            active_voice_clients = list(filter(lambda voice_client:
                                               str(voice_client.channel.id) == interaction.custom_id.
                                               replace("pause_button_", ""),
                                               self.voice_clients))
            if len(active_voice_clients) == 0:
                await interaction.respond(
                    embed=embeds.simple_message("ERROR",
                                                "Author not in any voice channel",
                                                self.user),
                )
                return
            active_voice_clients[0].pause()
            await interaction.respond(
                embed=embeds.simple_message("Paused",
                                            "",
                                            self.user),
            )
            return
        if interaction.custom_id.find("resume_button") != -1:
            active_voice_clients = list(
                filter(lambda voice_client: str(voice_client.channel.id) == interaction.custom_id.
                       replace("resume_button_", ""),
                       self.voice_clients))
            if len(active_voice_clients) == 0:
                await interaction.respond(
                    embed=embeds.simple_message("ERROR",
                                                "Author not in any voice channel",
                                                self.user),
                )
                return
            active_voice_clients[0].resume()
            await interaction.respond(
                embed=embeds.simple_message("Resumed",
                                            "",
                                            self.user),
            )
            return
        return

    @tasks.loop(seconds=10)
    async def check_activity_loop(self):
        # TODO bug leaves when there are others in channel
        for voice_client in self.voice_clients:
            channel_members = voice_client.channel.members
            print(channel_members)
            if len(channel_members) == 1:
                logging.info("leaving do to inactivity")
                await voice_client.disconnect()


if __name__ == '__main__':
    from dotenv import load_dotenv

    bot = Bot()
    load_dotenv()
    bot.run(os.getenv('DISCORD_TOKEN'))

# invite link for bot:
#   https://discord.com/api/oauth2/authorize?client_id=934479656671912036&permissions=36929088&scope=bot
