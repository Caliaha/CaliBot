from discord.ext import commands
from stuff import isBotOwner

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
	async def serverowner(self, ctx):
		await self.bot.send_message(ctx.message.channel, ctx.message.server.owner)

def setup(bot):
	bot.add_cog(utils(bot))