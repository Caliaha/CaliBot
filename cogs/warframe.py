import datetime
import discord
from discord.ext import tasks, commands
import json
import logging
import pymysql.cursors
import re
from stuff import BoxIt, doThumbs, fetchWebpage, sendBigMessage
import time


class Warframe(commands.Cog):
	"""TBD"""
	def __init__(self, bot):
		self.bot = bot
		self.logger = logging.getLogger(f'CaliBot.{__name__}')
		# MAYBE DO SOMETHING ABOUT THIS
		self.relics = { 'lith': 'VoidT1', 'meso': 'VoidT2', 'neo': 'VoidT3', 'axi': 'VoidT4', 'reqium': 'VoidT5' }
		self.missionTypes = { 'capture': 'MT_CAPTURE', 'defense': 'MT_DEFENSE', 'excavate': 'MT_EXCAVATE', 'interception': 'MT_TERRITORY', 'mobiledefense': 'MT_MOBILE_DEFENSE', 'rescue': 'MT_RESCUE', 'sabotage': 'MT_SABOTAGE', 'survival': 'MT_SURVIVAL' }
		self.relicsR = { 'VoidT1': 'Lith', 'VoidT2': 'Meso', 'VoidT3': 'Neo', 'VoidT4': 'Axi', 'VoidT5': 'Reqium' }
		self.missionTypesR = { 'MT_CAPTURE': 'Capture', 'MT_DEFENSE': 'Defense', 'MT_EXCAVATE': 'Excavate', 'MT_MOBILE_DEFENSE': 'Mobile Defense', 'MT_RESCUE': 'Rescue', 'MT_SABOTAGE': 'Sabotage', 'MT_SURVIVAL': 'Survival', 'MT_TERRITORY': 'Interception' }
		self.activeAlerts = { }
		#self.activeAlerts = activeAlerts
		self.alreadyAlerted = { }
		self.activeVoidFissures = [ ]
		self.cetusDawn = 0
		self.vallisHot = 0
		self.lastPresence = ''
		self.updateLoop.start()
		self.playingStatus.start()
		
		with open('data/solNodes.json', 'r') as file:
			self.solNodes = json.load(file)

	def cog_unload(self):
		self.updateLoop.cancel()
		self.playingStatus.cancel()

	def loadAlerts(self):
		self.activeAlerts.clear()
		self.activeAlerts['transitions'] = { 'cetus': [ ] }
		self.activeAlerts['void'] =  { 'VoidT1': [ ], 'VoidT2': [ ], 'VoidT3': [ ], 'VoidT4': [ ], 'VoidT5': [ ] }
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = 'SELECT * FROM `wf_alerts`'
				cursor.execute(sql)
				for result in cursor.fetchall():
					alert = { }
					alert['alertID'] = result['id']
					alert['ownerID'] = result['ownerID']
					alert['guildID'] = result['guildID']
					alert['channelID'] = result['channelID']
					alert['alertType'] = ('CHANNEL', 'PERSONAL')[result['type']]
					alert['runOnce'] = result['runOnce']
					alert['info1'] = result['info1']
					alert['info2'] = result['info2']
					
					if result['id'] not in self.alreadyAlerted:
						self.alreadyAlerted[result['id']] = [ ]
					
					if result['category'] == 0: # Void Relics
						print('Adding alert: ', alert)
						self.activeAlerts['void'][result['info2']].append(alert)
					if result['category'] == 1: # Plains of Eidolon Day/Night transitions
						self.activeAlerts['transitions'][result['info1']].append(alert)
		except Exception as e:
			self.logger.error(f'loadAlerts {e}')
		finally:
			connection.close()

	async def triggerCycleAlerts(self, place, cycle, endTime):
		thumbnails = { 'cetus': {
							'day': 'http://clipart-library.com/img/1374078.png',
							'night': 'http://clipart-library.com/new_gallery/12-123586_png-file-svg-moon-svg.png'
							}
					}
		for alert in self.activeAlerts['transitions'][place]:
			if alert['info2'] != cycle and alert['info2'] != 'both':
				continue
			channel = False
			user = self.bot.get_user(int(alert['ownerID']))
			if alert['alertType'] == "PERSONAL":
				if user:
					channel = user
			else:
				guild = self.bot.get_guild(int(alert['guildID']))
				tchannel = guild.get_channel(int(alert['channelID']))
				
				if tchannel:
					channel = tchannel
			
			if not channel:
				return False

			expireDate = time.time() + endTime

			expireDate = datetime.datetime.fromtimestamp(expireDate).strftime('%Y-%m-%d %H:%M:%S')
			embed = discord.Embed(title='Transition Alert', description='Beep', url='https://www.google.com', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
			embed.description = f"{user.mention} It's now {cycle} in {place}!"
			embed.set_thumbnail(url=thumbnails[place][cycle])
			embed.set_footer(text = f'Alert ID:{alert["alertID"]}, Owner ID: {alert["ownerID"]}, {expireDate}')
			msg = await channel.send(embed=embed)
			
			try:
				connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
				with connection.cursor() as cursor:
					sql = 'INSERT INTO `wf_outstanding` (`messageID`, `expires`, `type`, `userID`, `guildID`, `channelID`) VALUES(%s, %s, %s, %s, %s, %s)'
					cursor.execute(sql, (msg.id, expireDate, alert['alertType'], alert['ownerID'], alert['guildID'], alert['channelID']))
					connection.commit()
			except Exception as e:
				self.logger.error(f'Error adding to wf_outstanding {e}')
			finally:
				connection.close()

	async def doAlertEmbed(self, void, alert):
		channel = False
		user = self.bot.get_user(int(alert['ownerID']))
		if alert['alertType'] == "PERSONAL":
			if user:
				channel = user
		else:
			guild = self.bot.get_guild(int(alert['guildID']))
			tchannel = guild.get_channel(int(alert['channelID']))
			
			if tchannel:
				channel = tchannel
		
		if not channel:
			return False

		startDate = int(re.sub('[^0-9]', '', str(void["Activation"]["$date"])))/1000
		expireDate = int(re.sub('[^0-9]', '', str(void["Expiry"]["$date"])))/1000

		startDate = datetime.datetime.fromtimestamp(startDate).strftime('%Y-%m-%d %H:%M:%S')
		expireDate = datetime.datetime.fromtimestamp(expireDate).strftime('%Y-%m-%d %H:%M:%S')
		embed = discord.Embed(title='Void Relic Alert', description='Beep', url='https://www.google.com', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
		embed.description = f'{user.mention} A void relic fissure meeting your alert requirements has appeared!\nEra: {self.relicsR[void["Modifier"]]}\nMission Type: {self.missionTypesR[void["MissionType"]]}\nNode: {self.solNodes[void["Node"]]["value"]}\nEnemy: {self.solNodes[void["Node"]]["enemy"]}\nStarts At {startDate}\nExpires At {expireDate}'
		embed.set_thumbnail(url='https://vignette.wikia.nocookie.net/warframe/images/a/ae/VoidProjectionsIronD.png')
		embed.set_footer(text = f'Alert ID:{alert["alertID"]}, Owner ID: {alert["ownerID"]}, {startDate}-{expireDate}')
		msg = await channel.send(embed=embed)
		
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = 'INSERT INTO `wf_outstanding` (`messageID`, `missionID`, `expires`, `type`, `userID`, `guildID`, `channelID`) VALUES(%s, %s, %s, %s, %s, %s, %s)'
				cursor.execute(sql, (msg.id, void['_id']['$oid'], expireDate, alert['alertType'], alert['ownerID'], alert['guildID'], alert['channelID']))
				connection.commit()
		except Exception as e:
			self.logger.error(f'Error adding to wf_outstanding {e}')
		finally:
			connection.close()
		
		print('RUNONCE:', alert['runOnce'])
		#if runonce: TO DO
		#	self.deleteAlert(alertID)
		

	async def purgeOutdatedAlerts(self, purgeAll = False):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = f'SELECT * FROM `wf_outstanding` {"" if purgeAll else "WHERE `expires` < NOW()"}'
				cursor.execute(sql)
				results = cursor.fetchall()
				for result in results:
					if result['missionID'] in self.activeVoidFissures:
						pass
						#continue
					channel = False
					if result['type'] == "CHANNEL":
						try:
							guild = self.bot.get_guild(int(result['guildID']))
							channel = guild.get_channel(int(result['channelID']))
						except Exception as e:
							print(e)
					else:
						try:
							channel = self.bot.get_user(int(result['userID']))
						except:
							pass

					try:
						msg = await channel.fetch_message(int(result['messageID']))
						await msg.delete()
					except Exception as e:
						print("Couldn't find message to delete it", e, result['messageID'])
					
					sql = 'DELETE FROM `wf_outstanding` WHERE `id` = %s'
					cursor.execute(sql, (result['id']))
					connection.commit()
		except Exception as e:
			self.logger.error(f'Error adding to wf_outstanding {e}')
		finally:
			connection.close()
		pass

	def getSimpleTime(self, totalSeconds):
		hours, remainder = divmod(totalSeconds, 3600)
		minutes, seconds = divmod(remainder, 60)
		
		dateString = ''
		if hours > 0:
			dateString = f'{int(hours)}h:'
		return f'{dateString}{int(minutes)}m'

	@tasks.loop(seconds=10)
	async def playingStatus(self):
		if self.cetusDawn == 0 or self.vallisHot == 0:
			return
		currentTime = time.time()
		while currentTime >= self.cetusDawn: # Old date is expired, so create new expire date based on old one until updateLoop fixes it
			self.cetusDawn = self.cetusDawn + (150 * 60)
		#if currentTime >= self.vallisHot:

		#Next DAWN = self.cetusDawn
		#100 Minutes Day + 50 Minutes Day = 1 Cycle
		#if self.cetusDawn - currentTime > (100 * 60) = Still day?
		#print('Vallis:', datetime.datetime.fromtimestamp(self.vallisHot).strftime('%Y-%m-%d %H:%M:%S'))
		#print('Vallis:', datetime.datetime.fromtimestamp(self.vallisHot-currentTime).strftime('%M:%S'))
		#print(datetime.datetime.fromtimestamp(self.cetusDawn).strftime('%Y-%m-%d %H:%M:%S'))
		#print(datetime.datetime.fromtimestamp(self.cetusDawn-currentTime).strftime('%M:%S'))
		#vallisCycleLength = (26 * 60) + 40
		#print('Loop', int(currentTime) - self.vallisHot, vallisCycleLength)
		#print('Loop', (int(currentTime) - self.vallisHot) % vallisCycleLength)
		#print(self.cetusDawn - (currentTime + (50*60)), self.cetusDawn, currentTime)
		#if self.vallisHot - currentTime > (20 * 60):
		#	print('Vallis is Hot', 'Cold in')
		#else:
		#	print('Vallis is Cold', 'Warm in', datetime.datetime.fromtimestamp(self.cetusDawn-currentTime).strftime('%M:%S'))
		print('Current Time:', datetime.datetime.fromtimestamp(currentTime).strftime('%Y-%m-%d %H:%M:%S'))
		print('Cetus:', datetime.datetime.fromtimestamp(self.cetusDawn).strftime('%Y-%m-%d %H:%M:%S'))
		print(self.cetusDawn - currentTime, 100 * 60, self.cetusDawn, currentTime)
		if self.cetusDawn - currentTime >= (50 * 60): # Not night time
			if self.lastPresence.startswith('☀'):
				await self.triggerCycleAlerts('cetus', 'day', self.cetusDawn-(currentTime+(50*60)))
			currentStatus = f'🌙 in {self.getSimpleTime(self.cetusDawn-(currentTime+(50*60)))}'
		else:
			if self.lastPresence.startswith('🌙'):
				await self.triggerCycleAlerts('cetus', 'night', self.cetusDawn - (currentTime))
			currentStatus = f'☀️ in {self.getSimpleTime(self.cetusDawn - (currentTime))}'
			#currentStatus = f'D:{datetime.datetime.fromtimestamp(self.cetusDawn-currentTime).strftime("%Mm")}'
		#self.logger.debug(currentStatus)
		if currentStatus != self.lastPresence:
			self.lastPresence = currentStatus
			try:
				await self.bot.change_presence(activity=discord.Game(name=self.lastPresence))
			except:
				self.logger.warn('Failed to change presence')


	@tasks.loop(minutes=5.0)
	async def updateLoop(self):
		try:
			page = await fetchWebpage(self, 'http://content.warframe.com/dynamic/worldState.php')
			data = json.loads(page)
		except Exception as e:
			self.logger.error('Failed to parse worldState json {e}')
		self.activeVoidFissures.clear()
		try:
			self.cetusDawn = int(re.sub('[^0-9]', '', str(data['SyndicateMissions'][17]['Expiry']['$date'])))/1000
			self.vallisHot = int(re.sub('[^0-9]', '', str(data['SyndicateMissions'][16]['Activation']['$date'])))/1000
		except Exception as e:
			print(e)
		for void in data['ActiveMissions']:
			self.activeVoidFissures.append(void['_id']['$oid'])
			for alert in self.activeAlerts['void'][void['Modifier']]:
				if alert['info1'] == void['MissionType'] and void['_id']['$oid'] not in self.alreadyAlerted[alert['alertID']]:
					print('Doing alert')
					self.alreadyAlerted[alert['alertID']].append(void['_id']['$oid'])
					if alert['runOnce']:
						pass # Fix me later, idk if I can delete while iterating
						#del alert
					await self.doAlertEmbed(void, alert)
		try:
			for alertID in self.alreadyAlerted:
				for missionID in self.alreadyAlerted[alertID]:
					if missionID not in self.activeVoidFissures:
						print('Deleting from self.activeVoidFissures', alertID, missionID)
						self.alreadyAlerted[alertID].remove(missionID)
		except Exception as e:
			self.logger.warn(e)
		await self.purgeOutdatedAlerts()

	@commands.command()
	async def ttest(self, ctx, place, cycle):
		await self.triggerCycleAlerts(place, cycle, 30)

	#@tasks.loop(minutes=5.0)
	#async def updateLoop(self):
	@commands.command()
	async def wf(self, ctx):
		page = await fetchWebpage(self, 'http://content.warframe.com/dynamic/worldState.php')
		data = json.loads(page)
		self.activeVoidFissures.clear()
		for void in data['ActiveMissions']:
			self.activeVoidFissures.append(void['_id']['$oid'])
			for alert in self.activeAlerts['void'][void['Modifier']]:
				if alert['missionType'] == void['MissionType'] and void['_id']['$oid'] not in self.alreadyAlerted[alert['alertID']]:
					print('Doing alert')
					self.alreadyAlerted[alert['alertID']].append(void['_id']['$oid'])
					if alert['runOnce']:
						pass # Fix me later, idk if I can delete while iterating
						#del alert
					await self.doAlertEmbed(void, alert)
		try:
			for alertID in self.alreadyAlerted:
				for missionID in self.alreadyAlerted[alertID]:
					print(missionID)
					if missionID not in self.activeVoidFissures:
						print('Deleting from self.activeVoidFissures', alertID, missionID)
						self.alreadyAlerted[alertID].remove(missionID)
		except Exception as e:
			print(e)
		await self.purgeOutdatedAlerts()

	@updateLoop.before_loop
	async def before_updateLoop(self):
		self.loadAlerts()
		await self.bot.wait_until_ready()

	@playingStatus.before_loop
	async def before_playingStatus(self):
		await self.bot.wait_until_ready()

	async def addAlert(self, category, ownerID, guildID, channelID, personal, runOnce, info1, info2):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = 'INSERT INTO `wf_alerts` (`category`, `ownerID`, `guildID`, `channelID`, `type`, `runOnce`, `info1`, `info2`) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)'
				cursor.execute(sql, (category, ownerID, guildID, channelID, personal, runOnce, info1, info2))
				connection.commit()
		except Exception as e:
			self.logger.error(f'addAlert: {e}')
		finally:
			connection.close()
		
		self.loadAlerts()


	@commands.group(invoke_without_command=True)
	@doThumbs()
	async def wfAlert(self, ctx):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = sql = 'SELECT * FROM `wf_alerts` WHERE `guildID` = %s or `ownerID` = %s'
				cursor.execute(sql, (ctx.guild.id, ctx.author.id))
				
				box = BoxIt()
				results = cursor.fetchall()
				for result in results:
					box.addRow([ result['id'], ctx.guild.get_member(int(result['ownerID'])), "cycle" if result['category'] else "void", "PERSONAL" if result['type'] else "CHANNEL", result['info1'] if result['category'] else self.missionTypesR[result['info1']], result['info2'] if result['category'] else self.relicsR[result['info2']] ])
				box.sort(2, True)
				box.setHeader([ 'ID', 'User', 'Category', 'Type', 'Info1', 'Info2' ])
				box.setTitle('Warframe Alerts')

				await sendBigMessage(self, ctx, f'You can only delete CHANNEL alerts if you are an officer\n{box.box()}', '```', '```',)
				return True
		finally:
			connection.close()

	@wfAlert.command()
	@doThumbs()
	async def add(self, ctx, category, *args):		
		#relics = { 'lith': 'VoidT1', 'meso': 'VoidT2', 'neo': 'VoidT3', 'axi': 'VoidT4', 'reqium': 'VoidT5' }
		#missionTypes = { 'capture': 'MT_CAPTURE', 'defense': 'MT_DEFENSE', 'excavate': 'MT_EXCAVATE', 'interception': 'MT_TERRITORY', 'mobiledefense': 'MT_MOBILE_DEFENSE', 'rescue': 'MT_RESCUE', 'sabotage': 'MT_SABOTAGE', 'survival': 'MT_SURVIVAL'  } # Missing artifact and intel and maybe others
		
		if category == 'void':
			era = None
			mission = None
			personal = True
			runOnce = False
			for arg in args:
				arg = arg.lower()
				if arg in self.relics:
					era = self.relics[arg]
				if arg in self.missionTypes:
					mission = self.missionTypes[arg]
				if arg == 'runonce':
					runOnce = True
				if arg == 'channel':
					personal = False

			if (era and mission):		
				await self.addAlert(0, ctx.author.id, ctx.guild.id, ctx.channel.id, personal, runOnce, mission, era)
				await ctx.send(f'I have created a {"ONE-SHOT " if runOnce else ""}{"PERSONAL" if personal else "CHANNEL"} alert for a {self.relicsR[era]} {self.missionTypesR[mission]}!')
				return True
			else:
				await ctx.send("I couldn't understand that, usage:\n!wfAlert void lith capture [runonce] [channel]")
				return False

		if category == 'cycle':
			place = None
			cycle = None
			runOnce = False
			personal = True
			for arg in args:
				arg = arg.lower()
				if arg == 'cetus' or arg == 'vallis':
					place = arg
				if arg == 'day' or arg == 'night' or arg == 'both':
					cycle = arg
				if arg == 'runonce':
					runOnce = True
				if arg == 'channel':
					personal = False
				
		if (place and cycle):
			await self.addAlert(1, ctx.author.id, ctx.guild.id, ctx.channel.id, personal, runOnce, place, cycle)
			await ctx.send(f'I have created a {"ONE-SHOT " if runOnce else ""}{"PERSONAL" if personal else "CHANNEL"} alert for a {place} {"cycle change" if cycle == "both" else cycle}!')
			return True
		else:
			await ctx.send("I did not understand that.\nUsage: !wfAlert add cycle cetus [day|night|both] [runonce] [channel]")
			return False

	@wfAlert.command()
	@doThumbs()
	async def delete(self, ctx, alertID: int):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `ownerID`, `guildID`, `channelID`, `type` FROM `wf_alerts` WHERE `id` = %s"
				cursor.execute(sql, (alertID))
				result = cursor.fetchone()
				if not result:
					return False
				deleteOk = False
				if result['ownerID'] == str(ctx.author.id) and result['type']: # We are the owner and it's a personal alert for us
					deleteOk = True
				if result['guildID'] == str(ctx.guild.id) and not result['type']: # It's a channel message for our guild, ok to delete (ADD PERMISSIONS CHECK LATER)
					deleteOk = True

				if deleteOk:
					sql = 'DELETE FROM `wf_alerts` WHERE `id` = %s'
					cursor.execute(sql, (alertID))
					connection.commit()
					self.loadAlerts()
					return True
		finally:
			connection.close()

	@commands.command()
	@commands.is_owner()
	@doThumbs()
	async def purgeOutstanding(self, ctx):
		await self.purgeOutdatedAlerts(True)

def setup(bot):
	bot.add_cog(Warframe(bot))