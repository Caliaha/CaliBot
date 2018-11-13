import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import json
import pymysql.cursors
import re
from stuff import BoxIt, doThumbs, superuser, fetchWebpage, postWebdata
import time
import urllib.parse
import urllib.request

WOWHEAD_ITEMURL = 'https://www.wowhead.com/item='
CLASSCOLORS = [ 'C79C6E' , 'F58CBA', 'ABD473', 'FFF569', 'FFFFFF', 'C41F3B', '0070DE', '69CCF0', '9482C9', '00FF96', 'FF7D0A', 'A330C9' ]
CLASSCOLORS_FULL = {'death knight':'C41F3B', 'deathknight':'C41F3B', 'demon hunter':'A330C9', 'demonhunter':'A330C9', 'druid':'FF7D0A','hunter':'ABD473','mage':'69CCF0','monk':'00FF96','paladin':'F58CBA','priest':'FFFFFF','rogue':'FFF569','shaman':'0070DE','warlock':'9482C9','warrior':'C79C6E'}
REGION = 'en-us'
DEFAULT_REALM = 'cairne'
BNET_CLASSES = [ 'warrior', 'paladin', 'hunter', 'rogue', 'priest', 'death knight', 'shaman', 'mage', 'warlock', 'monk', 'druid', 'demon hunter' ]

LEGION_ENCHANTSLOTS = [ 'neck', 'back', 'finger1', 'finger2' ]
LEGION_ENCHANTS = [ 5437, 5438, 5439, 5889, 5890, 5891, 5434, 5435, 5436, 5427, 5428, 5429, 5430 ]
LEGION_ENCHANTS_CHEAP = [ 5985, 5896, 5897, 5898, 5431, 5432, 5433, 5423, 5424, 5425, 5426 ]
LEGION_GEMS = [ 151580, 151583, 151584, 151585 ]
LEGION_GEMS_SABER = [ 130246, 130247, 130248 ]
LEGION_GEMS_MIDTIER = [ 130219, 130220, 130221, 130222 ]
LEGION_GEMS_CHEAP = [ 130215, 130216, 130217, 130218, ]
BFA_ENCHANTSLOTS = [ 'mainHand', 'finger1', 'finger2' ]
BFA_ENCHANTS = [ 5942, 5943, 5944, 5945, 5946, 5948, 5949, 5950, 5962, 5963, 5964, 5965, 5966 ]
BFA_ENCHANTS_CHEAP = [ 5938, 5939, 5940, 5941 ]
BFA_GEMS = [ 154126, 154127, 154128, 154129 ]
BFA_GEMS_SABER = [ 153707, 153708, 153709 ]
BFA_GEMS_CHEAP = [ 153710, 153711, 153712 ] 
# Deadly Deep Chemirine, Quick Lightsphene,  Masterful Argulite, Versatile Labradorite
# Saber's Eye of Strength, Saber's Eye of Agility, Saber's Eye of Intellect
# Deadly Eye of Prophecy, Quick Dawnlight, Versatile Maelstrom Sapphire, Masterful Shadowruby
# Deadly Deep Amber, Quick Azsunite, Versatile Skystone, Masterful Queen's Opal, 
# Neck
# 5437 -> Mark of the Claw
# 5438 -> Mark of the Distant Army
# 5439 -> Mark of the Hidden Satyr
# 5889 -> Mark of the Heavy Hide
# 5890 -> Mark of the Trained Soldier
# 5891 -> Mark of the Ancient Priestess

# 5895 -> Mark of the Master
# 5896 -> Mark of the Versatile
# 5897 -> Mark of the Quick
# 5898 -> Mark of the Deadly (Cheep)
#
# Back
# 5431 -> Word of Strength
# 5432 -> Word of Agility
# 5433 -> Word of Intellect
# 5434 -> Binding of Strength
# 5435 -> Binding of Agility
# 5436 -> Binding of Intellect


# Ring
# 5427 -> Binding of Critical Strike
# 5428 -> Binding of Haste
# 5429 -> Binding of Mastery
# 5430 -> Binding of Versatility

# 5423 -> Word of Critical Strike (Cheep)
# 5424 -> Word of Haste
# 5425 -> Word of Mastery
# 5426 -> Word of Versatility

class WoW():
	def __init__(self, bot):
		self.bot = bot
		self.lastLookup = {}

	async def getWarcraftLogsGuildID(self, guild, realm):
		print('getWarcraftLogsGuildID', guild, realm)
		try:
			guildList = await fetchWebpage(self, "https://www.warcraftlogs.com/search/?term=" + urllib.parse.quote_plus(guild))
			print("https://www.warcraftlogs.com/search/?term=" + urllib.parse.quote_plus(guild))
		except:
			return False, False, False

		#guildPattern = re.compile('<a href="/guilds/(\d+)">(' + guild + ') on ' + realm + ' \(' + region + '\)</a><br>', re.IGNORECASE)
		guildPattern = re.compile('<a href="(.*?)"><span class=".*?">(' + guild + ')</span></a></div><div class="server">US - (' + realm + ')</div></div>', re.IGNORECASE)

		guildMatch = guildPattern.search(guildList)
		print(guildMatch)
		if guildMatch is not None:
			guildPage = await fetchWebpage(self, guildMatch[1])
			guildIDPattern = re.compile('var guildID = (\d+);')
			guildIDMatch = guildIDPattern.search(guildPage)
			if guildIDMatch is not None:
				print('Returning', guildIDMatch[1], guildMatch[2], guildMatch[3])
				return guildIDMatch[1], guildMatch[2], guildMatch[3]
		return False, False, False

	def getCharacterRealm(self, author, toon):
		snowflakePattern = re.compile('<\@\!?(\d+)>')
		snowflake = snowflakePattern.match(toon)
		rolePattern = re.compile('<\@\&(\d+)>')
		failedMention = re.compile('\@.+')
		if (toon == '@everyone' or toon == '@here' or rolePattern.match(toon) or failedMention.match(toon)):
			print('Role was passed, ignoring')
			return None, None

		if (toon == '*' or snowflake):
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			try:
				with connection.cursor() as cursor:
					#Check if entry exists then update or create one
					sql = "SELECT `character`, `realm` FROM `usersettings` WHERE `discordID`=%s"
					try:
						discordID = snowflake[1]
					except:
						discordID = author.id
					cursor.execute(sql, discordID)
					result = cursor.fetchone()
					if result is not None and result['character'] is not None and result['realm'] is not None:
						return result['character'], result['realm']
					else:
						return None, None
			finally:
				connection.close()
		if (toon == '-'):
			if author in self.lastLookup:
				toon = self.lastLookup[author]
			else:
				return None, None
		else:
			self.lastLookup[author] = toon
		characterRegex = re.compile('^(.*?) (.*)$')
		characterName = characterRegex.match(toon)
 
		if characterName is None: # Couldn't find a space, probably just one argument and we'll assume it's the name
			return urllib.parse.quote_plus(toon), DEFAULT_REALM
		realm = characterName[2]
		
		return urllib.parse.quote_plus(characterName[1]), urllib.parse.quote_plus(realm.replace(" ","-"))

	@commands.command()
	@doThumbs()
	async def affixes(self, ctx):
		"""Show weekly mythic+ affixes"""
		await ctx.trigger_typing()
 
		wowheadData = await fetchWebpage(self, 'https://www.wowhead.com')
		if wowheadData is False:
			print("Couldn't access wowhead.com")
			await ctx.send('I was unable to access wowhead.com')
			return False

		mythicAffixes = { }
		mythicAffixes['Overflowing'] = 'Healing in excess of a target\'s maximum health is instead converted to a heal absorption effect.'
		mythicAffixes['Skittish'] = 'Enemies pay far less attention to threat generated by tanks.'
		mythicAffixes['Volcanic'] = 'While in combat, enemies periodically cause gouts of flame to erupt beneath the feet of distant players.'
		mythicAffixes['Necrotic'] = 'All enemies\' melee attacks apply a stacking blight that inflicts damage over time and reduces healing received.'
		mythicAffixes['Teeming'] = 'Additional non-boss enemies are present throughout the dungeon.'
		mythicAffixes['Raging'] = 'Non-boss enemies enrage at 30% health remaining, dealing 100% increased damage until defeated.'
		mythicAffixes['Bolstering'] = 'When any non-boss enemy dies, its death cry empowers nearby allies, increasing their maximum health and damage by 20%.'
		mythicAffixes['Sanguine'] = 'When slain, non-boss enemies leave behind a lingering pool of ichor that heals their allies and damages players.'
		mythicAffixes['Tyrannical'] = 'Boss enemies have 40% more health and inflict up to 15% increased damage.'
		mythicAffixes['Fortified'] = 'Non-boss enemies have 20% more health and inflict up to 30% increased damage.'
		mythicAffixes['Bursting'] = 'When slain, non-boss enemies explode, causing all players to suffer 10% of their max health in damage over 4 sec. This effect stacks.'
		mythicAffixes['Grievous'] = 'When injured below 90% health, players will suffer increasing damage over time until healed above 90% health.'
		mythicAffixes['Explosive'] = 'While in combat, enemies periodically summon Explosive Orbs that will detonate if not destroyed.'
		mythicAffixes['Quaking'] = 'Periodically, all players emit a shockwave, inflicting damage and interrupting nearby allies.'
		mythicAffixes['Relentless'] = 'Non-boss enemies are granted temporary immunity to Loss of Control effects.'
		mythicAffixes['Infested'] = 'Some non-boss enemies have been infested with a Spawn of G\'huun.'
 
		embed=discord.Embed(title='Mythic+ Affixes', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))

		affixesP = re.compile('<a href="(/affix=.*?)" id="US-mythicaffix-\d" class="icontiny"><img src=".*?"> (.*?)</a>')
		foundAffixes = False
		for affix in affixesP.findall(wowheadData):
			embed.add_field(name=affix[1], value=mythicAffixes[affix[1]])
			foundAffixes = True

		if not foundAffixes:
			embed.description = 'Unable to find the affixes for this week.  If it\'s a Tuesday then wowhead.com may not have updated their website yet.  Please try again later.'

		try:
			await ctx.send(embed=embed)
		except discord.HTTPException as e:
			print(e)
 
		if foundAffixes:
			return True
		else:
			return False

	@commands.command(description='Set default character/realm combo for WoW commands')
	async def setmain(self, ctx, *, toon: str):
		"""Set your default character to be used by other commands"""
		await ctx.trigger_typing()
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await ctx.send('Usage: !setmain character realm')
			return False
			
		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `character`, `realm` FROM `usersettings` WHERE `discordID`=%s"
				cursor.execute(sql, (ctx.message.author.id))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `usersettings` (`discordID`, `character`, `realm`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (ctx.message.author.id, character, realm))
					connection.commit()
				else:
					sql = "UPDATE `usersettings` SET `character` = %s, `realm` = %s WHERE `discordID` = %s LIMIT 1"
					cursor.execute(sql, (character, realm, ctx.message.author.id))
					connection.commit()
				await ctx.send(ctx.message.author.name + '\'s main has been set to **' + character + '** on **' + realm + '**')
		finally:
			connection.close()

	@commands.command()
	@doThumbs()
	async def mythic(self, ctx, *args):
		"""Shows raider.io mythic+ scores for a guild"""
		try:
			guild = args[0]
		except:
			guild = "The Touch of Chaos"
		try:
			realm = args[1]
		except:
			realm = "Cairne"
		
		fullWait = False
		fullWaitWarning = ''
		if guild is '*':
			guild = None
			fullWait = True
			fullWaitWarning = 'I have been requested to wait out the full duration of the queue, this may cause problems!\n'
		
		try:
			doWait = args[0]
			if doWait is '*':
				fullWait = True
				fullWaitWarning = 'I have been requested to wait out the full duration of the queue, this may cause problems!\n'
		except:
			pass

		if (len(args) <= 1 and ctx.guild is not None):
			guild, realm, updateableMessage = await self.fetchGuildFromDB(ctx)

		await ctx.trigger_typing()

		try:
			headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0' }
			rawJSON = await fetchWebpage(self, 'https://raider.io/api/search?term=' + urllib.parse.quote_plus(guild))
		except:
			await ctx.send('Error searching for guild\nUsage: !mythic "guild" "realm"')
			return False

		guilds = json.loads(rawJSON)
		guildData = None
		try:
			for guildJSON in guilds['matches']:
				#print(guildJSON['data']['realm']['name'])
				#print(guildJSON['data']['name'])
				if guildJSON['type'] == 'guild' and guildJSON['data']['realm']['name'].lower() == realm.lower() and guildJSON['data']['name'].lower() == guild.lower():
					guild = guildJSON['data']['name']
					realm = guildJSON['data']['realm']['slug']
					guildData = guildJSON
					print("Found guild")
		except:
			print('Unable to find guild')
			await ctx.send('Error searching for guild\nUsage: !mythic "guild" "realm"')
			return False
		
		if guildData is None:
			print('Unable to find guild')
			await ctx.send('Error searching for guild\nUsage: !mythic "guild" "realm"')
			return False

		try:
			updateableMessage
		except:
			updateableMessage = await ctx.send(fullWaitWarning + 'Performing lookup for <' + guild + '> on ' + realm)

		try:
			await updateableMessage.edit(content=fullWaitWarning + 'Attempting to update website before I request the data Status: Unknown Currently Processing: 0/0')

			data = { 'realmId': guildData['data']['realm']['id'], 'realm': guildData['data']['realm']['name'], 'region': guildData['data']['region']['slug'], 'guild': guildData['data']['name'], 'numMembers': 50 }

			postJSON = json.loads(await postWebdata(self, 'https://raider.io/api/crawler/guilds', data))
			#print(pageJSON['success'], pageJSON['jobData']['jobId'], pageJSON['jobData']['batchId'])
			checkStatus = True
			startTime = time.time()
			while checkStatus:
				status = json.loads(await fetchWebpage(self, 'https://raider.io/api/crawler/monitor?batchId=' + postJSON['jobData']['batchId']))
				try:
					if int(status['batchInfo']['jobs'][0]['positionInQueue']) > 0:
						queueStatus = 'Queue: {} out of {}\n'.format(status['batchInfo']['jobs'][0]['positionInQueue'], status['batchInfo']['jobs'][0]['totalItemsInQueue'])
					else:
						queueStatus = ''
					await updateableMessage.edit(content=fullWaitWarning + 'Attempting to update website before I request the data\nTime left before I abort this update: {:.0f}\n'.format((startTime + 120 - time.time())) + queueStatus + 'Status: {} Currently Processing: {}/{}'.format(status['batchInfo']['status'], status['batchInfo']['totalJobsRemaining'], status['batchInfo']['numCrawledEntities']))
				except Exception as e:
					print("Could not update !mythic updateable message", e)
				if  startTime + 120 < time.time():
					if not fullWait:
						checkStatus = False
						print("breaking from checkStatus because alotted time ran out")
				if ((status['batchInfo']['status'] != 'waiting' and status['batchInfo']['status'] != 'active')):
					checkStatus = False
					print("breaking from checkStatus because: " + status['batchInfo']['status'])
				#print(status['batchInfo']['status'], status['batchInfo']['totalJobsRemaining'], status['batchInfo']['numCrawledEntities'])
				await asyncio.sleep(0.4)
			print("Done requesting update from raider.io")
			await ctx.trigger_typing()
			await asyncio.sleep(6) # Just in case website still needs a little time to update things
		except:
			try:
				await updateableMessage.edit(content='Attempting to update website before I request the data\nStatus: Failed\nRaider.io will process the update at some point in the future but I am not waiting for it\nWill use older information', delete_after=60)
			except Exception as e:
				print("Could not update !mythic updateable message", e)
			print("Failed to request raider.io guild update")

		try:
			headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0' }
			print(realm ,guild, 'https://raider.io/api/guilds/us/' + urllib.parse.quote_plus(realm) + '/' + urllib.parse.quote_plus(guild) + '/roster')
			rawJSON = await fetchWebpage(self, 'https://raider.io/api/mythic-plus/rankings/characters?region=us&realm=' + realm + '&guild=' + guild + '&season=season-bfa-1&class=all&role=all&page=0')
			#rawJSON = await fetchWebpage(self, 'https://raider.io/api/guilds/us/' + realm + '/' + guild + '/roster')
		except:
			await ctx.send('Error fetching JSON for that guild (guild or realm probably doesn\'t exist or **has not been scanned by raider.io**), check your spelling\nUsage: !mythic "guild" "realm"')
			await updateableMessage.delete()
			return False

		try:
			roster = json.loads(rawJSON)
		except:
			print("Failed to parse JSON data")
			await ctx.send('Error parsing JSON for that guild')
			return False
		
		box = BoxIt()
		box.setTitle('Mythic+ Scores for ' + guild)
		for character in roster['rankings']['rankedCharacters']:
			print(character['character']['name'], character['character']['spec']['name'], character['rank'], character['score'])
			box.addRow([ character['character']['name'], character['character']['spec']['name'], float(character['score']) ])
		#for character in roster['guildRoster']['roster']:
		#	#print(character['character']['name'], character['character']['items']['item_level_equipped'], character['character']['items']['item_level_total'])
		#	if 'keystoneScores' in character and 'allScore' in character['keystoneScores']:
		#		if (int(character['keystoneScores']['allScore']) >= 300):
		#			box.addRow( [ character['character']['name'], str(character['character']['items']['item_level_equipped']), int(character['keystoneScores']['allScore']) ] )

		box.sort(2, True)
		box.setHeader( ['Name', 'Spec', 'Mythic+ Score' ] ) # FIX ME Shouldn't have to put header after the sort
		message = '```' + box.box()
		
		#embed=discord.Embed(title='Mythic+', description='SOmething', url='https://raider.io/guilds/us/' +  urllib.parse.quote(realm) + '/' + urllib.parse.quote(guild) + '/roster#mode=mythic_plus', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16))) Maybe for later

		if message:
			lines = message.splitlines(True)
			newMessage = ''
			for line in lines:
				if len(newMessage + line) > 1995:
					await ctx.send(newMessage + '```')
					#embed.add_field(name='-', value=newMessage + '```', inline=False)
					newMessage = '```'
				newMessage += line
			if newMessage != '':
				await ctx.send(newMessage + '```')
				#embed.add_field(name='-', value=newMessage + '```', inline=False)
		#await ctx.send(embed=embed)
		
		#try:
		#	data = { 'realmId': roster['guildRoster']['guild']['realm']['id'], 'realm': roster['guildRoster']['guild']['realm']['name'], 'region': roster['guildRoster']['guild']['region']['slug'], 'guild': roster['guildRoster']['guild']['name'], 'numMembers': 0 }
		#	page = await postWebdata(self, 'https://raider.io/api/crawler/guilds', data)
		#	print("Done requesting update from raider.io")
		#except:
		#	print("Failed to request raider.io guild update")
		try:
			await updateableMessage.delete()
		except:
			print("Could not delete !mythic updateable message")
		return True

	@commands.command()
	@doThumbs()
	async def wp(self, ctx, *, toon = '*'):
		"""Mythic+ completion rates as shown on wowprogress.com"""
		await ctx.trigger_typing()
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await ctx.send('Unable to find character and realm name, please double check the command you typed\nUsage: !wp character realm')
			return False
 
		try:
			wowprogressData = await fetchWebpage(self, 'https://www.wowprogress.com/character/us/' + realm + '/' + character)
		except:
			await ctx.send('Wowprogress data not found')
			print("Couldn't find wowprogress data for", character, realm)
			return False
		classP = re.compile('<i>.*?<span class=".*?">(.*?)</span> \d+</i>&nbsp;&nbsp;&nbsp;&nbsp;<a class="armoryLink')
		mythicTwoP = re.compile('Amount of Mythic 2\+ Dungeons <span class=\'info\'>completed in time</span>: (\d+)<br/>')
		mythicFiveP= re.compile('Amount of Mythic 5\+ Dungeons <span class=\'info\'>completed in time</span>: (\d+)<br/>')
		mythicTenP = re.compile('Amount of Mythic 10\+ Dungeons <span class=\'info\'>completed in time</span>: (\d+)<br/>')

		toonClass = classP.search(wowprogressData)
		mythicTwo = mythicTwoP.search(wowprogressData)
		mythicFive = mythicFiveP.search(wowprogressData)
		mythicTen = mythicTenP.search(wowprogressData)
		mythicMessage = None
		if mythicTwo is not None and mythicFive is not None and mythicTen is not None:
			mythicMessage = 'Mythic+ dungeons completed within the time limit:'
			mythicMessage += '\n**+2** -> ' + mythicTwo[1] + ', **+5** -> ' + mythicFive[1] + ', **+10** -> ' + mythicTen[1]
		else:
			await ctx.send('Mythic+ data not found')
			return False
 
		mythicScoreP = re.compile('<div class="gearscore">Mythic\+ Score <span class="small_tag info">.*?</span>: (.*?)</div>')
		mythicScoreHealerP = re.compile('<div class="gearscore">Mythic\+ Score Healer <span class="small_tag info">.*?</span>: (.*?)</div>')
		mythicScoreTankP = re.compile('<div class="gearscore">Mythic\+ Score Tank <span class="small_tag info">.*?</span>: (.*?)</div>')
		mythicScoreDPSP = re.compile('<div class="gearscore">Mythic\+ Score DPS <span class="small_tag info">.*?</span>: (.*?)</div>')

		mythicScore = mythicScoreP.search(wowprogressData)
		mythicHealer = mythicScoreHealerP.search(wowprogressData)
		mythicTank = mythicScoreTankP.search(wowprogressData)
		mythicDPS = mythicScoreDPSP.search(wowprogressData)

		color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16))
		if toonClass is not None:
			if toonClass[1] in CLASSCOLORS_FULL:
				color = discord.Color(int(CLASSCOLORS_FULL[toonClass[1].lower()], 16))
  
		embed=discord.Embed(title='Mythic+ Data for ' + character.capitalize() + ' @ ' + realm.capitalize(), url='https://www.wowprogress.com/character/us/' + realm + '/' + character, color=color)
		embed.add_field(name='Mythic+ Dungeons completed within the time limit', value='**+2** -> ' + mythicTwo[1] + ', **+5** -> ' + mythicFive[1] + ', **+10** -> ' + mythicTen[1], inline=False)
		#embed.set_thumbnail(url='https://render-us.worldofwarcraft.com/character/' + toon['thumbnail'])

		if mythicScore is not None:
			mythicMessage += '\nMythic+ Score: ' + mythicScore[1]
			embed.add_field(name='Mythic+ Score', value=mythicScore[1], inline=True)
		if mythicHealer is not None:
			mythicMessage += '\nMythic+ Healer Score: ' + mythicHealer[1]
			embed.add_field(name='Mythic+ Healer Score', value=mythicHealer[1], inline=True)
		if mythicTank is not None:
			mythicMessage += '\nMythic+ Tank Score: ' + mythicTank[1]
			embed.add_field(name='Mythic+ Tank Score', value=mythicTank[1], inline=True)
		if mythicDPS is not None:
			mythicMessage += '\nMythic+ DPS Score: ' + mythicDPS[1]
			embed.add_field(name='Mythic+ DPS Score', value=mythicDPS[1], inline=True)
 
		# This bit is to request that wowprogress.com update the character, this won't affect what we just got but may help with future requests for this character
		updateFormP = re.compile('<form method="post" id="update_character_form" action="(.*?)"><input type="hidden" name="(.*?)" value="(.*?)"><input type="button"\nonclick=".*?\n.*?value="(.*?)"></form>')
		updateFormFields = updateFormP.search(wowprogressData)

		if updateFormFields is not None:
			formData = { updateFormFields[2]: updateFormFields[3], 'submit': updateFormFields[4] }
		try:
			urllib.request.urlopen(urllib.request.Request('https://www.wowprogress.com' + updateFormFields[1], data=urllib.parse.urlencode(formData).encode()))
		except urllib.error.HTTPError as e:
			print(e.reason, updateFormFields[1], formData)
			print("Failed while requesting wowprogress update")
   
		try:
			await ctx.send(embed=embed)
		except discord.HTTPException as e:
			print(e)
			await ctx.send(mythicMessage)
		return True
	
	async def getIndividualPerformance(self, characterID, type, zone, difficulty):
		try:
			url = 'https://www.warcraftlogs.com/rankings/character_rankings_for_zone/' + characterID + '/' + zone + '/0/' + type + '/0/1/?keystone=0'
			characterPage = await fetchWebpage(self, url)
			characterPerfPattern = re.compile('<div class="stats" id="stats-10-' + difficulty + '-.*?">\nBest Perf\. Avg<br>\n<b style="font-size:32px" class=".*?">(.*?)</b>.*?>Median Perf\. Avg:<.*?>\n(.*?)<tr>.*?>(\d+)', re.DOTALL)
			characterPerfData = characterPerfPattern.search(characterPage)
			return characterPerfData[1], characterPerfData[2], characterPerfData[3]
		except:
			return "N/A", "N/A", "N/A"

	# Most of this stuff was copy/pasted from the !logs command FIXME
	async def getCharacterLog(self, characterID, selectedRankingZone = '17'):
		try:
			await fetchWebpage(self, 'https://www.warcraftlogs.com/tracker/updatecharacter/' + characterID)
		except:
			print("Failed to update character")

		statsPattern = re.compile('<div class="stats" id="stats-10-(\d+)-Any-Any">\n<div class="best-perf-avg">\nBest Perf. Avg<br>\n<b style="font-size:32px" class="(.*?)">(.*?)</b>\n</div>\n<table class="median-and-all-star"><tr><td style="text-align:right">Median Perf. Avg:<td style="text-align:left" class="(.*?)">\n(.*?)<tr><td style="text-align:right">Kills Ranked:<td style="text-align:left">(.*?)\n<tr><td style="text-align:right">All Star Points:<td style="text-align:left" class="primary">(.*?)<tr><td colspan=2 style="font-size:10px;">Out of (.*?) possible All Star Points</td></tr>\n</table>\n</div>')
		RankingMetrics = [ 'dps', 'hps' ]
		characterData = { }

		didStuff = False
		for RankingMetric in RankingMetrics:
			try:
				statsDataPage = await fetchWebpage(self, 'https://www.warcraftlogs.com/rankings/character_rankings_compact/' + characterID + '/' + selectedRankingZone + '/' + RankingMetric)
			except:
				print("Exception while accessing statsDataPage")
				return False
			statsData = statsPattern.findall(statsDataPage)
			if statsData is None:
				return False
  
			didStuff = False
			for statData in statsData:
				difficulty = 'Unknown';
   
				if statData[2] is not '-':
					didStuff = True

					if statData[0] is '5': difficulty = 'mythic'
					if statData[0] is '4': difficulty = 'heroic'
					if statData[0] is '3': difficulty = 'normal'
					if statData[0] is '2': difficulty = 'lfr' # Not sure
					if difficulty not in characterData:
						characterData[difficulty] = { }
					if RankingMetric not in characterData[difficulty]:
						characterData[difficulty][RankingMetric] = { }

					characterData[difficulty][RankingMetric] = { 'best': float(statData[2]), 'median': float(statData[4]), 'kills': int(statData[5]), 'allstar': float(statData[6].replace(',', '')), 'allstartotal': float(statData[7].replace(',', '') ) }
		if didStuff:
			return characterData
		else:
			return False

	@commands.command()
	@doThumbs()
	async def logs(self, ctx, *, toon = "*"):
		"""Shows basic warcraft logs summary"""
		await ctx.trigger_typing()
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await ctx.send('Unable to find character and realm name, please double check the command you typed\nUsage: !logs character realm')
			return False
 
		characterIDPattern = re.compile('var characterID = (\d+);')
 
		try:
			characterIDPage = await fetchWebpage(self, 'https://www.warcraftlogs.com/character/us/' + realm + '/' + character)
		except:
			print("Exception while accessing character Id page")
			await ctx.send('An Exception has occurred for some reason.  Could be website not found, network things, cosmic rays, or I goofed up. Maybe try your request again?')
			return False
		characterID = characterIDPattern.search(characterIDPage)
		if characterID is None:
			await ctx.send("Couldn't find character ID, character or realm may be incorrect or character doesn't exist on warcraftlogs.com or bad regex")
			return False
  
		try:
			await fetchWebpage(self, 'https://www.warcraftlogs.com/character/update/' + characterID[1])
		except:
			print('Failed to request warcraftlogs update for ' + character + '-' + realm)

		characterNameRealmPattern = re.compile('(.*?) - (.*?) - Warcraft Logs')
		characterNameRealm = characterNameRealmPattern.search(characterIDPage)
		characterClassPattern = re.compile('<div id="character-class" class="(.*?)">')
		characterClass = characterClassPattern.search(characterIDPage)
		characterPortraitPattern = re.compile('<img id="character-portrait-image" src="(.*?)">')
		characterPortrait = characterPortraitPattern.search(characterIDPage)

		#statsPattern = re.compile('<div class="stats" id="stats-10-(\d)-Any-Any">\n<div class="best-perf-avg">\nBest Perf. Avg<br>\n<b style="font-size:32px" class="(.*?)">(.*?)</b>\n</div>\n<table class="median-and-all-star"><tr><td style="text-align:right">Median Perf. Avg:<td style="text-align:left" class="(.*?)">\n(.*?)<tr><td style="text-align:right">Kills Ranked:<td style="text-align:left">(.*?)\n<tr><td style="text-align:right">All Star Points:<td style="text-align:left" class="primary">(.*?)<tr><td colspan=2 style="font-size:10px;">Out of (.*?) possible All Star Points</td></tr>\n</table>\n</div>')
		statsPattern = re.compile('Best Perf. Avg<br>\n<b style="font-size:32px" class=".*?">(.*?)</b>\n</div>\n<table class="median-and-all-star"><tr><td style="text-align:right">Median Perf. Avg:<td style="text-align:left" class=".*?">\n(.*?)\n<tr><td style="text-align:right">Kills Ranked:<td style="text-align:left">(\d+)\n.*?\n<tr><td style="text-align:right">All Star Points:<td style="text-align:left" class="primary">(.*?)\n')
		RankingMetrics = { '***Damage***': 'dps', '***Healing***': 'hps' }
		difficulties = { 'heroic': '4', 'normal': '3' }
		selectedRankingZone = '19' # Uldir

		color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16))

		if characterClass is not None:
			if characterClass[1].lower() in CLASSCOLORS_FULL:
				color = discord.Color(int(CLASSCOLORS_FULL[characterClass[1].lower()], 16))
 
		embed=discord.Embed(title='WarcraftLogs Data', url='https://www.warcraftlogs.com/character/us/' + realm + '/' + character, color=color)

		if characterPortrait is not None:
			embed.set_thumbnail(url='https:' + characterPortrait[1] + '?' + str(time.time()))

		if characterClass is not None and characterNameRealm is not None:
			embed.description = '{} @ {} - {}'.format(characterNameRealm[1], characterNameRealm[2], characterClass[1])

		characterData = { }
		characterData['heroic'] = { }
		characterData['normal'] = { }
		characterData['heroic']['dps'] = { 'best': 'N/A', 'median': 'N/A', 'killsRanked': 'N/A', 'allStars': 'N/A' }
		characterData['heroic']['hps'] = { 'best': 'N/A', 'median': 'N/A', 'killsRanked': 'N/A', 'allStars': 'N/A' }
		characterData['normal']['dps'] = { 'best': 'N/A', 'median': 'N/A', 'killsRanked': 'N/A', 'allStars': 'N/A' }
		characterData['normal']['hps'] = { 'best': 'N/A', 'median': 'N/A', 'killsRanked': 'N/A', 'allStars': 'N/A' }
		didStuff = False
		for difficulty, difficultyID in difficulties.items():
			for RankingMetricName, RankingMetric in RankingMetrics.items():
				try:
					#Overall:	https://www.warcraftlogs.com/character/rankings-compact/6818049/Best/19/hps/4/0/0
					#ItemLvl:	https://www.warcraftlogs.com/character/rankings-compact/6818049/Best/19/hps/4/1/0
					#Normal :	https://www.warcraftlogs.com/character/rankings-compact/6818049/Best/19/hps/3/1/0
					#			https://www.warcraftlogs.com/character/rankings-compact/6818049/Best/19/hps/4/1/0/0
					statsDataPage = await fetchWebpage(self, 'https://www.warcraftlogs.com/character/rankings-compact/' + characterID[1] + '/Best/' + selectedRankingZone + '/' + RankingMetric + '/' + difficultyID + '/1/0/0')
				except:
					print("Exception while accessing statsDataPage")
					await ctx.send('An Exception has occurred for some reason.  Could be website not found, network things, cosmic rays, or I goofed up. Maybe try your request again?')
					return False
				statData = statsPattern.search(statsDataPage)
				if statData:
					characterData[difficulty][RankingMetric] = { 'best': statData[1], 'median': statData[2], 'killsRanked': statData[3], 'allStars': statData[4] }
					didStuff = True

		if didStuff:
			try:
				for RankingMetricName, RankingMetric in RankingMetrics.items():
					embed.add_field(name=RankingMetricName, value='Best Performance Avg -> {} normal, {} heroic\nMedian Performance Avg -> {} normal, {} heroic\nKills Ranked -> {} normal, {} heroic\nAll Star Points -> {} normal, {} heroic'.format(characterData['normal'][RankingMetric]['best'], characterData['heroic'][RankingMetric]['best'], characterData['normal'][RankingMetric]['median'], characterData['heroic'][RankingMetric]['median'], characterData['normal'][RankingMetric]['killsRanked'], characterData['heroic'][RankingMetric]['killsRanked'], characterData['normal'][RankingMetric]['allStars'], characterData['heroic'][RankingMetric]['allStars']))
				await ctx.send(embed=embed)
			except discord.HTTPException as e:
				print(e)
				return False
			return True
		else:
			await ctx.send('No warcraftlogs data found or bad regex')
			return False

	@commands.command()
	@doThumbs()
	async def wowtoken(self, ctx):
		"""Show current wow token price"""
		await ctx.trigger_typing()
		tokenpattern = re.compile('\{"NA":\{"timestamp":(.*?)."raw":\{"buy":(.*?)."24min":(.*?),"24max":(.*?)."timeToSell":')
		try:
			tokenjson = urllib.request.urlopen('https://data.wowtoken.info/snapshot.json').read().decode('utf-8')
		except:
			await ctx.send('Couldn\'t access wowtoken.info')
			return False
		tokenmatch = tokenpattern.match(tokenjson)
		if tokenmatch is not None:
			embed=discord.Embed(title='WoW Token', description='The WoWToken is currently at {:,} gold.'.format(int(tokenmatch.group(2))), url='https://wowtoken.info', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
			embed.set_thumbnail(url='https://i.imgur.com/Mm5Ywjn.png')
			print('!wowtoken -> {:,}'.format(int(tokenmatch.group(2))))
			try:
				await ctx.send(embed=embed)
			except:
				await ctx.send('The WoWToken is currently at {:,} gold.'.format(int(tokenmatch.group(2))))
			return True
		else:
			await ctx.send('Failed to parse out wowtoken pricing information')
			return False

	@commands.command()
	@superuser()
	@commands.guild_only()
	async def defaultguild(self, ctx, *args):
		"""Sets default guild/realm for this discord server"""
		try:
			guild = args[0]
			realm = args[1]
			update = True
		except:
			msg = 'Usage: !defaultguild "GUILD" "REALM"'
			if (len(args)>0):
				msg = 'I was unable to understand what you meant.\n' + msg
			await ctx.send(msg)
			update = False
  
  
		guildID = ctx.guild.id
		print(guildID)

		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `guild`, `realm` FROM `guild_defaults` WHERE `guildID`=%s"
				cursor.execute(sql, (guildID))
				result = cursor.fetchone()
				if update is False and result is not None:
					await ctx.send('Currently the guild and realm for ' + ctx.guild.name + ' is set to <' + result['guild'] + '> on ' + result['realm'])
				print(guildID, result)
				if update is True:
					if result is None:
						sql = "INSERT INTO `guild_defaults` (`guildID`, `guild`, `realm`) VALUES(%s, %s, %s)"
						cursor.execute(sql, (guildID, guild, realm))
						connection.commit()
					else:
						sql = "UPDATE `guild_defaults` SET `guild` = %s, `realm` = %s WHERE `guildID` = %s LIMIT 1"
						cursor.execute(sql, (guild, realm, guildID))
						connection.commit()
						#print(result)
					await ctx.send('The default guild and realm for ' + ctx.guild.name + ' has been set to <' + guild + '> on ' + realm) 
		finally:
			connection.close()

	async def sendBulkyMessage(self, ctx, message, append = '', prepend = ''):
			lines = message.splitlines(True)
			newMessage = prepend
			for line in lines:
				if len(newMessage + line) > 1995:
					await ctx.send(newMessage + append)
					newMessage = prepend
				newMessage += line
			if newMessage != prepend:
				await ctx.send(newMessage + prepend)

	async def fetchWarcraftLogsAttendance(self, guildID, zoneID):
		try:
			attendancePage = await fetchWebpage(self, 'https://www.warcraftlogs.com/guilds/attendance_table/' + guildID + '/0/' + zoneID)
		except:
			return None

		characterPattern = re.compile('text-overflow:ellipsis">(\w+)<td style="text-align:right')
		
		attendance = []
		try:
			for character in characterPattern.findall(attendancePage):
				attendance.append(character)
		except:
			return None
			
		return attendance

	@commands.command(hidden=True)
	@doThumbs()
	async def guildperf(self, ctx, *args):
		"""Shows performance data for guild"""
		await ctx.send('This command is outdated, please use !rankings instead')
		return False

		difficultyID = { 'normal': '3', 'heroic': '4', 'mythic': '5' }
		raidID = { 'ant': '17', 'tomb': '13' }
		RAIDNAME = { 'ant': 'Antorus', 'tomb': 'Tomb of Sargeras' }

		try:
			guild = args[0]
		except:
			guild = "Clan Destined"
		try:
			realm = args[1]
		except:
			realm = "Cairne"
		
		try:
			full = args[2]
			full = True
		except:
			full = False
		
		
		if (len(args) == 0 and ctx.message.guild is not None):
			guild, realm, updateabledMessage = await self.fetchGuildFromDB(ctx)

		totalRequests = 0
		try:
			updateableMessage
		except:
			updateableMessage = await ctx.send('Performing lookup for <' + guild + '> on ' + realm + '\nThis will take a very long time! Total Requests Made: ' + str(totalRequests))
		await ctx.trigger_typing()
		#try:
		#	region = args[2]
		#except:
		region = "US"
		async with ctx.channel.typing():
			try:
				difficulty = args[2].lower()
				if difficulty not in difficultyID:
					raise
			except:
				difficulty = "normal"
			try:
				raid = args[3].lower()
				if raid not in raidID:
					raise
			except:
				raid = 'ant'
			print(guild, realm)
			
			try:
				guildList = await fetchWebpage(self, "https://www.warcraftlogs.com/search/?term=" + urllib.parse.quote_plus(guild))
				print("https://www.warcraftlogs.com/search/?term=" + urllib.parse.quote_plus(guild))
			except urllib.error.HTTPError as e:
				print(e.reason)
				await ctx.send('I was unable to search warcraftlogs.com for that guild')
				return False
			
			guildPattern = re.compile('<a href="/guilds/(\d+)">(' + guild + ') on ' + realm + ' \(' + region + '\)</a><br>', re.IGNORECASE)

			print('<a href="/guilds/(\d+)">' + guild + ' on ' + realm + ' \(' + region + '\)</a><br>')
			guildMatch = guildPattern.search(guildList)
			print(guildMatch)
			print("Raid: ", raidID[raid])
			print("Difficulty: ", difficultyID[difficulty])
			if guildMatch is not None:
					guildID = guildMatch[1]
					guild = guildMatch[2]
			else:
				await ctx.send('I was unable to find that guild on warcraftlogs.com, please check your typing and try again')
				return False
			print("GuildID: ", guildID)
			
			try:
				guildRoster = await fetchWebpage(self, 'https://www.warcraftlogs.com/guilds/characters/' + guildID)
			except:
				await ctx.send('I was unable to fetch the guild roster')
			
			characterPattern = re.compile('<a class="(\w+)" href="https://www\.warcraftlogs\.com/character/id/(\d+)">(\w+)</a>.*?<td class="\w+">[\w ]+<td class="main-table-number" style="width:16px">(\d+)<td', re.DOTALL)
			matches = characterPattern.search(guildRoster)

			RankingMetrics = [ 'dps', 'hps' ]
			difficulties = [ 'normal', 'heroic' ]
			boxes = { }
			didStuff = { }
			
			if not full:
				attendance = await self.fetchWarcraftLogsAttendance(guildID, '17')
			else:
				attendance = None
			print("Attendance:", attendance)
			if attendance is not None and len(attendance) > 0:
				updateMessage = 'Performing lookup for <' + guild + '> on ' + realm + '\nUsing attendance data to decrease requests! Total Requests Made: '
			else:
				full = True
				updateMessage = 'Performing lookup for <' + guild + '> on ' + realm + '\nThis will take a very long time! Total Requests Made: '
			print(full)
			for character in characterPattern.findall(guildRoster):
				print(character[0], character[1], character[2], character[3])
				if int(character[3]) == 110 and (full or (character[2] in attendance)):
					totalRequests += 1
					try:
						await updateableMessage.edit(content=updateMessage + str(totalRequests), delete_after=180)
					except:
						print("Couldn't update totals message")
					characterData = await self.getCharacterLog(character[1])
					if characterData:
						for difficulty in difficulties:
							if difficulty not in boxes:
								boxes[difficulty] = BoxIt()
								boxes[difficulty].setTitle(difficulty.capitalize() + ' - <' + guild + '>')
								#boxes[difficulty].setHeader( ['Name', 'Kills', 'DPS Best', 'Avg', 'Pnts', 'HPS Best', 'Avg', 'Pnts'] ) # FIXME
							try:
								char = characterData[difficulty]
								data = [ character[2], char['dps']['kills'], char['dps']['best'], char['dps']['median'], char['dps']['allstar'], char['hps']['best'], char['hps']['median'], char['hps']['allstar'] ]
								boxes[difficulty].addRow(data)
								print('Added character data for', character[2])
								didStuff[difficulty] = True
							except:
								print('No data for', character[2], difficulty)
			for difficulty in didStuff:
				if didStuff[difficulty]:
					boxes[difficulty].sort(0, False) # FIXME
					boxes[difficulty].setHeader( ['Name', 'Kills', 'DPS Best', 'Avg', 'Pnts', 'HPS Best', 'Avg', 'Pnts'] ) # FIXME
					await self.sendBulkyMessage(ctx, boxes[difficulty].box(), '```', '```')
			if len(didStuff) == 0:
				await ctx.send('No log data found for guild')
				return False
		return True

	async def fetchGuildFromDB(self, ctx):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `guild`, `realm` FROM `guild_defaults` WHERE `guildID`=%s"
				cursor.execute(sql, (ctx.guild.id))
				result = cursor.fetchone()
				print(result)
				if result is not None:
					guild = result["guild"]
					realm = result["realm"]
					updateableMessage = await ctx.send('Using <' + guild + '> on ' + realm + ' for guild ' + ctx.guild.name)
					return guild, realm, updateableMessage
		except:
			print("Database lookup failed fetchGuildFromDB")
		finally:
			connection.close()

		return None, None, None

	@commands.command()
	@doThumbs()
	async def linklogs(self, ctx, *args):
		"""Shows links to the latest warcraft logs for the guild"""

		try:
			guild = args[0]
		except:
			guild = None
		try:
			realm = args[1]
		except:
			realm = None
		
		
		if (len(args) == 0 and ctx.guild is not None):
			guild, realm, updateableMessage = await self.fetchGuildFromDB(ctx)

		await ctx.trigger_typing()

		region = "US"

		if (guild == None or realm == None):
			await ctx.send('Invalid arguments passed and no default guild  or realm set for this Discord guild\nUsage: !linklogs "Guild" "Server"')
		
		try:
			guildList = await fetchWebpage(self, "https://www.warcraftlogs.com/search/?term=" + urllib.parse.quote_plus(guild))
		except:
			await ctx.send('I was unable to search warcraftlogs.com for that guild')
			return False
		
		guildPattern = re.compile('<a href="/guilds/(\d+)">(' + guild + ') on ' + realm + ' \(' + region + '\)</a><br>', re.IGNORECASE)
		guildPattern = re.compile('<div class="search-item"><div class="name"><a href="(.*?)"><span class=".*?">(.*?)</span></a></div><div class="server">(.*?) - (.*?)</div></div>', re.IGNORECASE)
		guildMatch = guildPattern.search(guildList)
		if guildMatch is not None:
				url = guildMatch[1]
				guild = guildMatch[2]
		else:
			await ctx.send('I was unable to find that guild on warcraftlogs.com, please check your typing and try again')
			return False
		try:
			guildPage = await fetchWebpage(self, url)
			guildIDPattern = re.compile('var guildID = (\d+);')
			guildIDMatch = guildIDPattern.search(guildPage)
			guildID = guildIDMatch[1]
		except:
			await ctx.send('I was unable to find the guild ID for that guild')
			return False

		try:
			reportlist = await fetchWebpage(self, "https://www.warcraftlogs.com/guild/reports-list/" + str(guildID) + "/")
		except:
			await ctx.send('I was unable to grab the reports list for that guild or something')
			return False

		try:
			soup = BeautifulSoup(reportlist, "html.parser")
		except:
			await ctx.send('I was unable to parse the webpage with BeautifulSoup')
			return False
		
		reportTable = soup.find('table', id = 'reports-table')
		datePattern = re.compile('var reportDate = new Date\((\d+) \* 1000\);')
		reportData = ''

		count = 0
		for tr in reportTable.find_all('tr'):
			dateMatch = datePattern.search(str(tr))
			if dateMatch:
				date = int(dateMatch[1])
			else:
				date = 0
			try:
				links = tr.find_all('a')
				try:
					reportID = links[0].get('href').split("/reports/", 1)[1]
				except:
					print("Failed to find report id")
					reportID = ''
				reportData += '\n[' + links[0].string + '](https://www.warcraftlogs.com' + links[0].get('href') + ') > ' + time.strftime("%a, %d %b %Y", time.localtime(date)) + ' < ' + '[Analyzer](https://wowanalyzer.com/report/' + reportID + ')'
			except:
				reportData += '\nError parsing this log entry'
			count = count + 1
			if (count > 5):
				break

		embed=discord.Embed(title='Latest log reports for <' + guild + '>', description=reportData, url='https://www.warcraftlogs.com/guilds/reportslist/' + guildID + '/', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
		embed.set_thumbnail(url='https://www.warcraftlogs.com/img/common/warcraft-logo.png')
		embed.set_footer(text='Git Gud, Scrubs!', icon_url='https://wowanalyzer.com/favicon.png')

		try:
			await ctx.send(embed=embed)
			return True
		except discord.HTTPException as e:
			print(e)
			await ctx.send('I need to be allowed to embed messages')
			return False
		return True

	@commands.command(hidden=True)
	@doThumbs()
	async def allstars(self, ctx, *args):
		"""Shows guild allstars performance and realm rankings"""
		difficultyID = { 'normal': '3', 'heroic': '4', 'mythic': '5' }
		raidID = { 'uldir': '19', 'ant': '17', 'tomb': '13' }
		RAIDNAME = { 'uldir': 'Uldir', 'ant': 'Antorus', 'tomb': 'Tomb of Sargeras' }

		try:
			guild = args[0]
		except:
			guild = None
		try:
			realm = args[1]
		except:
			realm = None

		try:
			difficulty = args[2].lower()
			if difficulty not in difficultyID:
				raise
		except:
			if guild == 'normal' and realm == None:
				difficulty = 'normal'
				guild = None
			else:
				difficulty = "normal"

		if realm is None:
			realm = 'Cairne'

		if (guild is None and ctx.guild is not None):
			guild, realm, updateabledMessaged = await self.fetchGuildFromDB(ctx)

		async with ctx.channel.typing():
			#try:
			#	region = args[2]
			#except:
			region = "US"

			try:
				raid = args[3]
				if raid not in raidID:
					raise
			except:
				raid = 'uldir'
			print(guild, realm)

			guildID, guild, realm = await self.getWarcraftLogsGuildID(guild, realm)
			if not guildID:
				await ctx.send('I was unable to find that guild on warcraftlogs.com, please check your typing and try again')
				return False
			print("GuildID: ", guildID)
			print("Raid: ", raidID[raid])
			print("Difficulty: ", difficultyID[difficulty])
			try:
				guildRankings = await fetchWebpage(self, "https://www.warcraftlogs.com/guild/rankings/" + guildID + "/latest/")
				serverMatchPattern = re.compile('<a id="guildserver" href="/server/id/(\d+)/">') #re.compile('var filterServer = (\d+);')
				serverMatch = serverMatchPattern.search(guildRankings)
				print(serverMatch)
				serverID = serverMatch[1]
				
				print("Warcraftlogs ServerID:", serverID)
			except:
				await ctx.send('I was unable to parse the server id for that guild, tell Cali about it')
				return False

			totalRequests = 0
			try:
				updateableMessage
			except:
				updateableMessage = await ctx.send('This command is obsolete, please use the !rankings command.\nPerforming lookup for <' + guild + '> on ' + realm + '\nThis will take a bit! Total Requests Made: ' + str(totalRequests), delete_after=120)
			#await ctx.trigger_typing()
			urls = { }
			#https://www.warcraftlogs.com/rankings/guild-rankings-for-zone/80702/dps/19/0/3/10/1/Any/Any/rankings/historical/0/best/0
			urls['DAMAGE'] = 'https://www.warcraftlogs.com/rankings/guild-rankings-for-zone/' + str(guildID) + '/dps/' + raidID[raid] + '/0/'+ difficultyID[difficulty] + '/10/1/DPS/Any/rankings/historical/0/best/0'
			urls['DAMAGE'] = 'https://www.warcraftlogs.com/rankings/guild-rankings-for-zone/' + str(guildID) + '/dps/' + raidID[raid] + '/0/'+ difficultyID[difficulty] + '/10/1/DPS/Any/rankings/historical/0/best/0'
			#urls['HEALING'] = 'https://www.warcraftlogs.com/rankings/guild-rankings-for-zone/' + raidID[raid] + '/-1/'+ difficultyID[difficulty] + '/25/1/Healers/Any/0/' + serverID + '/0/0/' + guildID + '/?search=&page=1&keystone=0'
			#urls['TANKING - HPS'] = 'https://www.warcraftlogs.com/rankings/table/hps/' + raidID[raid] + '/-1/'+ difficultyID[difficulty] + '/25/1/Tanks/Any/0/' + serverID + '/0/0/' + guildID + '/?search=&page=1&keystone=0'
			#urls['TANKING - DPS'] = 'https://www.warcraftlogs.com/rankings/table/dps/' + raidID[raid] + '/-1/'+ difficultyID[difficulty] + '/25/1/Tanks/Any/0/' + serverID + '/0/0/' + guildID + '/?search=&page=1&keystone=0'

			message = '```Guild All Stars for <' + guild + '> ' + difficulty.capitalize() + ' ' + RAIDNAME[raid]
			didStuff = False


			for url in urls:
				print(urls[url])
				box = BoxIt()
				box.setTitle(url)
				#box.addRow( [ 'Name', 'Spec', 'Best', 'Median', 'Kills', 'Realm Rank', 'Score' ] )
				try:
					guildData = await fetchWebpage(self, urls[url])
					print(guildData)
					totalRequests += 1
					try:
						await updateableMessage.edit(content='Performing lookup for <' + guild + '> on ' + realm + '\nThis will take a bit! Total Requests Made: ' + str(totalRequests), delete_after=120)
					except:
						print("Couldn't update totals message")
				except:
					print('Failed to get guild performance data')
					await ctx.send('Something bad happened')

				# Realm Rank, CharacterID, Zone, metric, Name, score
				try:
					soup = BeautifulSoup(guildData, "lxml")
				except:
					await ctx.send('I was unable to parse the webpage with BeautifulSoup')
					return False
		
				reportTable = soup.find('table', {'class':'character-metric-table'})
				#print(reportTable)
				
				rows = reportTable.find_all("tr")
				for row in rows:
					data = row.find_all("td")
					#print('DATA', data)
					if not data:
						continue
					name = data[0].get_text().replace(" ", "").replace("\n", "").replace("\r", "").replace("/tbody>", "")
					avg = data[1].get_text().replace(" ", "").replace("\n", "").replace("\r", "").replace("/tbody>", "")
					score = data[-1].get_text().replace(" ", "").replace("\n", "").replace("\r", "").replace("/tbody>", "")

					print(name, avg, score)
					didStuff = True
					box.addRow( [ name, avg, score ] )
				box.sort(2, True)
				box.setHeader( [ 'Name', 'Average', 'All Star Points' ] )
				message += '\n' + box.box()
				#characterPattern = re.compile('<tr.*?<td class="rank.*?">(\d+)<(.*?)<a class="main-table-link.*?href="/rankings/character/(\d+)/(\d+)/#metric=(.*?)".>(.*?)</a>.*?<td class="main-table-number primary players-table-score".*?>([\d,]+).*?</tr>', re.DOTALL)
				#characterClassAndSpecPattern = re.compile('<img src="/img/icons/(.*?)-(.*?)\.jpg" class="players-table-spec-icon">')
				

				#for character in characterPattern.findall(guildData):
				#	print(character[0], character[1], character[2], character[3], character[4], character[5], character[6])
				#	try:
				#		classStuff = characterClassAndSpecPattern.search(character[1])
				#		playerClass = classStuff[1]
				#		playerSpec = classStuff[2]
				#	except:
				#		print(character)
				#		playerClass = 'N/A'
				#		playerSpec = 'N/A'
				#	best, median, kills = await self.getIndividualPerformance(character[2], character[4], character[3], str(difficultyID[difficulty]))
				#	totalRequests += 1
				#	try:
				#		await updateableMessage.edit(content='Performing lookup for <' + guild + '> on ' + realm + '\nThis will take a bit! Total Requests Made: ' + str(totalRequests), delete_after=120)
				#	except:
				#		print("Couldn't update totals message")
				#	didStuff = True
				#	box.addRow( [ character[5], playerSpec, float(best), float(median), int(kills), int(character[0]), int(character[6].replace(',', '')) ] )
				#box.sort(6, True)
				#box.setHeader( [ 'Name', 'Spec', 'Best', 'Median', 'Kills', 'Realm Rank', 'Score' ] )
				#message += '\n' + box.box()

			if didStuff:
				lines = message.splitlines(True)
				newMessage = ''
				for line in lines:
					if len(newMessage + line) > 1995:
						#embed=discord.Embed(title='Guild All Stars for <' + guild + '> ' + difficulty.capitalize() + ' ' + RAIDNAME[raid], description=newMessage + '```', color=0x9cf5a0)
						#await ctx.send(embed=embed)
						await ctx.send(newMessage + '```')
						newMessage = '```'
					newMessage += line
				if newMessage != '':
					#embed=discord.Embed(title='Guild All Stars for <' + guild + '> ' + difficulty.capitalize() + ' ' + RAIDNAME[raid] + ' - Cont.', description=newMessage + '```', color=0x9cf5a0)
					#await ctx.send(embed=embed)
					await ctx.send(newMessage + '```')
			else:
				await ctx.send('I was unable to find the right data')
				return False
			return True

	async def numSocketsGear(self, itemID, context, bonusList):
		count = 0
		try:

			url = 'https://us.api.battle.net/wow/item/' + str(itemID) + '?bl=' + ','.join(str(bonus) for bonus in bonusList) + '&locale=en_US&apikey=' + self.bot.APIKEY_WOW
			itemJSON = json.loads(await fetchWebpage(self, url))
		except:
			#print(e.reason)
			#print('Failure to load item socket data')
			return count
		if 'socketInfo' in itemJSON:
			for socket in itemJSON['socketInfo']['sockets']:
				if socket['type'] == 'PRISMATIC':
					count += 1
		return count

	@commands.command()
	@doThumbs()
	async def rankings(self, ctx, *args):
		"""Shows warcraftlogs.com rankings for a guild"""
		difficulties = { 'normal': '3', 'heroic': '4' }
		categories = [ 'today', 'historical' ]
		raids = { 'uldir': '19' }
		sortCategories = { 'performance': 1, 'allstars': 10 }
		validArguments = { '-g': 'guild', '-s': 'realm', '-d': 'difficulty', '-r': 'raid', '-c': 'category', '-t': 'sort' }
		arguments = { }
		
		if len(args) >= 1 and (args[0] == 'help' or args[0] == '-h'):
			await ctx.send('Usage: !rankings -g "guild name" -s "realm name" -d [normal|heroic] -r raidname -c [today|historical] -t [performance|allstars]\nAll arguments are optional.')
			return True
		
		for i in range(len(args)):
			if args[i] in validArguments:
				if i+1 < len(args):
					arguments[validArguments[args[i]]] = args[i+1]

		try:
			guild = arguments['guild']
		except:
			guild = False
		try:
			realm = arguments['realm']
		except:
			realm = "Cairne"
		try:
			difficulty = arguments['difficulty']
			difficulty in difficulties
		except:
			difficulty = 'normal'
		try:
			category = arguments['category']
			category in categories
		except:
			category = 'today'
		try:
			raid = arguments['raid']
			raid in raids
		except:
			raid = 'uldir'
		try:
			sort = arguments['sort']
			sort in sortCategories
		except:
			sort = 'performance'

		if (not guild and ctx.guild is not None):
			guild, realm, updateableMessage = await self.fetchGuildFromDB(ctx)

		try:
			await updateableMessage.delete()
		except:
			pass

		async with ctx.channel.typing():
			guildID, guild, realm = await self.getWarcraftLogsGuildID(guild, realm)
			if not guildID:
				return False

			urls = { }
			urls['Damage Dealers'] = 'https://www.warcraftlogs.com/rankings/guild-rankings-for-zone/' + guildID + '/dps/' + raids[raid] + '/0/' + difficulties[difficulty] + '/10/1/Any/Any/rankings/' + category + '/1/best/0/0'
			urls['Healers'] = 'https://www.warcraftlogs.com/rankings/guild-rankings-for-zone/' + guildID + '/hps/' + raids[raid] + '/0/' + difficulties[difficulty] + '/10/1/Any/Any/rankings/' + category + '/1/best/0/0'

			for title, url in urls.items():
				webpage = await fetchWebpage(self, url)
				soup = BeautifulSoup(webpage, "html.parser")

				rankingPattern = re.compile('<td class="character-metric-name"><a class="(.*?)" href=".*?">(.*?)</a>')
				bossRankPattern = re.compile('<td class="character-metric-overall-rank (.*?)">\n?(\d+\.\d+|\d+|\-)')

				rankingTable = soup.find('table', { 'class': 'character-metric-table summary-table' })
				box = BoxIt()
				box.setTitle('{} of {} for {} on {} difficulty'.format(title, guild, raid.capitalize(), difficulty.capitalize()))
				for tr in re.findall('<tr>(.*?)(?=<tr>|</table>)', str(rankingTable), re.DOTALL):
					tr = re.sub('<img class="wrong-spec-icon" src=".*?"/>\n', '', tr)
					tr = re.sub(' wrong-spec', '', tr)
					
					rankingMatch = rankingPattern.search(str(tr))
					if rankingMatch:
						characterData = ([ rankingMatch[2] ])
						for bossRanks in bossRankPattern.findall(tr):
							if bossRanks[1] == '-':
								characterData.append(bossRanks[1])
							elif re.search('\.', bossRanks[1]):
								characterData.append(float(bossRanks[1]))
							else:
								characterData.append(int(bossRanks[1]))
						box.addRow(characterData)
				box.sort(sortCategories[sort], True)
				box.setHeader( ['Name', 'Avg', 'Taloc', 'Mom', 'Devourer', 'Zek', 'Vect', 'Zul', 'Myth', 'G\'huun', '*'] )
				await self.sendBulkyMessage(ctx, box.box(), '```', '```')
		return True
	
	@commands.command()
	@doThumbs()
	async def gear(self, ctx, *, toon = '*'):
		"""Shows current equipped gear and basic gem/enchant check"""
		await ctx.trigger_typing()

		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await ctx.send('Unable to find character and realm name, please double check the command you typed\nUsage: !gear character realm')
			return False
 
		gearSlots = [ 'head', 'neck', 'shoulder', 'back', 'chest', 'wrist', 'hands', 'waist', 'legs', 'feet', 'finger1', 'finger2', 'trinket1', 'trinket2', 'mainHand', 'offHand' ] # Left out shirt, tabard

		try:
			itemsJSON = await fetchWebpage(self, 'https://us.api.battle.net/wow/character/' + realm + '/' + character + '?fields=items,guild&locale=en_US&apikey=' + self.bot.APIKEY_WOW)
		except:
			await ctx.send("Unable to access character data, check for typos or invalid realm or the Battle.net API is down")
			return False
		try:
			toon = json.loads(itemsJSON)
		except:
			await ctx.send('Unable to parse JSON data, probably Cali\'s fault')
			return False
		#except discord.HTTPException as e:

		gearData = ""
		msg = 'Gear for **' + toon['name'] + '** of **' + toon['realm'] + '**'
		msg += ' (<https://worldofwarcraft.com/en-us/character/' + realm + '/' + character + '>)'
		msg += '\n**Item Level**: *' + str(toon['items']['averageItemLevelEquipped']) + '* equipped, *' + str(toon['items']['averageItemLevel']) + '* total'
 
 
		missingEnchants = ''
		missingGems = ''
		totalSockets = 0
		sabersEye = False
		gemsCheapEquipped = 0
		gemsMidTierEquipped = 0
		#legendariesNotUpgraded = 0
		#totalLegendariesEquipped = 0
		for gear in gearSlots:
			#embed.add_field(name="Gear", value=gearData, inline=True)
			#gearData = ""
			socketData = ''
			if gear in toon['items']:
				sockets = await self.numSocketsGear(toon['items'][gear]['id'], toon['items'][gear]['context'], toon['items'][gear]['bonusLists'])
				totalSockets += sockets
				if (sockets > 0):
					gemCount = 0
					for i in range(0, sockets):
						#print("Loop", i, sockets)
						try:
							if toon['items'][gear]['tooltipParams']['gem' + str(i)]:
								quality = toon['items'][gear]['tooltipParams']['gem' + str(i)]
								#print("Gem Quality", quality, gear)
								if quality in BFA_GEMS:
									pass
								elif quality in BFA_GEMS_SABER:
									sabersEye = True
								#elif quality in LEGION_GEMS_MIDTIER:
								#	gemsMidTierEquipped += 1
								elif quality in BFA_GEMS_CHEAP:
									gemsCheapEquipped += 1
							else:
								gemCount += 1
						except:
							gemCount += 1
					#print(sockets, gemCount)
					if (gemCount > 0):
						if missingGems != '':
							missingGems += ', '
						missingGems += gear.capitalize() + ' is missing ' + str(gemCount) + '/' + str(sockets) + ' gems'
					if (sockets > 0):
						socketData = ' (' + str(sockets - gemCount) + '/' + str(sockets) + ')'
					
				enchant = ''
				if gear in BFA_ENCHANTSLOTS:
					try:
						#print(toon['items'][gear]['tooltipParams']['enchant'])
						if toon['items'][gear]['tooltipParams']['enchant'] in BFA_ENCHANTS:
							pass
						elif toon['items'][gear]['tooltipParams']['enchant'] in BFA_ENCHANTS_CHEAP:
							enchant = 'Cheap'
						else:
							enchant = 'No'
					except:
						enchant = 'No'
					if enchant == 'No' or enchant == 'Cheap':
						if missingEnchants != '':
							missingEnchants += ', '
						missingEnchants += enchant + ' ' + gear.capitalize() + ' enchant'

				#if int(toon['items'][gear]['quality']) == 5 and (int(toon['items'][gear]['itemLevel']) >= 910 and int(toon['items'][gear]['itemLevel']) <= 1000):
				#	totalLegendariesEquipped += 1
				#	if int(toon['items'][gear]['itemLevel']) < 1000:
				#		legendariesNotUpgraded += 1

				msg += '\n' + str(toon['items'][gear]['itemLevel']) + ' - ' + gear.capitalize() + ' - ' + toon['items'][gear]['name'] + ' - <' + WOWHEAD_ITEMURL + str(toon['items'][gear]['id']) + '> '
				gearData += str(toon['items'][gear]['itemLevel']) + socketData + ' - ' + gear.capitalize() + ' - [' + toon['items'][gear]['name'] + '](' + WOWHEAD_ITEMURL + str(toon['items'][gear]['id']) + ')\n'

						
				#embed.add_field(name=gear.capitalize(), value=str(toon['items'][gear]['itemLevel']) + ' - ' + gear.capitalize() + ' - [' + toon['items'][gear]['name'] + '](' + WOWHEAD_ITEMURL + str(toon['items'][gear]['id']) + ')', inline=False)
			else:
				msg += '\n' + gear.capitalize() + ' is empty!'
				gearData += gear.capitalize() + ' is empty!\n'

		if (not sabersEye and totalSockets > 0):
			if missingGems != '':
				missingGems += '\n'
			missingGems += 'No Kraken\'s Eye Equipped!'
		if (gemsMidTierEquipped > 0):
			if missingGems != '':
				missingGems += '\n'
			missingGems += str(gemsMidTierEquipped) + ' "okay" gems equipped!'
		if (gemsCheapEquipped > 0):
			if missingGems != '':
				missingGems += '\n'
			missingGems += str(gemsCheapEquipped) + ' "pathetic" gems equipped!'
 
		if (toon['class']-1) < len(CLASSCOLORS):
			color = discord.Color(int(CLASSCOLORS[toon['class']-1], 16))
		else:
			color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16))
		#print(toon['class'], color)
		embedTitle = toon['name'] + ' of ' + toon['realm']
		if 'guild' in toon:
			if 'name' in toon['guild']:
				embedTitle += ' <' + toon['guild']['name'] + '>'
		embed=discord.Embed(title=embedTitle, description=gearData, url='https://worldofwarcraft.com/en-us/character/' + realm + '/' + character, color=color)
		embed.set_thumbnail(url='https://render-us.worldofwarcraft.com/character/' + toon['thumbnail'] + '?' + str(time.time()))
		embed.add_field(name="Equipped Item Level", value=str(toon['items']['averageItemLevelEquipped']), inline=True)
		embed.add_field(name="Total Item Level", value=str(toon['items']['averageItemLevel']), inline=True)
		missingStuff = missingEnchants + '\n' + missingGems
		#if (totalLegendariesEquipped < 2):
		#	missingStuff += '\nDoesn\'t have the max allowed number of legendaries! Only ' + str(totalLegendariesEquipped) + ' equipped.'
		#if (legendariesNotUpgraded == 1):
		#	missingStuff += '\n' + str(legendariesNotUpgraded) + ' legendary not at max level'
		#elif (legendariesNotUpgraded > 1):
		#	missingStuff += '\n' + str(legendariesNotUpgraded) + ' legendaries not at max level'
		if (missingStuff != '\n'):
			embed.add_field(name="Gear Check", value=missingStuff, inline=True)
		#print(toon['name'] + '** of **' + toon['realm'] + str(toon['items']['averageItemLevelEquipped']) + '* equipped, *' + str(toon['items']['averageItemLevel']) + '* total')
		#print('https://worldofwarcraft.com/en-us/character/' + realm + '/' + character)
		#print('https://render-us.worldofwarcraft.com/character/' + toon['thumbnail'])

		try:
			await ctx.send(embed=embed)
		except discord.HTTPException as e:
			print(e)
			await ctx.send(msg)
		return True

	@commands.command()
	@doThumbs()
	async def armory(self, ctx, *, toon = '*'):
		"""Shows item level and progression info"""
		await ctx.trigger_typing()
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await ctx.send('Unable to find character and realm name, please double check the command you typed\nUsage: !armory character realm')
			return False
		 
		try:
			characterJSON = await fetchWebpage(self, 'https://us.api.battle.net/wow/character/' + realm + '/' + character + '?fields=guild,progression,items,achievements&locale=en_US&apikey=' + self.bot.APIKEY_WOW)
			if (characterJSON == "{}"):
				await ctx.send('Empty JSON Data, this character probably doesn\'t exist or something.')
				return False
			try:
				toon = json.loads(characterJSON)
			except:
				print('Unable to parse JSON data, probably Cali\'s fault')
				await ctx.send('Unable to parse JSON data, probably Cali\'s fault')
				return False
		except:
			await ctx.send('Unable to access api for ' + character + ' - ' + realm + '\nBattle.net API could also be down')
			return False

		color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16))
		if (toon['class']-1) < len(CLASSCOLORS):
		 color = discord.Color(int(CLASSCOLORS[toon['class']-1], 16))
		 
		 embedTitle = toon['name'] + ' of ' + toon['realm']
		 if 'guild' in toon:
		  if 'name' in toon['guild']:
		   embedTitle += ' <' + toon['guild']['name'] + '>'
		 
		 embed=discord.Embed(title=embedTitle, url='https://worldofwarcraft.com/en-us/character/' + realm + '/' + character, color=color)
		 embed.set_thumbnail(url='https://render-us.worldofwarcraft.com/character/' + toon['thumbnail'] + '?' + str(time.time()))
		 embed.add_field(name="Equipped Item Level", value=str(toon['items']['averageItemLevelEquipped']), inline=True)
		 embed.add_field(name="Total Item Level", value=str(toon['items']['averageItemLevel']), inline=True)

		#RAIDS = [ 'Antorus, the Burning Throne', 'Tomb of Sargeras', 'The Nighthold', 'Trial of Valor', 'The Emerald Nightmare' ]
		#RAID_AOTC = { 'Antorus, the Burning Throne': 12110, 'Tomb of Sargeras': 11874, 'The Nighthold': 11195, 'Trial of Valor': 11581, 'The Emerald Nightmare': 11194 }
		RAIDS = [ 'Uldir' ]
		RAID_AOTC = { 'Uldir' : 12536 }
		RAID_PROG = { }
		for raid in RAIDS:
			RAID_PROG[raid] = { }
			RAID_PROG[raid]['Normal'] = 0
			RAID_PROG[raid]['Heroic'] = 0
			RAID_PROG[raid]['Mythic'] = 0
			RAID_PROG[raid]['total'] = 0
		 
		for raid in toon['progression']['raids']:
			if raid['name'] in RAID_PROG:
				for boss in raid['bosses']:
					RAID_PROG[raid['name']]['total'] += 1
					if boss['normalKills'] > 0:
						RAID_PROG[raid['name']]['Normal'] += 1
					if boss['heroicKills'] > 0:
						RAID_PROG[raid['name']]['Heroic'] += 1
					if boss['mythicKills'] > 0:
						RAID_PROG[raid['name']]['Mythic'] += 1
		progressionMessage = ''
		firstRaid = True

		for raid in RAID_PROG:
			firstProg = True
			raidMessage = ''
			progress = False
			if firstRaid is True:
				raidMessage += '**' + raid + '**: '
				firstRaid = False
			else:
				raidMessage += '\n**' + raid + '**: '
			for difficulty in RAID_PROG[raid]:
				if difficulty == "total":
					continue
				if firstProg is not True:
					raidMessage += ', '
				else:
					firstProg = False   
				raidMessage += str(RAID_PROG[raid][difficulty]) + '/' + str(RAID_PROG[raid]['total']) + ' ' + difficulty
				if RAID_PROG[raid][difficulty] > 0:
					progress = True
			if progress is True:
				progressionMessage += raidMessage
				if raid in RAID_AOTC:
					if RAID_AOTC[raid] in toon['achievements']['achievementsCompleted']:
						progressionMessage += ' *AOTC*'
		 
		if progressionMessage != '':
			embed.add_field(name='Progression', value=progressionMessage)

		hasAOTC = True
		if 12535 in toon['achievements']['achievementsCompleted']:
			embed.description = 'Has *Cutting Edge* for the current tier'
		elif 12536 in toon['achievements']['achievementsCompleted']:
			embed.description = 'Has *AOTC* for the current tier'
		else:
			hasAOTC = False
			embed.description = 'Doesn\'t Have AOTC for the current tier'
		  
		try:
			await ctx.send(embed=embed)
		except discord.HTTPException as e:
			characterProgress = toon['name'] + ' - ' + toon['realm']
			characterProgress += '\nEquipped Item Level: ' + str(toon['items']['averageItemLevelEquipped']) + ' Total item Level: ' + str(toon['items']['averageItemLevel'])
			if hasAOTC:
				characterProgress += '\nHas AOTC for the current tier'
			else:
				characterProgress += '\nDoesn\'t have AOTC for the current tier'
				characterProgress += '\n' + progressionMessage
			print(e)
			await ctx.send(characterProgress)
		return True

def setup(bot):
	bot.add_cog(WoW(bot))