import discord
from discord.ext import commands
import json
import pymysql.cursors
import re
import time
import urllib.request
import urllib.parse

WOWHEAD_ITEMURL = 'https://www.wowhead.com/item='
CLASSCOLORS = [ 'C79C6E' , 'F58CBA', 'ABD473', 'FFF569', 'FFFFFF', 'C41F3B', '0070DE', '69CCF0', '9482C9', '00FF96', 'FF7D0A', 'A330C9' ]
CLASSCOLORS_FULL = {'death knight':'C41F3B', 'deathknight':'C41F3B', 'demon hunter':'A330C9', 'demonhunter':'A330C9', 'druid':'FF7D0A','hunter':'ABD473','mage':'69CCF0','monk':'00FF96','paladin':'F58CBA','priest':'FFFFFF','rogue':'FFF569','shaman':'0070DE','warlock':'9482C9','warrior':'C79C6E'}
REGION = 'en-us'
DEFAULT_REALM = 'cairne'
BNET_CLASSES = [ 'warrior', 'paladin', 'hunter', 'rogue', 'priest', 'death knight', 'shaman', 'mage', 'warlock', 'monk', 'druid', 'demon hunter' ]

class WoW():
	def __init__(self, bot):
		self.bot = bot
		self.lastLookup = {}
 
	def getCharacterRealm(self, author, toon):
		if (toon == '*'):
			connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db='CaliBot', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			try:
				with connection.cursor() as cursor:
					#Check if entry exists then update or create one
					sql = "SELECT `character`, `realm` FROM `main` WHERE `discordID`=%s"
					cursor.execute(sql, (author.id))
					result = cursor.fetchone()
					if result is not None:
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

	async def fetchWebpage(self, url):
		attempts = 0
		while attempts < 5:
			try:
				webpage = urllib.request.urlopen(url).read().decode('utf-8')
				return webpage
			except:
				print("Failed to grab webpage", url, attempt)
				attempt += 1
				return False

	@commands.command(pass_context=True, description='Show weekly mythic+ affixes as shown on wowhead.com')
	async def affixes(self, ctx):
		await self.bot.send_typing(ctx.message.channel)
 
		wowheadData = await self.fetchWebpage('https://www.wowhead.com')
		if wowheadData is False:
			print("Couldn't access wowhead.com")
			await self.bot.send_message(ctx.message.channel, 'I was unable to access wowhead.com')
			return False
  
		affix1P = re.compile('<a href="(/affix=.*?)" id="US-mythicaffix-1" class="icontiny"><img src=".*?"> (.*?)</a>')
		affix2P = re.compile('<a href="(/affix=.*?)" id="US-mythicaffix-2" class="icontiny"><img src=".*?"> (.*?)</a>')
		affix3P = re.compile('<a href="(/affix=.*?)" id="US-mythicaffix-3" class="icontiny"><img src=".*?"> (.*?)</a>')

		affix1 = affix1P.search(wowheadData)
		affix2 = affix2P.search(wowheadData)
		affix3 = affix3P.search(wowheadData)
 
		embed=discord.Embed(title='Mythic+ Affixes', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))

		msg = 'Mythic+ Affixes'

		if affix1 is None or affix2 is None or affix3 is None:
			await self.bot.send_message(ctx.message.channel, 'I was unable to find the affixes on wowhead.com. If it\'s a tuesday, wowhead may not have yet updated them for this week.')
			print("Couldn't find the affixes")
			return False

		affixes = { affix1[1] : affix1[2], affix2[1] : affix2[2], affix3[1] : affix3[2] }
		succeded = 0
		for affix in affixes:
			affixDescP = re.compile('<div id="infobox-alternate-position"></div>(.*?)<h2 class')
			wowheadAffixData = await self.fetchWebpage('https://www.wowhead.com' + affix)
			if wowheadAffixData is not False:
				affixDesc = affixDescP.search(wowheadAffixData)
				if affixDesc is not None:
					embed.add_field(name=affixes[affix], value=affixDesc[1])
					msg += '\n**' + affixes[affix] + '** -> ' + affixDesc[1]
					succeded += 1
 
		if succeded < 3:
			#await self.bot.send_message(ctx.message.channel, 'Error attempting to grab some or all affix descriptions' + str(succeded))
			embed.description = 'The affixes for this week are: ' + affix1[2] + ', ' + affix2[2] + ', and ' + affix3[2] + '.\nThere were some errors while attempting to fetch their effects.'
			msg += '\nThe affixes for this week are: ' + affix1[2] + ', ' + affix2[2] + ', and ' + affix3[2] + '.\nThere were some errors while attempting to fetch their effects.'

		try:
			await self.bot.send_message(ctx.message.channel, embed=embed)
		except discord.HTTPException as e:
			await self.bot.send_message(ctx.message.channel, msg)
			print(e)
 
		if succeded > 0:
			return True
		else:
			return False

	@commands.command(pass_context=True, description='Set default character/realm combo for WoW commands')
	async def setmain(self, ctx, *, toon: str):
		await self.bot.send_typing(ctx.message.channel)
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await self.bot.send_message(ctx.message.channel, 'Usage: !setmain character realm')
			return False
			
		connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db='CaliBot', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `character`, `realm` FROM `main` WHERE `discordID`=%s"
				cursor.execute(sql, (ctx.message.author.id))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `main` (`discordID`, `character`, `realm`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (ctx.message.author.id, character, realm))
					connection.commit()
				else:
					sql = "UPDATE `main` SET `character` = %s, `realm` = %s WHERE `discordID` = %s LIMIT 1"
					cursor.execute(sql, (character, realm, ctx.message.author.id))
					connection.commit()
				await self.bot.send_message(ctx.message.channel, ctx.message.author.name + '\'s main has been set to **' + character + '** on **' + realm + '**')
		finally:
			connection.close()

	@commands.command(pass_context=True)
	async def wp(self, ctx, *, toon = '*'):
		await self.bot.send_typing(ctx.message.channel)
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await self.bot.send_message(ctx.message.channel, 'Unable to find character and realm name, please double check the command you typed')
			return False
 
		try:
			wowprogressData = urllib.request.urlopen('https://www.wowprogress.com/character/us/' + realm + '/' + character).read().decode('utf-8')
		except:
			await self.bot.send_message(ctx.message.channel, 'Wowprogress data not found')
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
			await self.bot.send_message(ctx.message.channel, 'Mythic+ data not found')
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
  
		embed=discord.Embed(title='Mythic+ Data', url='https://www.wowprogress.com/character/us/' + realm + '/' + character, color=color)
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
			await self.bot.send_message(ctx.message.channel, embed=embed)
		except discord.HTTPException as e:
			print(e)
			await self.bot.send_message(ctx.message.channel, mythicMessage)
		return True
	
	@commands.command(pass_context=True)
	async def logs(self, ctx, *, toon = "*"):
		await self.bot.send_typing(ctx.message.channel)
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await self.bot.send_message(ctx.message.channel, 'Unable to find character and realm name, please double check the command you typed')
			return False
 
		characterIDPattern = re.compile('var characterID = (\d+);')
 
		try:
			characterIDPage = await self.fetchWebpage('https://www.warcraftlogs.com/character/us/' + realm + '/' + character)
		except:
			print("Exception while accessing character Id page")
			await self.bot.send_message(ctx.message.channel, 'An Exception has occurred for some reason.  Could be website not found, network things, cosmic rays, or I goofed up. Maybe try your request again?')
			return False
		characterID = characterIDPattern.search(characterIDPage)
		if characterID is None:
			await self.bot.send_message(ctx.message.channel, "Couldn't find character ID, character or realm may be incorrect or character doesn't exist on warcraftlogs.com or bad regex")
			return False
  
		try:
			urllib.request.urlopen('https://www.warcraftlogs.com/tracker/updatecharacter/' + characterID[1]).read().decode('utf-8')
		except:
			print('Failed to request warcraftlogs update for ' + character + '-' + realm)

		characterNameRealmPattern = re.compile('(.*?) on (.*?) - Warcraft Logs')
		characterNameRealm = characterNameRealmPattern.search(characterIDPage)
		characterClassPattern = re.compile('<div id="character-class" class=".*?">\r\n(.*?) \r\n(.*?)</div>')
		characterClass = characterClassPattern.search(characterIDPage)
		characterPortraitPattern = re.compile('<img id="character-portrait-image" src="(.*?)">')
		characterPortrait = characterPortraitPattern.search(characterIDPage)

		statsPattern = re.compile('<div class="stats" id="stats-10-(\d)-Any-Any">\n<div class="best-perf-avg">\nBest Perf. Avg<br>\n<b style="font-size:32px" class="(.*?)">(.*?)</b>\n</div>\n<table class="median-and-all-star"><tr><td style="text-align:right">Median Perf. Avg:<td style="text-align:left" class="(.*?)">\n(.*?)<tr><td style="text-align:right">Kills Ranked:<td style="text-align:left">(.*?)\n<tr><td style="text-align:right">All Star Points:<td style="text-align:left" class="primary">(.*?)<tr><td colspan=2 style="font-size:10px;">Out of (.*?) possible All Star Points</td></tr>\n</table>\n</div>')
		RankingMetrics = [ 'dps', 'hps' ]
		selectedRankingZone = '17' # Tomb of Sargeras

		color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16))
		print(characterClass)
		if characterClass is not None:
			if characterClass[2].lower() in CLASSCOLORS_FULL:
				color = discord.Color(int(CLASSCOLORS_FULL[characterClass[2].lower()], 16))
 
		embed=discord.Embed(title='WarcraftLogs Data', url='https://www.warcraftlogs.com/character/us/' + realm + '/' + character, color=color)
		
		if characterPortrait is not None:
			embed.set_thumbnail(url='https:' + characterPortrait[1] + '?' + str(time.time()))

		warcraftLogsMessage = '**Warcraft Logs Data'
		if characterClass is not None and characterNameRealm is not None:
			warcraftLogsMessage += " for " + characterNameRealm[1] + '-' + characterNameRealm[2] + " " + characterClass[1] + ' ' + characterClass[2] + '**\n'
			embed.description = characterClass[1] + ' ' + characterClass[2]
			warcraftLogsMessage += '<https://www.warcraftlogs.com/character/us/' + realm + '/' + character + '>\n'
		else:
			warcraftLogsMessage += '**\n'
		for RankingMetric in RankingMetrics:
			try:
				statsDataPage = await self.fetchWebpage('https://www.warcraftlogs.com/rankings/character_rankings_compact/' + characterID[1] + '/' + selectedRankingZone + '/' + RankingMetric)
			except:
				print("Exception while accessing statsDataPage")
				await self.bot.send_message(ctx.message.channel, 'An Exception has occurred for some reason.  Could be website not found, network things, cosmic rays, or I goofed up. Maybe try your request again?')
				return False
			statsData = statsPattern.findall(statsDataPage)
			if statsData is None:
				await self.bot.send_message(ctx.message.channel, 'No warcraftlogs data found, this is very likely a regex error.')
				return False
  
			if RankingMetric is 'hps':
				warcraftLogsMessage += ' ***HEALING:***\n'
			if RankingMetric is 'dps':
				warcraftLogsMessage += ' ***DAMAGE:***\n'
			didStuff = False
			embedData = ''
			for statData in statsData:
				difficulty = 'Unknown';
   
				if statData[2] is not '-':
					didStuff = True
					if statData[0] is '5': difficulty = '  **Mythic:**'
					if statData[0] is '4': difficulty = '  **Heroic:**'
					if statData[0] is '3': difficulty = '  **Normal:**'
					if statData[0] is '2': difficulty = '  **LFR Maybe?:**'
  
					warcraftLogsMessage += difficulty + '\n   Best Performance Avg -> ' + statData[2] + '\n   Median Performance Avg -> ' + statData[4] + '\n   Kills Ranked -> ' + statData[5] + '\n   All Star Points -> ' + statData[6] + ' Out of ' + statData[7] + ' Possible\n'
					embedData += difficulty + '\n   Best Performance Avg -> ' + statData[2] + '\n   Median Performance Avg -> ' + statData[4] + '\n   Kills Ranked -> ' + statData[5] + '\n   All Star Points -> ' + statData[6] + ' Out of ' + statData[7] + ' Possible\n'
			catName = 'Fix Me'
			if RankingMetric is 'hps':
				catName = '***HEALING***'
			if RankingMetric is 'dps':
				catName = '***DAMAGE***'
			embed.add_field(name=catName, value=embedData, inline=True)


		if didStuff:
			try:
				await self.bot.send_message(ctx.message.channel, embed=embed)
			except discord.HTTPException as e:
				print(e)
				await self.bot.send_message(ctx.message.channel, warcraftLogsMessage)
			return True
		else:
			await self.bot.send_message(ctx.message.channel, 'No warcraftlogs data found or bad regex')
			return False

	@commands.command(pass_context=True)
	async def wowtoken(self, ctx):
		await self.bot.send_typing(ctx.message.channel)
		tokenpattern = re.compile('\{"NA":\{"timestamp":(.*?)."raw":\{"buy":(.*?)."24min":(.*?),"24max":(.*?)."timeToSell":')
		try:
			tokenjson = urllib.request.urlopen('https://data.wowtoken.info/snapshot.json').read().decode('utf-8')
		except:
			await self.bot.send_message(ctx.message.channel, 'Couldn\'t access wowtoken.info')
			await self.bot.add_reaction(ctx.message, "\U0001F44E") # ThumbsDown
			return
		tokenmatch = tokenpattern.match(tokenjson)
		if tokenmatch is not None:
			await self.bot.send_message(ctx.message.channel, 'The WoWToken is currently at {:,} gold.'.format(int(tokenmatch.group(2))))
			print('!wowtoken -> {:,}'.format(int(tokenmatch.group(2))))
			await self.bot.add_reaction(ctx.message, "\U0001F44D") # ThumbsUp
		else:
			await self.bot.send_message(ctx.message.channel, 'Failed to parse out wowtoken pricing information')
			await self.bot.add_reaction(ctx.message, "\U0001F44E") # ThumbsDown

	def padString(self, string, padAmount, padStart = False, padCharacter = " "):
		while len(string) < padAmount:
			if padStart:
				string = padCharacter + string
			else:
				string += padCharacter
		return string

	def centerpadString(self, string, padAmount, padCharacter = " "):
		while len(string) < padAmount:
			string = padCharacter + string + padCharacter
		return string

	async def checkPermissions(self, ctx, command):
		if (ctx.message.server.owner == ctx.message.author):
			print("checkPermissions, user is server owner")
			return True
		if (ctx.message.author.id == self.bot.ADMINACCOUNT):
			print("checkPermissions, user is bot owner")
			return True
		#print (ctx.message.server.owner.id, ctx.message.author.id)
		return False

	@commands.command(pass_context=True)
	async def defaultguild(self, ctx, *args):
		if ctx.message.server is None:
			await self.bot.send_message(ctx.message.channel, 'This command must be run from a server, not a direct message')
			return False
		if not await self.checkPermissions(ctx, 'defaults'):
			await self.bot.send_message(ctx.message.channel, "You don't have permission to use this command; or if you do then I haven't finished programming this part")
			return False
		try:
			guild = args[0]
			realm = args[1]
			update = True
		except:
			msg = 'Usage: !defaultguild "GUILD" "REALM"'
			if (len(args)>0):
				msg = 'I was unable to understand what you meant.\n' + msg
			await self.bot.send_message(ctx.message.channel, msg)
			update = False
  
  
		serverid = ctx.message.server.id
		print(serverid)
		
		connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db='CaliBot', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `guild`, `realm` FROM `guild_defaults` WHERE `serverid`=%s"
				cursor.execute(sql, (serverid))
				result = cursor.fetchone()
				if update is False and result is not None:
					await self.bot.send_message(ctx.message.channel, 'Currently the guild and realm for ' + ctx.message.server.name + ' is set to <' + result['guild'] + '> on ' + result['realm'])
				print(serverid, result)
				if update is True:
					if result is None:
						sql = "INSERT INTO `guild_defaults` (`serverid`, `guild`, `realm`) VALUES(%s, %s, %s)"
						cursor.execute(sql, (serverid, guild, realm))
						connection.commit()
					else:
						sql = "UPDATE `guild_defaults` SET `guild` = %s, `realm` = %s WHERE `serverid` = %s LIMIT 1"
						cursor.execute(sql, (guild, realm, serverid))
						connection.commit()
						#print(result)
					await self.bot.send_message(ctx.message.channel, 'The default guild and realm for ' + ctx.message.server.name + ' has been set to <' + guild + '> on ' + realm) 
		finally:
			connection.close()

	@commands.command(pass_context=True)
	async def guildperf(self, ctx, *args):
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
		
		
		if (len(args) == 0 and ctx.message.server is not None):
			connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db='CaliBot', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			try:
				with connection.cursor() as cursor:
					sql = "SELECT `guild`, `realm` FROM `guild_defaults` WHERE `serverid`=%s"
					cursor.execute(sql, (ctx.message.server.id))
					result = cursor.fetchone()
					print(result)
					if result is not None:
						guild = result["guild"]
						realm = result["realm"]
						await self.bot.send_message(ctx.message.channel, 'Using <' + guild + '> on ' + realm + ' for server ' + ctx.message.server.name)
			finally:
				connection.close()


		#try:
		#	region = args[2]
		#except:
		region = "US"
			
		try:
			difficulty = args[2]
			if difficulty not in difficultyID:
				raise
		except:
			difficulty = "normal"
		try:
			raid = args[3]
			if raid not in raidID:
				raise
		except:
			raid = 'ant'
		print(guild, realm)
		
		try:
			guildList = await self.fetchWebpage("https://www.warcraftlogs.com/search/?term=" + urllib.parse.quote_plus(guild))
			print("https://www.warcraftlogs.com/search/?term=" + urllib.parse.quote_plus(guild))
		except urllib.error.HTTPError as e:
			print(e.reason)
			await self.bot.send_message(ctx.message.channel, 'I was unable to search warcraftlogs.com for that guild')
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
			await self.bot.send_message(ctx.message.channel, 'I was unable to find that guild on warcraftlogs.com, please check your typing and try again')
			return False
		print("GuildID: ", guildID)
		try:
			guildRankings = await self.fetchWebpage("https://www.warcraftlogs.com/rankings/guild/" + guildID + "/latest/")
			#print(guildRankings)
			serverMatchPattern = re.compile('var filterServer = (\d+);')
			serverMatch = serverMatchPattern.search(guildRankings)
			print(serverMatch)
			serverID = serverMatch[1]
			
			print("Warcraftlogs ServerID:", serverID)
		except urllib.error.HTTPError as e:
			print(e)
			await self.bot.send_message(ctx.message.channel, 'I was unable to parse the server id for that guild, tell Cali about it')
			return False
		
		#return
		await self.bot.send_typing(ctx.message.channel)
		urls = { }
		urls['DAMAGE'] = 'https://www.warcraftlogs.com/rankings/table/dps/' + raidID[raid] + '/-1/'+ difficultyID[difficulty] + '/25/1/DPS/Any/0/' + serverID + '/0/0/' + guildID + '/?search=&page=1&keystone=0'
		urls['HEALING'] = 'https://www.warcraftlogs.com/rankings/table/hps/' + raidID[raid] + '/-1/'+ difficultyID[difficulty] + '/25/1/Healers/Any/0/' + serverID + '/0/0/' + guildID + '/?search=&page=1&keystone=0'
		urls['TANKING'] = 'https://www.warcraftlogs.com/rankings/table/hps/' + raidID[raid] + '/-1/'+ difficultyID[difficulty] + '/25/1/Tanks/Any/0/' + serverID + '/0/0/' + guildID + '/?search=&page=1&keystone=0'
		#guild = '231680'
		#url = 'https://www.warcraftlogs.com/rankings/table/dps/17/-1/3/25/1/Any/Any/0/172/0/0/231680/?search=&page=1&keystone=0'
		#url = 'https://www.warcraftlogs.com/rankings/table/hps/17/-1/3/25/1/Healers/Any/0/172/0/0/231680/?search=&page=1&keystone=0'
		message = '```Guild Performance for <' + guild + '> ' + difficulty.capitalize() + ' ' + RAIDNAME[raid] + '\n'
		didStuff = False

		for url in urls:
			print(urls[url])
			message += '\n' + self.centerpadString(url, 45, "=") + '\n'
			try:
				guildData = await self.fetchWebpage(urls[url])
			except:
				print('Failed to get guild performance data')
				await self.bot.send_message(ctx.message.channel, 'Something bad happened')

			characterPattern = re.compile('<tr.*?<td class="rank.*?">(\d+)<.*?<a class="main-table-link.*?>(.*?)</a>.*?<td class="main-table-number primary players-table-score".*?>(\d+).*?</tr>', re.DOTALL)

			#message += '   Name    Realm Rank  Score\n'
			for character in characterPattern.findall(guildData):
				didStuff = True
				message += self.padString(character[1] + ':', 15) + self.padString('Realm Rank -> ' + self.padString(character[0], 3, True) + ',', 19, False, ' ') + 'Score -> ' + self.padString(character[2], 3, True) + '\n'
				print(character[0], character[1], character[2])
		message += '```'
		
		
		if didStuff:
			await self.bot.send_message(ctx.message.channel, message)
		else:
			await self.bot.send_message(ctx.message.channel, 'I was unable to find the right data')
		#else:
		#	await self.bot.send_message(ctx.message.channel, 'Unable to find data, bad regex probably')
		#	print('Unable to find data, bad regex probably')
			
		
		
	
	@commands.command(pass_context=True)
	async def gear(self, ctx, *, toon = '*'):
		await self.bot.send_typing(ctx.message.channel)

		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await self.bot.send_message(ctx.message.channel, 'Unable to find character and realm name, please double check the command you typed')
			return False
 
		gearSlots = [ 'head', 'neck', 'shoulder', 'back', 'chest', 'wrist', 'hands', 'waist', 'legs', 'feet', 'finger1', 'finger2', 'trinket1', 'trinket2', 'mainHand', 'offHand' ] # Left out shirt, tabard

		try:
			itemsJSON = urllib.request.urlopen('https://us.api.battle.net/wow/character/' + realm + '/' + character + '?fields=items,guild&locale=en_US&apikey=' + self.bot.APIKEY_WOW).read().decode('utf-8')
		except urllib.error.HTTPError as e:
			print(e.reason,character,realm)
			if e.reason == "Service Unavailable":
				print("Battle.net services are down")
				await self.bot.send_message(ctx.message.channel, "The Battle.net API is down, try again later")
			else:  
				await self.bot.send_message(ctx.message.channel, 'Unable to access character data, check for typos or invalid realm')
				print("Unable to access api for",character,realm)
				return False
		try:
			toon = json.loads(itemsJSON)
		except:
			await self.bot.send_message(ctx.message.channel, 'Unable to parse JSON data, probably Cali\'s fault')
			return False
		#except discord.HTTPException as e:

		gearData = ""
		msg = 'Gear for **' + toon['name'] + '** of **' + toon['realm'] + '**'
		msg += ' (<https://worldofwarcraft.com/en-us/character/' + realm + '/' + character + '>)'
		msg += '\n**Item Level**: *' + str(toon['items']['averageItemLevelEquipped']) + '* equipped, *' + str(toon['items']['averageItemLevel']) + '* total'
 
 
		for gear in gearSlots:
			#embed.add_field(name="Gear", value=gearData, inline=True)
			#gearData = ""
			if gear in toon['items']:
				msg += '\n' + str(toon['items'][gear]['itemLevel']) + ' - ' + gear.capitalize() + ' - ' + toon['items'][gear]['name'] + ' - <' + WOWHEAD_ITEMURL + str(toon['items'][gear]['id']) + '>'
				gearData += str(toon['items'][gear]['itemLevel']) + ' - ' + gear.capitalize() + ' - [' + toon['items'][gear]['name'] + '](' + WOWHEAD_ITEMURL + str(toon['items'][gear]['id']) + ')\n'
				#embed.add_field(name=gear.capitalize(), value=str(toon['items'][gear]['itemLevel']) + ' - ' + gear.capitalize() + ' - [' + toon['items'][gear]['name'] + '](' + WOWHEAD_ITEMURL + str(toon['items'][gear]['id']) + ')', inline=False)
			else:
				msg += '\n' + gear.capitalize() + ' is empty!'
				gearData += gear.capitalize() + ' is empty!\n'
				#embed.add_field(name="Gear", value=gearData, inline=True)

 
 
		if (toon['class']-1) < len(CLASSCOLORS):
			color = discord.Color(int(CLASSCOLORS[toon['class']-1], 16))
		else:
			color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16))
		print(toon['class'], color)
		embedTitle = toon['name'] + ' of ' + toon['realm']
		if 'guild' in toon:
			if 'name' in toon['guild']:
				embedTitle += ' <' + toon['guild']['name'] + '>'
		embed=discord.Embed(title=embedTitle, description=gearData, url='https://worldofwarcraft.com/en-us/character/' + realm + '/' + character, color=color)
		embed.set_thumbnail(url='https://render-us.worldofwarcraft.com/character/' + toon['thumbnail'] + '?' + str(time.time()))
		embed.add_field(name="Equipped Item Level", value=str(toon['items']['averageItemLevelEquipped']), inline=True)
		embed.add_field(name="Total Item Level", value=str(toon['items']['averageItemLevel']), inline=True)
		print(toon['name'] + '** of **' + toon['realm'] + str(toon['items']['averageItemLevelEquipped']) + '* equipped, *' + str(toon['items']['averageItemLevel']) + '* total')
		print('https://worldofwarcraft.com/en-us/character/' + realm + '/' + character)
		print('https://render-us.worldofwarcraft.com/character/' + toon['thumbnail'])

		try:
			await self.bot.send_message(ctx.message.channel, embed=embed)
		except discord.HTTPException as e:
			print(e)
			await self.bot.send_message(ctx.message.channel, msg)
		return True
	@commands.command(pass_context=True)
	async def armory(self, ctx, *, toon = '*'):
		await self.bot.send_typing(ctx.message.channel)
		character, realm = self.getCharacterRealm(ctx.message.author, toon)
		if character is None or realm is None:
			await self.bot.send_message(ctx.message.channel, 'Unable to find character and realm name, please double check the command you typed')
			return False
		 
		try:
			characterJSON = urllib.request.urlopen('https://us.api.battle.net/wow/character/' + realm + '/' + character + '?fields=guild,progression,items,achievements&locale=en_US&apikey=' + self.bot.APIKEY_WOW).read().decode('utf-8')
			if (characterJSON == "{}"):
				await self.bot.send_message(ctx.message.channel, 'Empty JSON Data, this character probably doesn\'t exist or something.')
				return False
			try:
				toon = json.loads(characterJSON)
			except:
				print('Unable to parse JSON data, probably Cali\'s fault')
				await self.bot.send_message(ctx.message.channel, 'Unable to parse JSON data, probably Cali\'s fault')
				return False
		except urllib.error.HTTPError as e:
			if e.reason == "Service Unavailable":
				await self.bot.send_message(ctx.message.channel, 'Battle.net API services are down')
				#print("Battle.net services are down")
				#return await doArmoryLookup(message)
			else:  
				print("Unable to access api for",character,realm)
				await self.bot.send_message(ctx.message.channel, 'Unable to access api for ' + character + ' - ' + realm)
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
		 
		RAIDS = [ 'Antorus, the Burning Throne', 'Tomb of Sargeras', 'The Nighthold', 'Trial of Valor', 'The Emerald Nightmare' ]
		RAID_AOTC = { 'Antorus, the Burning Throne': 12110, 'Tomb of Sargeras': 11874, 'The Nighthold': 11195, 'Trial of Valor': 11581, 'The Emerald Nightmare': 11194 }
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
		 
		embed.add_field(name='Progression', value=progressionMessage)

		hasAOTC = True
		if 12111 in toon['achievements']['achievementsCompleted']:
			embed.description = 'Has *Cutting Edge* for the current tier'
		elif 12110 in toon['achievements']['achievementsCompleted']:
			embed.description = 'Has *AOTC* for the current tier'
		else:
			hasAOTC = False
			embed.description = 'Doesn\'t Have AOTC for the current tier'
		  
		try:
			await self.bot.send_message(ctx.message.channel, embed=embed)
		except discord.HTTPException as e:
			characterProgress = toon['name'] + ' - ' + toon['realm']
			characterProgress += '\nEquipped Item Level: ' + str(toon['items']['averageItemLevelEquipped']) + ' Total item Level: ' + str(toon['items']['averageItemLevel'])
			if hasAOTC:
				characterProgress += '\nHas AOTC for the current tier'
			else:
				characterProgress += '\nDoesn\'t have AOTC for the current tier'
				characterProgress += '\n' + progressionMessage
			print(e)
			await self.bot.send_message(ctx.message.channel, characterProgress)
		return True

def setup(bot):
	bot.add_cog(WoW(bot))