import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import json
import pymysql.cursors
import re
from stuff import BoxIt, deleteMessage, doThumbs, superuser, fetchWebpage, postWebdata
import time
import urllib.parse
import urllib.request

class Diablo3(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.lastLookup = {}
		self.accessToken = None
		self.accessTokenExpiration = None
		self.d3images = {}		
		self.d3images['barbarian_female'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/barbarian_female.png"
		self.d3images['barbarian_male'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/barbarian_male.png"
		self.d3images['crusader_female'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/x1_crusader_female.png"
		self.d3images['crusader_male'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/x1_crusader_male.png"
		self.d3images['demonhunter_female'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/demonhunter_female.png"
		self.d3images['monk_female'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/monk_female.png"
		self.d3images['monk_male'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/monk_male.png"
		self.d3images['necromancer_female'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/p6_necro_female.png"
		self.d3images['witch-doctor_female'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/witchdoctor_female.png"
		self.d3images['witch-doctor_male'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/witchdoctor_male.png"
		self.d3images['wizard_female'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/wizard_female.png"
		self.d3images['wizard_male'] = "https://blzmedia-a.akamaihd.net/d3/icons/portraits/100/wizard_male.png"
		self.d3images['logo'] = "https://blzmedia-a.akamaihd.net/battle.net/logos/og-d3.png"

	async def getAccessToken(self):
		auth = aiohttp.BasicAuth(login=self.bot.WOWAPI_CLIENTID, password=self.bot.WOWAPI_CLIENTSECRET)
		data = { 'grant_type': 'client_credentials' }

		async with aiohttp.ClientSession(auth=auth) as session:
			async with session.post('https://us.battle.net/oauth/token', data=data) as response:
				if response.status == 200:
					try:
						data = json.loads(await response.text())
						self.accessToken = data['access_token']
						self.accessTokenExpiration = time.time() + int(data['expires_in'])
					except Exception as e:
						print('Failed to parse json, getAccessToken', e)

	async def validateAccessToken(self):
		if self.accessToken == None or self.accessTokenExpiration == None or self.accessTokenExpiration < time.time():
			await self.getAccessToken()
			
	def getBattletag(self, ctx, battletag):
		battletagPattern = re.compile('^.*?\#\d+$')
		
		if (battletag == '-'):
			try:
				battletag = self.lastLookup[ctx.author.id]
				return battletag
			except:
				return None
		
		if battletagPattern.match(battletag):
			self.lastLookup[ctx.author.id] = battletag
			return battletag

		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `battletag` FROM `usersettings` WHERE `discordID`=%s"
				try:
					discordID = ctx.guild.get_member_named(battletag).id
				except:
					discordID = ctx.author.id
				cursor.execute(sql, (discordID))
				result = cursor.fetchone()
				if result is not None and result['battletag'] is not None:
					self.lastLookup[ctx.author.id] = result['battletag']
					return result['battletag']
				else:
					return None
		finally:
			connection.close()

	async def getHeroID(self, hero, battletag):
		await self.validateAccessToken()

		try:
			j = json.loads(await fetchWebpage(self, f'https://us.api.blizzard.com/d3/profile/{battletag.replace("#", "%23")}/?locale=en_US&access_token={self.accessToken}'))
		except Exception as e:
			return False
	
		for heroJ in j['heroes']:
			if heroJ['name'].lower() == hero.lower():
				return heroJ['id']
		
		return None

	@commands.command()
	@doThumbs()
	async def d3(self, ctx, *, battletag = '*'):
		"""Shows item level and progression info"""
		await ctx.trigger_typing()
		await self.validateAccessToken()
		battletag = self.getBattletag(ctx, battletag)
	
		try:
			j = json.loads(await fetchWebpage(self, f'https://us.api.blizzard.com/d3/profile/{battletag.replace("#", "%23")}/?locale=en_US&access_token={self.accessToken}'))
		except Exception as e:
			await ctx.send(f'Failed: {e}')
			return False

		embed=discord.Embed(
			title=f'{battletag} Diablo 3 - {j["guildName"]}',
			url=f'https://us.diablo3.com/en/profile/{battletag.replace("#", "-")}/',
			color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
		embed.set_thumbnail(url=self.d3images['logo'])
		embed.add_field(name='Paragon Levels', value=f'Normal: {j["paragonLevel"]}, Seasonal: {j["paragonLevelSeason"]}, Hardcore: {j["paragonLevelHardcore"]}, Seasonal Hardcore: {j["paragonLevelSeasonHardcore"]}', inline=False)
		embed.add_field(name='Kills', value=f'Monsters: {j["kills"]["monsters"]}, Elites: {j["kills"]["elites"]}, Hardcore Monsters: {j["kills"]["hardcoreMonsters"]}', inline=False)
		heroes = []
		for hero in j['heroes']:
			heroes.append(f'{("", "🍃")[hero["seasonal"]]}{hero["name"]} ({hero["level"]}) {("Male", "Female")[hero["gender"]]} {hero["class"].capitalize()}{("", "Hardcore")[hero["hardcore"]]}{("", "Dead")[hero["dead"]]}')
			#embed.add_field(name=f'{hero["name"]}', value=f'Class: {hero["class"]}, Hardcore: {hero["hardcore"]}, Seasonal: {hero["seasonal"]}, Dead: {hero["dead"]}')
		embed.add_field(name='Heroes', value="\n".join(heroes))
		try:
			await ctx.send(embed=embed)
		except discord.HTTPException as e:
			print('Beep', e)
			return False
		return True

	@commands.command()
	@doThumbs()
	async def d3info(self, ctx, hero, battletag = '*'):
		await ctx.trigger_typing()
		await self.validateAccessToken()
		battletag = self.getBattletag(ctx, battletag)
		heroID = await self.getHeroID(hero, battletag)

		try:
			j = json.loads(await fetchWebpage(self, f'https://us.api.blizzard.com/d3/profile/{battletag.replace("#", "%23")}/hero/{heroID}?locale=en_US&access_token={self.accessToken}'))
		except Exception as e:
			await ctx.send(f'Failed: {e}')
			return False

		embed=discord.Embed(
			title=f'{j["name"]} - {("Male", "Female")[j["gender"]]} {j["class"].capitalize()} {battletag}',
			description = f'Highest Solo Rift: {j["highestSoloRiftCompleted"]}\nParagon Level: {j["paragonLevel"]}\nSeasonal: {j["seasonal"]}, Hardcore: {j["hardcore"]}',
			url=f'https://us.diablo3.com/en/profile/{battletag.replace("#", "-")}/hero/{heroID}',
			color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
		embed.set_thumbnail(url=self.d3images[f'{j["class"]}_{("male", "female")[j["gender"]]}'])

		#embed.add_field(name='Paragon Level', value=f'Normal: {j["paragonLevel"]}, Seasonal: {j["paragonLevelSeason"]}, Hardcore: {j["paragonLevelHardcore"]}, Seasonal Hardcore: {j["paragonLevelSeasonHardcore"]}', inline=False)
		#embed.add_field(name='Kills', value=f'Monsters: {j["kills"]["monsters"]}, Elites: {j["kills"]["elites"]}, Hardcore Monsters: {j["kills"]["hardcoreMonsters"]}', inline=False)
		
		activeSkills = []
		for activeSkill in j['skills']['active']:
			try:
				skill = activeSkill["skill"]["name"]
			except:
				skill = 'Error'
			try:
				rune = activeSkill["rune"]["name"]
			except:
				rune = 'None'
			activeSkills.append(f'{skill} - {rune}')
		passiveSkills = []
		for passiveSkill in j['skills']['passive']:
			passiveSkills.append(passiveSkill["skill"]["name"])
		kanaisCube = [ ]
		for lp in j['legendaryPowers']:
			kanaisCube.append(lp["name"])
		#	embed.add_field(name=f'{activeSkill["skill"]["name"]} - {activeSkill["rune"]["name"]}', value=f'{activeSkill["skill"]["description"]}')
		if activeSkills:
			embed.add_field(name='Active Skills', value="\n".join(activeSkills))
		if passiveSkills:
			embed.add_field(name='Passive Skills', value=", ".join(passiveSkills))
		if kanaisCube:
			embed.add_field(name="Kanai's Cube", value=", ".join(kanaisCube))
		try:
			await ctx.send(embed=embed)
		except discord.HTTPException as e:
			print(e)
			return False
		return True

	@commands.command()
	@doThumbs()
	async def d3items(self, ctx, hero, battletag = '*'):
		await ctx.trigger_typing()
		await self.validateAccessToken()
		battletag = self.getBattletag(ctx, battletag)
		heroID = await self.getHeroID(hero, battletag)

		try:
			j = json.loads(await fetchWebpage(self, f'https://us.api.blizzard.com/d3/profile/{battletag.replace("#", "%23")}/hero/{heroID}?locale=en_US&access_token={self.accessToken}'))
		except Exception as e:
			await ctx.send(f'Failed: {e}')
			return False
		gear = []
		for item in j['items']:
			gear.append(f'{item}: [{j["items"][item]["name"]}](https://us.diablo3.com/en{j["items"][item]["tooltipParams"]})')

		embed=discord.Embed(
			title=f'{j["name"]} - {("Male", "Female")[j["gender"]]} {j["class"].capitalize()} {battletag}',
			description = "\n".join(gear),
			url=f'https://us.diablo3.com/en/profile/{battletag.replace("#", "-")}/hero/{heroID}',
			color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
		embed.set_thumbnail(url=self.d3images[f'{j["class"]}_{("male", "female")[j["gender"]]}'])

		try:
			await ctx.send(embed=embed)
		except discord.HTTPException as e:
			return False
		return True

def setup(bot):
	bot.add_cog(Diablo3(bot))