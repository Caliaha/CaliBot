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

def setup(bot):
	bot.add_cog(utils(bot))