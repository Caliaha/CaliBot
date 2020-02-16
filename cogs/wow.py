import asyncio
import discord
from discord.ext import commands
import json
import pymysql.cursors
import re
from stuff import BoxIt, deleteMessage, doThumbs, fetchWebpage, postWebdata, superuser
import time
import urllib.parse

class WoW(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

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

	@commands.command()
	@deleteMessage()
	@doThumbs()
	async def mythic(self, ctx, *args):
		"""Shows raider.io mythic+ scores for a guild"""

		validArguments = { '-g': 'guild', '-s': 'realm', '-t': 'threshold', '-f': 'fullWait' }
		arguments = { }
		
		if len(args) >= 1 and (args[0] == 'help' or args[0] == '-h'):
			await ctx.send('Usage: !mythic -g "guild name" -s "realm name" -t [integer] -f\nAll arguments are optional.')
			return True
		
		for i in range(len(args)):
			if args[i] in validArguments:
				if i+1 < len(args):
					arguments[validArguments[args[i]]] = args[i+1]
				else:
					arguments[validArguments[args[i]]] = True
		try:
			guild = arguments['guild']
		except:
			guild = False
		try:
			realm = arguments['realm']
		except:
			realm = "Cairne"
		try:
			threshold = int(arguments['threshold'])
		except:
			threshold = 50

		try:
			arguments['fullWait']
			fullWait = True
		except:
			fullWait = False
		
		fullWaitWarning = ''
		if fullWait:
			fullWaitWarning = 'I have been requested to wait out the full duration of the queue, this may cause problems!\n'

		if (not guild and ctx.guild is not None):
			guild, realm, updateableMessage = await self.fetchGuildFromDB(ctx)

		#await ctx.trigger_typing()
		async with ctx.channel.typing():
			try:
				headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0' }
				print(guild, realm)
				rawJSON = await fetchWebpage(self, 'https://raider.io/api/search?term=' + urllib.parse.quote_plus(guild))
			except Exception as e:
				await ctx.send('Error searching for guild\nUsage: !mythic -g "guild" -s "realm"')
				print('!mythic', e)
				return False

			guilds = json.loads(rawJSON)
			guildData = None
			try:
				for guildJSON in guilds['matches']:
					print(guildJSON['data']['realm']['name'])
					print(guildJSON['data']['name'])
					if guildJSON['type'] == 'guild' and guildJSON['data']['realm']['name'].lower() == realm.lower() and guildJSON['data']['name'].lower() == guild.lower():
						guild = guildJSON['data']['name']
						realm = guildJSON['data']['realm']['slug']
						guildData = guildJSON
						print("Found guild")
			except:
				print('Unable to find guild')
				await ctx.send('Error searching for guild\nUsage: !mythic -g "guild" -s "realm"')
				return False
			
			if guildData is None:
				print('Unable to find guild')
				await ctx.send('Error searching for guild\nUsage: !mythic -g "guild" -s "realm"')
				return False

			embed=discord.Embed(title='Mythic+ Data for {} on {}'.format(guild, realm.capitalize()), url='https://raider.io/guilds/us/{}/{}/roster#mode=mythic_plus'.format(urllib.parse.quote(realm), urllib.parse.quote(guild)), color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
			embed.add_field(name='Status', value='N/A', inline=True)
			embed.add_field(name='Time Left', value='N/A', inline=True)
			embed.add_field(name='Queue Position', value='N/A', inline=True)
			embed.add_field(name='Crawled', value='N/A', inline=True)
			
			try:
				updateableMessage
			except Exception as e:
				print(e)
				updateableMessage = await ctx.send(embed=embed)

			try:
				embed.set_field_at(0, name='Status', value='Unknown')
				embed.description = fullWaitWarning
				await updateableMessage.edit(embed=embed, content='')

				data = { 'realmId': guildData['data']['realm']['id'], 'realm': guildData['data']['realm']['name'], 'region': guildData['data']['region']['slug'], 'guild': guildData['data']['name'], 'numMembers': 50 }

				postJSON = json.loads(await postWebdata(self, 'https://raider.io/api/crawler/guilds', data))
				checkStatus = True
				startTime = time.time()
				while checkStatus:
					status = json.loads(await fetchWebpage(self, 'https://raider.io/api/crawler/monitor?batchId=' + postJSON['jobData']['batchId']))
					try:
						print(status['batchInfo']['status'])
						try:# It's try/excepts all the way down
							embed.set_field_at(2, name='Queue Position', value='{}/{}'.format(status['batchInfo']['jobs'][0]['positionInQueue'], status['batchInfo']['jobs'][0]['totalItemsInQueue']), inline=True)
						except:
							pass
						embed.set_field_at(0, name='Status', value='{}'.format(status['batchInfo']['status']), inline=True)
						embed.set_field_at(1, name='Time Left', value='{:.0f}'.format((startTime + 120 - time.time())), inline=True)
						embed.set_field_at(3, name='Crawled', value='{}/{}'.format(status['batchInfo']['totalJobsRemaining'], status['batchInfo']['numCrawledEntities']), inline=True)
						await updateableMessage.edit(embed=embed, content='')
					except Exception as e:
						print(status)
						print("Could not update !mythic updateable message", e)
					if  startTime + 120 < time.time():
						if not fullWait:
							checkStatus = False
							print("breaking from checkStatus because alotted time ran out")
					if ((status['batchInfo']['status'] != 'waiting' and status['batchInfo']['status'] != 'active')):
						checkStatus = False
						print("breaking from checkStatus because: " + status['batchInfo']['status'])
					await asyncio.sleep(0.4)
				print("Done requesting update from raider.io")
				#await ctx.trigger_typing()
				await asyncio.sleep(6) # Just in case website still needs a little time to update things
			except:
				try:
					await updateableMessage.edit(content='Attempting to update website before I request the data\nStatus: Failed\nRaider.io will process the update at some point in the future but I am not waiting for it\nWill use older information', delete_after=60)
				except Exception as e:
					print("Could not update !mythic updateable message", e)
				print("Failed to request raider.io guild update")

			try:
				headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0' }
				rawJSON = urllib.request.urlopen(urllib.request.Request(f'https://raider.io/api/mythic-plus/rankings/characters?region=us&realm={urllib.parse.quote(realm)}&guild={urllib.parse.quote(guild)}&season=season-bfa-4&class=all&role=all&page=0', data=None, headers=headers)).read().decode('utf-8')
			except:
				try:
					rawJSON = await fetchWebpage(self, f'https://raider.io/api/mythic-plus/rankings/characters?region=us&realm={urllib.parse.quote(realm)}&guild={urllib.parse.quote(guild)}&season=season-bfa-4&class=all&role=all&page=0')
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
			didSomething = False
			for character in roster['rankings']['rankedCharacters']:
				didSomething = True
				if float(character['score']) >= threshold:
					box.addRow([ character['character']['name'], character['character']['spec']['name'], float('{0:.2f}'.format(character['score'])) ])

			box.sort(2, True)
			box.setHeader( ['Name', 'Spec', 'Mythic+ Score' ] ) # FIX ME Shouldn't have to put header after the sort
			message = '```' + box.box()
			
			if not didSomething:
				message = f'```No data found for {guild}\nThis is either an error or a new mythic+ season has started and no runs have been completed yet.'

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

			try:
				await updateableMessage.delete()
			except:
				print("Could not delete !mythic updateable message")
			return True

def setup(bot):
	bot.add_cog(WoW(bot))