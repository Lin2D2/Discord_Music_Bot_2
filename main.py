import os

from dotenv import load_dotenv

from music_bot.bot import Bot

if __name__ == '__main__':
    bot = Bot()
    load_dotenv()
    bot.run(os.getenv('DISCORD_TOKEN'))
