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


stop_whitelist = [
    "Grobhack#7188"
]


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
        if interaction.custom_id.find("play_pause_button") != -1:
            await self.commands_handler.resume_pause(None, interaction)
            return
        if interaction.custom_id.find("stop_button") != -1:
            if f"{interaction.author.name}#{interaction.author.discriminator}" not in stop_whitelist:
                await interaction.respond(
                    embed=embeds.simple_message("Not Allowed", "Not Allowed to stop, you can still pause", self.user)
                )
                return
            await self.commands_handler.stop(None, interaction)
            return
        await interaction.respond(
            embed=embeds.simple_message("ERROR", "unknown Command", self.user)
        )
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
