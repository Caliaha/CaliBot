import aiohttp
import asyncio
import discord
import re
from stuff import fetchWebpage

class WoWToken():
	def __init__(self, bot):
		self.bot = bot
		self.bot.loop.create_task(self.background_lookup())

	async def fetchWoWTokenGoldCost(self):
		tokenpattern = re.compile('\{"NA":\{"timestamp":(.*?)."raw":\{"buy":(.*?)."24min":(.*?),"24max":(.*?)."timeToSell":')
		try:
			tokenjson = await fetchWebpage(self, 'https://data.wowtoken.info/snapshot.json')
		except:
			print("Error fetching token price")
			return False
		tokenmatch = tokenpattern.match(tokenjson)
		if tokenmatch is not None:
			return tokenmatch.group(2)
		else:
			return False

	async def background_lookup(self):
		await self.bot.wait_until_ready()
		while not self.bot.is_closed():
			try:
				token = await self.fetchWoWTokenGoldCost()
				if token:
					try:
						print('Set Now Playing to -> WoW Token: {:,}'.format(int(token)))
						await self.bot.change_presence(activity=discord.Game(name='WoW Token: {:,}'.format(int(token))))
					except Exception as e:
						print('Error changing presence to wow token price', e)
				else:
					await self.bot.change_presence(activity=discord.Game(name=None))
			except:
				print('Unable to set Playing Status to wow token price')
			await asyncio.sleep(300)

def setup(bot):
	bot.add_cog(WoWToken(bot))