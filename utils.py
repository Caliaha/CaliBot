from dateutil.relativedelta import relativedelta
from discord.ext import commands
from stuff import checkPermissions, doThumbs, isBotOwner, superuser
import sys
import time
import uptime

class utils():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
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
	@doThumbs()
	async def guildowner(self, ctx):
		"""Shows guild owner"""
		await ctx.send(ctx.message.guild.owner)
		return True

	@commands.command()
	@checkPermissions('utils')
	async def restart(self, ctx):
		"""Restarts CaliBot, guild owner only"""
		await ctx.message.channel.send('I am restarting. It will take me a moment to reconnect')
		print('Restarting script')
		await self.bot.close()
		await sys.exit()

	@commands.command()
	@doThumbs()
	async def uptime(self, ctx):
		"""Shows how long CaliBot and the computer running it has been online"""
		await ctx.send(self.bot.NAME + ' Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=time.time() - self.bot.startTime)))
		await ctx.send('Computer Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=uptime.uptime())))
		return True

	@commands.command()
	@isBotOwner()
	@doThumbs()
	async def load(self, ctx, extension_name : str):
		"""Loads an extension."""
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return False
		await ctx.send("{} loaded.".format(extension_name))
		return True

	@commands.command()
	@isBotOwner()
	@doThumbs()
	async def unload(self, ctx, extension_name : str):
		"""Unloads an extension."""
		self.bot.unload_extension(extension_name)
		await ctx.send("{} unloaded.".format(extension_name))
		return True

	@commands.command()
	@isBotOwner()
	@doThumbs()
	async def reload(self, ctx, extension_name : str):
		"""Unloads and then loads an extension."""
		self.bot.unload_extension(extension_name)
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return False
		await ctx.send("{} has been reloaded.".format(extension_name))
		return True

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def dm(self, ctx, messageID: int, channelID = None, guildID = None):
		try:
			if (guildID):
				guild = self.bot.get_guild(int(guildID))
				print(guild.name)
			else:
				guild = ctx.guild
			if (channelID):
				channel = guild.get_channel(int(channelID))
				print(channel.name)
			else:
				channel = ctx.channel
			print('Getting message for {} in {}'.format(channel.name, guild.name))
			message = await channel.get_message(messageID)
			await message.delete()
			return True
		except:
			return False

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def eval(self, ctx, *, code : str):
		try:
			await ctx.send(eval(code))
		except Exception as e:
			await ctx.send(e)
			return False
		return True

	@commands.command(hidden=True)
	@superuser()
	@commands.guild_only()
	async def purge(self, ctx, amount: int = 10):
		await ctx.channel.delete_messages(await ctx.channel.history(limit=amount).flatten())

def setup(bot):
	bot.add_cog(utils(bot))