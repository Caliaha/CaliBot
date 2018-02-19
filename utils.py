from dateutil.relativedelta import relativedelta
from discord.ext import commands
from stuff import isBotOwner, superuser
import sys
import time
import uptime

class utils():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(hidden=True)
	@isBotOwner()
	async def guildlist(self, ctx):
		"""Shows guilds that I am active in"""
		for guild in self.bot.guilds:
			try:
				message += ', ' + guild.name
			except:
				message = 'I am in the following guilds: ' + guild.name
		
		if (not message):
			message = 'I am not in any guilds'
		
		await ctx.send(message)

	@commands.command(hidden=True)
	@isBotOwner()
	@commands.guild_only()
	async def guildowner(self, ctx):
		"""Shows guild owner"""
		await ctx.send(ctx.message.guild.owner)

	@commands.command()
	@superuser()
	async def restart(self, ctx):
		"""Restarts CaliBot, guild owner only"""
		await ctx.message.channel.send('I am restarting. It will take me a moment to reconnect')
		print('Restarting script')
		await self.bot.close()
		await sys.exit()

	@commands.command()
	async def uptime(self, ctx):
		"""Shows how long CaliBot and the computer running it has be online"""
		await ctx.send(self.bot.NAME + ' Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=time.time() - self.bot.startTime)))
		await ctx.send('Computer Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=uptime.uptime())))

	@commands.command()
	@isBotOwner()
	async def load(self, ctx, extension_name : str):
		"""Loads an extension."""
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return
		await ctx.send("{} loaded.".format(extension_name))

	@commands.command()
	@isBotOwner()
	async def unload(self, ctx, extension_name : str):
		"""Unloads an extension."""
		self.bot.unload_extension(extension_name)
		await ctx.send("{} unloaded.".format(extension_name))

	@commands.command()
	@isBotOwner()
	async def reload(self, ctx, extension_name : str):
		"""Unloads and then loads an extension."""
		self.bot.unload_extension(extension_name)
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return
		await ctx.send("{} has been reloaded.".format(extension_name))

def setup(bot):
	bot.add_cog(utils(bot))