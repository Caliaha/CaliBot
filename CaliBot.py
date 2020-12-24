import aiohttp
import config
import discord
from discord.ext import commands
import logging
import os
import sys
import time

intents = discord.Intents.default()
intents.members = True

# Authorize bot link: https://discordapp.com/oauth2/authorize?&client_id=362335676248621068&scope=bot&permissions=271932480

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description='CaliBot', intents=intents)
bot.startTime = time.time()
bot.NAME = config.NAME
bot.ADMINACCOUNT = config.ADMINACCOUNT
bot.APIKEY_OSU = config.APIKEY_OSU
bot.APIKEY_WOW = config.APIKEY_WOW
bot.WOWAPI_CLIENTID = config.WOWAPI_CLIENTID
bot.WOWAPI_CLIENTSECRET = config.WOWAPI_CLIENTSECRET
bot.MYSQL_HOST = config.MYSQL_HOST
bot.MYSQL_DB = config.MYSQL_DB
bot.MYSQL_USER = config.MYSQL_USER
bot.MYSQL_PASSWORD = config.MYSQL_PASSWORD
bot.TTS_PROGRAM = config.TTS_PROGRAM
bot.TTS_FILE = config.TTS_FILE
bot.DEFAULT_EMBED_COLOR = '444580'
bot.USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0'
bot.COG_DIRECTORY = config.COG_DIRECTORY
bot.COG_DIRECTORY_DISABLED = config.COG_DIRECTORY_DISABLED

bot.SESSION = aiohttp.ClientSession(loop=bot.loop)

bot.log = logging.getLogger('CaliBot')
bot.log.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('CaliBot.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
bot.log.addHandler(fh)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
bot.log.addHandler(ch)

@bot.event
async def on_ready():
	print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))

if __name__ == "__main__":
	for filename in os.listdir(f'./{bot.COG_DIRECTORY}'):
		if not os.path.isfile(f'./{bot.COG_DIRECTORY}/{filename}'):
			continue
		(file, ext) = os.path.splitext(filename)
		if not ext == '.py':
			continue
		bot.load_extension(f'{bot.COG_DIRECTORY}.{file}')
		print("Loaded cog: ", file)


	bot.run(config.DISCORD_TOKEN)
