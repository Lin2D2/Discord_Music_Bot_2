import os

from dotenv import load_dotenv

import music_bot

if __name__ == '__main__':
    load_dotenv()
    music_bot.bot.run(os.getenv('DISCORD_TOKEN'))
