import os
import logging
import sys
import asyncio

import discord

from commands import Commands


root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)


class Bot(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.prefix = "?"
        self.commands = None

    async def on_ready(self):
        logging.info(f"{self.user} is ready")
        self.commands = Commands(self.user, self.prefix)

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content == "":
            logging.warning(f"empty message from: {message.author}")
            return

        logging.info(f"{self.user} got message: \"{message.content}\", from: {message.author}")
        if message.content.startswith("?"):
            asyncio.create_task(self.commands.command(message))


if __name__ == '__main__':
    from dotenv import load_dotenv
    bot = Bot()
    load_dotenv()
    bot.run(os.getenv('DISCORD_TOKEN'))

# invite link for bot:
#   https://discord.com/api/oauth2/authorize?client_id=934479656671912036&permissions=36929088&scope=bot
