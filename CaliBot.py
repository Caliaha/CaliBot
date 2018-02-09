import config
import discord
from discord.ext import commands
from stuff import isBotOwner
import sys
import time

# Authorize bot link: https://discordapp.com/oauth2/authorize?&client_id=362335676248621068&scope=bot&permissions=271932480

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description='CaliBot')
bot.startTime = time.time()
bot.NAME = config.NAME
bot.ADMINACCOUNT = config.ADMINACCOUNT
bot.APIKEY_WOW = config.APIKEY_WOW
bot.MYSQL_DB = config.MYSQL_DB
bot.MYSQL_USER = config.MYSQL_USER
bot.MYSQL_PASSWORD = config.MYSQL_PASSWORD
bot.TTS_PROGRAM = config.TTS_PROGRAM
bot.TTS_FILE = config.TTS_FILE
bot.DEFAULT_EMBED_COLOR = '444580'
bot.USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0'

startup_extensions = [ 'announce', 'color', 'hots', 'permissions', 'settings', 'tf2', 'utils', 'wow', 'wowtoken' ]

@bot.event
async def on_ready():
	print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))

if __name__ == "__main__":
	for extension in startup_extensions:
		try:
			bot.load_extension(extension)
		except Exception as e:
			exc = '{}: {}'.format(type(e).__name__, e)
			print('Failed to load extension {}\n{}'.format(extension, exc))

	bot.run(config.DISCORD_TOKEN_TEST)