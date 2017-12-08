import asyncio
import config
import discord
from discord.ext import commands
import sys

# Authorize bot link: ``````````````````````````````````````````````````````

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description='CaliBot')
bot.ADMINACCOUNT = config.ADMINACCOUNT
bot.APIKEY_WOW = config.APIKEY_WOW
bot.MYSQL_DB = config.MYSQL_DB
bot.MYSQL_USER = config.MYSQL_USER
bot.MYSQL_PASSWORD = config.MYSQL_PASSWORD
bot.DEFAULT_EMBED_COLOR = '444580'
bot.USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0'

@bot.command(pass_context=True, hidden=True)
async def restart(ctx):
	if ctx.message.author.id != bot.ADMINACCOUNT:
		return False
	print('Restarting script')
	await bot.close()
	await sys.exit()

@bot.event
async def on_ready():
	print('Logged in as:\n{0} (ID: {0.id})'.format(bot.user))

if __name__ == "__main__":
	#bot.load_extension('utils')
	bot.load_extension('wow')
	#bot.load_extension('color')
	bot.load_extension('tf2')
	bot.load_extension('announce')
	bot.load_extension('wynncraft')
	bot.run(config.DISCORD_TOKEN)