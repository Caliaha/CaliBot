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
		
		await self.bot.send_message(ctx.message.channel, message)

	@commands.command(pass_context=True, hidden=True)
	@isBotOwner()
	@no_pm()
	async def serverowner(self, ctx):
		await self.bot.send_message(ctx.message.channel, ctx.message.server.owner)

	@commands.command(pass_context=True, hidden=True)
	@superuser()
	async def restart(self, ctx):
		await self.bot.send_message(ctx.message.channel, 'I am restarting. It will take me a moment to reconnect')
		print('Restarting script')
		await self.bot.close()
		await sys.exit()

	@commands.command(pass_context=True)
	async def uptime(self, ctx):
		await self.bot.send_message(ctx.message.channel, self.bot.NAME + ' Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=time.time() - self.bot.startTime)))
		await self.bot.send_message(ctx.message.channel, 'Computer Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=uptime.uptime())))

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