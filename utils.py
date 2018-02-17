from dateutil.relativedelta import relativedelta
from discord.ext import commands
from stuff import isBotOwner, no_pm, superuser
import sys
import time
import uptime

class utils():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True, hidden=True)
	@isBotOwner()
	async def serverlist(self, ctx):
		for server in self.bot.servers:
			try:
				message += ', ' + server.name
			except:
				message = server.name
		
		if (not message):
			message = 'I am not in any guilds'
		
		await ctx.message.channel.send(message)

	@commands.command(pass_context=True, hidden=True)
	@isBotOwner()
	@no_pm()
	async def serverowner(self, ctx):
		await ctx.message.channel.send(ctx.message.server.owner)

	@commands.command(pass_context=True, hidden=True)
	@superuser()
	async def restart(self, ctx):
		await ctx.message.channel.send('I am restarting. It will take me a moment to reconnect')
		print('Restarting script')
		await self.bot.close()
		await sys.exit()

	@commands.command(pass_context=True)
	async def uptime(self, ctx):
		await ctx.message.channel.send(self.bot.NAME + ' Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=time.time() - self.bot.startTime)))
		await ctx.message.channel.send('Computer Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=uptime.uptime())))

	@commands.command(pass_context=True)
	@isBotOwner()
	async def load(self, ctx, extension_name : str):
		"""Loads an extension."""
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await self.bot.say("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return
		await self.bot.say("{} loaded.".format(extension_name))

	@commands.command(pass_context=True)
	@isBotOwner()
	async def unload(self, ctx, extension_name : str):
		"""Unloads an extension."""
		self.bot.unload_extension(extension_name)
		await self.bot.say("{} unloaded.".format(extension_name))

	@commands.command(pass_context=True)
	@isBotOwner()
	async def reload(self, ctx, extension_name : str):
		"""Unloads and the loads an extension."""
		self.bot.unload_extension(extension_name)
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await self.bot.say("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return
		await self.bot.say("{} has been reloaded.".format(extension_name))

def setup(bot):
	bot.add_cog(utils(bot))