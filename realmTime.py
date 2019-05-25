import asyncio
from datetime import datetime
import discord
from discord.ext import commands
import json
from pytz import timezone
from stuff import checkPermissions, deleteMessage, doThumbs, isBotOwner, superuser, fetchWebpage

class realmTime(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.bot.loop.create_task(self.background_lookup())
		self.realmTZCache = { }
		self.realmNameCache = { }

	async def background_lookup(self):
		activeChannels = { 'cairne': 581932082192711697 }
		await self.bot.wait_until_ready()
		while not self.bot.is_closed():
			for realmName, categoryID in activeChannels.items():
				if realmName in self.realmNameCache:
					realmName = self.realmNameCache[realmName]
				category = self.bot.get_channel(categoryID)
				if realmName not in self.realmTZCache:
					realm, tz = await self.fetchRealmTZData(realmName.lower())
					self.realmNameCache[realmName] = realm
					self.realmTZCache[realm] = tz
					realmName = realm

				currentTime = datetime.now(timezone(self.realmTZCache[realmName])).strftime('%I:%M %p')
				if category.name != f'{realmName}: {currentTime}':
					if category.permissions_for(category.guild.me).manage_channels:
						await category.edit(name=f'{realmName}: {currentTime}')
						print(f'Updated time for {category.guild}')
					else:
						print('I don\'t have the proper permissions for that')
				
			await asyncio.sleep(3)
	
	async def fetchRealmTZData(self, realm):
		wow = self.bot.get_cog('WoW')
		accessToken = await wow.validateAccessToken()
		
		realmJSON = await fetchWebpage(self, f'https://us.api.blizzard.com/data/wow/realm/{realm}?namespace=dynamic-us&locale=en_US&access_token={accessToken}')
		realmData = json.loads(realmJSON)
		print('Beep', accessToken)
		print(f'Added {realmData["name"]} with tz {realmData["timezone"]} to cache')
		return realmData['name'], realmData['timezone']

def setup(bot):
	bot.add_cog(realmTime(bot))