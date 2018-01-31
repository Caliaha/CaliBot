import aiohttp
import asyncio
import discord
import re

class WoWToken():
	def __init__(self, bot):
		self.bot = bot
		self.bot.loop.create_task(self.background_lookup())

	async def fetchWebpage(self, url):
		attempts = 0
		while attempts < 5:
			try:
				async with aiohttp.get(url) as r:
					if r.status == 200:
						return await r.text()
					elif r.status == 404:
						print("Page was 404")
						return False
					else:
						raise
			except:
				print("Failed to grab webpage", url, attempts)
				attempts += 1
		raise ValueError('Unable to fetch url')

	async def fetchWoWTokenGoldCost(self):
		tokenpattern = re.compile('\{"NA":\{"timestamp":(.*?)."raw":\{"buy":(.*?)."24min":(.*?),"24max":(.*?)."timeToSell":')
		try:
			tokenjson = await self.fetchWebpage('https://data.wowtoken.info/snapshot.json')
		except:
			return False
		tokenmatch = tokenpattern.match(tokenjson)
		if tokenmatch is not None:
			return tokenmatch.group(2)
		else:
			return False

	async def background_lookup(self):
		await self.bot.wait_until_ready()
		while not self.bot.is_closed:
			try:
				token = await self.fetchWoWTokenGoldCost()
				if token:
					print('Set Now Playing to -> WoW Token: {:,}'.format(int(token)))
					await self.bot.change_presence(game=discord.Game(name='WoW Token: {:,}'.format(int(token))))
				else:
					await self.bot.change_presence(game=discord.Game(name=None))
			except:
				print('Unable to set Playing Status to wow token price')
			await asyncio.sleep(300)

def setup(bot):
	bot.add_cog(WoWToken(bot))