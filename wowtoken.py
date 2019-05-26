import asyncio
import discord
from discord.ext import tasks, commands
import json
from stuff import fetchWebpage

class WoWToken(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.tokenUpdateLoop.start()

	def cog_unload(self):
		self.updateLoop.cancel()

	async def fetchWoWTokenGoldCost(self):
		wow = self.bot.get_cog('WoW')
		accessToken = await wow.validateAccessToken()
		try:
			tokenJSON = json.loads(await fetchWebpage(self, f'https://us.api.blizzard.com/data/wow/token/index?namespace=dynamic-us&locale=en_US&access_token={accessToken}'))
		except Exception as e:
			print("Errow getting wowtoken", e)
			return False
		return int(tokenJSON['price'] / 10000)

	@tasks.loop(minutes=5.0)
	async def tokenUpdateLoop(self):
			cost = await self.fetchWoWTokenGoldCost()
			if cost:
				try:
					print('Set Now Playing to -> WoW Token: {:,}'.format(int(cost)))
					await self.bot.change_presence(activity=discord.Game(name='WoW Token: {:,}'.format(int(cost))))
				except Exception as e:
					print('Error changing presence to wow token price', e)
			else:
				await self.bot.change_presence(activity=discord.Game(name=None))

def setup(bot):
	bot.add_cog(WoWToken(bot))