import asyncio
from datetime import datetime
import discord
from discord.ext import tasks, commands
import json
from pytz import timezone
from stuff import checkPermissions, deleteMessage, doThumbs, isBotOwner, superuser, fetchWebpage

class realmTime(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.lastPresence = ''
		self.realmTZCache = { }
		self.realmNameCache = { }
		self.updateLoop.start()

	def cog_unload(self):
		self.updateLoop.cancel()

	@tasks.loop(seconds=3.0)
	async def updateLoop(self):
		#activeThings = [ [ 'cairne', 0, 'status'  ], [ 'tichondrius', 581932082192711697, 'category' ], [ 'alterac-mountains', 493512483273965568, 'category' ], [ 'perenolde', 493512483273965568, 'topic' ] ]
		activeThings = [ [ 'cairne', 0, 'status' ], [ 'cairne', 254746234466729987, 'topic' ] ]
		#activeChannels = { 'cairne': 581932082192711697 }
		#for realmName, categoryID in activeChannels.items():
		for thing in activeThings:
			realm = thing[0]
			id = thing[1]
			type = thing[2]

			if realm in self.realmNameCache:
				realm = self.realmNameCache[realm]
			currentTime = await self.fetchRealmTime(realm)
			
			if type == "status":
				if self.lastPresence != f'{realm}: {currentTime}':
					self.lastPresence = f'{realm}: {currentTime}'
					try:
						await self.bot.change_presence(activity=discord.Game(name=self.lastPresence))
					except:
						print('Failed to update status')
					
			if type == 'topic':
				category = self.bot.get_channel(id)
				if category.topic != f'{realm}: {currentTime}':
						if category.permissions_for(category.guild.me).manage_channels:
							try:
								await category.edit(topic=f'{realm}: {currentTime}')
							except:
								print('Failed to update topic', category.name)
						else:
							print('I don\'t have the proper permissions for that')
			
			if type == 'category' or type == 'channel':
				category = self.bot.get_channel(id)
				if category.name != f'{realm}: {currentTime}':
						if category.permissions_for(category.guild.me).manage_channels:
							try:
								await category.edit(name=f'{realm}: {currentTime}')
							except:
								print('Failed to update channel', category.name)
						else:
							print('I don\'t have the proper permissions for that')

	@updateLoop.before_loop
	async def before_updateLoop(self):
		await self.bot.wait_until_ready()
	
	async def fetchRealmTZData(self, realm):
		wow = self.bot.get_cog('WoW')
		accessToken = await wow.validateAccessToken()
		
		realmJSON = await fetchWebpage(self, f'https://us.api.blizzard.com/data/wow/realm/{realm}?namespace=dynamic-us&locale=en_US&access_token={accessToken}')
		if not realmJSON:
			return False, False
		realmData = json.loads(realmJSON)
		print('Beep', accessToken)
		print(f'Added {realmData["name"]} with tz {realmData["timezone"]} to cache')
		return realmData['name'], realmData['timezone']

	async def fetchRealmTime(self, realm):
			if realm not in self.realmTZCache:
				realName, tz = await self.fetchRealmTZData(realm.lower())
				if not realName:
					return 'Err'
				self.realmNameCache[realm] = realName
				self.realmTZCache[realName] = tz
				realm = realName

			return datetime.now(timezone(self.realmTZCache[realm])).strftime('%I:%M %p')

	@commands.command()
	@doThumbs()
	async def realmtime(self, ctx, realm):
		if realm in self.realmNameCache:
				realm = self.realmNameCache[realm]
		currentTime = await self.fetchRealmTime(realm)
		try:
			await ctx.send(f'It is currently {currentTime} on {realm}.')
		except:
			return False
		return True

def setup(bot):
	bot.add_cog(realmTime(bot))