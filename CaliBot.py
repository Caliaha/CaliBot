import aiohttp
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
bot.APIKEY_OSU = config.APIKEY_OSU
bot.APIKEY_WOW = config.APIKEY_WOW
bot.MYSQL_HOST = config.MYSQL_HOST
bot.MYSQL_DB = config.MYSQL_DB
bot.MYSQL_USER = config.MYSQL_USER
bot.MYSQL_PASSWORD = config.MYSQL_PASSWORD
bot.TTS_PROGRAM = config.TTS_PROGRAM
bot.TTS_FILE = config.TTS_FILE
bot.DEFAULT_EMBED_COLOR = '444580'
bot.USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0'

bot.SESSION = aiohttp.ClientSession(loop=bot.loop)

startup_extensions = [ 'announce', 'color', 'hots', 'osu', 'permissions', 'guild_management', 'settings', 'tf2', 'utils', 'wow', 'wowtoken' ]

@bot.event
async def on_ready():
	print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))

#@bot.event
#async def on_command_error(ctx, error):
#	print('Beep')
#	print(ctx.message.author.name)
#	ctx.send('Beep')

if __name__ == "__main__":
	#bot.load_extension('announce')
	for extension in startup_extensions:
		#try:
		bot.load_extension(extension)
		print("Loaded cog: ", extension)
		#except Exception as e:
		#	exc = '{}: {}'.format(type(e).__name__, e)
		#	print('Failed to load extension {}\n{}'.format(extension, exc))
		#	print(e)

	bot.run(config.DISCORD_TOKEN_TEST)