import asyncio
import discord
from discord.ext import tasks, commands
import random

class NowPlaying(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.statusList = [ 'This space intentionally left blank', 'If you can read this you are driving too close', 'Lefty-loosy, Righty-tighty', 'No, that\'s my horse' ]
		self.updateLoop.start()

	def cog_unload(self):
		self.updateLoop.cancel()

	@tasks.loop(minutes=30)
	async def updateLoop(self):
			status = random.choice(self.statusList)
			try:
				await self.bot.change_presence(activity=discord.Game(name=f'{status}'))
			except Exception as e:
				print('Error changing presence:', e)

	@updateLoop.before_loop
	async def before_updateLoop(self):
		await self.bot.wait_until_ready()

def setup(bot):
	bot.add_cog(NowPlaying(bot))