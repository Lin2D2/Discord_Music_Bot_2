import os
import logging
import sys
import asyncio

# import discord
import discord_components as dc

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
            # TODO play song

    async def on_button_click(self, interaction):
        await interaction.respond(content="Button Clicked")


if __name__ == '__main__':
    from dotenv import load_dotenv
    bot = Bot()
    load_dotenv()
    bot.run(os.getenv('DISCORD_TOKEN'))

# invite link for bot:
#   https://discord.com/api/oauth2/authorize?client_id=934479656671912036&permissions=36929088&scope=bot
