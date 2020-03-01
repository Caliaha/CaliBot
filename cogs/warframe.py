import datetime
import discord
from discord.ext import tasks, commands
import json
import pymysql.cursors
import re
from stuff import BoxIt, doThumbs, fetchWebpage, sendBigMessage


class Warframe(commands.Cog):
	"""TBD"""
	def __init__(self, bot):
		self.bot = bot
		# MAYBE DO SOMETHING ABOUT THIS
		self.relics = { 'lith': 'VoidT1', 'meso': 'VoidT2', 'neo': 'VoidT3', 'axi': 'VoidT4', 'reqium': 'VoidT5' }
		self.missionTypes = { 'capture': 'MT_CAPTURE', 'defense': 'MT_DEFENSE', 'excavate': 'MT_EXCAVATE', 'interception': 'MT_TERRITORY', 'mobiledefense': 'MT_MOBILE_DEFENSE', 'rescue': 'MT_RESCUE', 'sabotage': 'MT_SABOTAGE', 'survival': 'MT_SURVIVAL' }
		activeAlerts = { }
		activeAlerts['void'] =  { 'VoidT1': [ ], 'VoidT2': [ ], 'VoidT3': [ ], 'VoidT4': [ ], 'VoidT5': [ ] }
		self.activeAlerts = activeAlerts
		self.alreadyAlerted = { }
		self.activeVoidFissures = [ ]
		self.updateLoop.start()
		
		with open('data/solNodes.json', 'r') as file:
			self.solNodes = json.load(file)

	def cog_unload(self):
		self.updateLoop.cancel()

	def loadAlerts(self):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = 'SELECT * FROM `wf_voidRelics`'
				cursor.execute(sql)
				results = cursor.fetchall()
				for result in results:
					self.activeAlerts['void'][result['Era']].append({
						'alertID': result['id'],
						'ownerID': result['ownerID'],
						'guildID': result['guildID'],
						'channelID': result['channelID'],
						'missionType': result['MissionType'],
						'alertType': ('CHANNEL', 'PERSONAL')[result['type']],
						'runOnce': result['runOnce'],
					})
					if result['id'] not in self.alreadyAlerted:
						self.alreadyAlerted[result['id']] = [ ]
		finally:
			connection.close()
		#alert = { 'missionType': 'MT_DEFENSE', 'alertType': 'personal', 'owner': 208758694555418624, 'runOnce': True, 'alertedFor': [ ] }
		#self.activeAlerts['void']['VoidT4'].append(alert)

	async def doAlertEmbed(self, void, alert):
		relicsR = { 'VoidT1': 'Lith', 'VoidT2': 'Meso', 'VoidT3': 'Neo', 'VoidT4': 'Axi', 'VoidT5': 'Reqium' }
		missionTypesR = { 'MT_CAPTURE': 'Capture', 'MT_DEFENSE': 'Defense', 'MT_EXCAVATE': 'Excavate', 'MT_MOBILE_DEFENSE': 'Mobile Defense', 'MT_RESCUE': 'Rescue', 'MT_SABOTAGE': 'Sabotage', 'MT_SURVIVAL': 'Survival', 'MT_TERRITORY': 'Interception' }

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
		embed.description = f'{user.mention} A void relic fissure meeting your alert requirements has appeared!\nEra: {relicsR[void["Modifier"]]}\nMission Type: {missionTypesR[void["MissionType"]]}\nNode: {self.solNodes[void["Node"]]["value"]}\nEnemy: {self.solNodes[void["Node"]]["enemy"]}\nStarts At {startDate}\nExpires At {expireDate}'
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
			print('Error adding to wf_outstanding', e)
		finally:
			connection.close()
		

	async def purgeOutdatedAlerts(self):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = 'SELECT * FROM `wf_outstanding` WHERE `expires` < NOW()'
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
			print('Error adding to wf_outstanding', e)
		finally:
			connection.close()
		pass

	@tasks.loop(minutes=5.0)
	async def updateLoop(self):
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
					if missionID not in self.activeVoidFissures:
						print('Deleting from self.activeVoidFissures', alertID, missionID)
						self.alreadyAlerted[alertID].remove(missionID)
		except Exception as e:
			print(e)
		await self.purgeOutdatedAlerts()

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
						print('beep')
						print('Deleting from self.activeVoidFissures', alertID, missionID)
						self.alreadyAlerted[alertID].remove(missionID)
		except Exception as e:
			print(e)
		await self.purgeOutdatedAlerts()

	@updateLoop.before_loop
	async def before_updateLoop(self):
		self.loadAlerts()
		await self.bot.wait_until_ready()

	@commands.group(invoke_without_command=True)
	@doThumbs()
	async def wfAlert(self, ctx):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = sql = 'SELECT * FROM `wf_voidRelics` WHERE `guildID` = %s or `ownerID` = %s'
				cursor.execute(sql, (ctx.guild.id, ctx.author.id))
				
				box = BoxIt()
				results = cursor.fetchall()
				for result in results:
					box.addRow([ result['id'], ctx.guild.get_member(int(result['ownerID'])), "PERSONAL" if result['type'] else "CHANNEL", result['MissionType'], result['Era'] ])
				box.sort(2, True)
				box.setHeader([ 'ID', 'User', 'Type', 'Era', 'Mission' ])
				box.setTitle('Void Relic Alerts')

				await sendBigMessage(self, ctx, f'You can only delete CHANNEL alerts if you are an officer\n{box.box()}', '```', '```',)
				return True
		finally:
			connection.close()

	@wfAlert.command()
	@doThumbs()
	async def add(self, ctx, *, args):
		validArguments = { '-p': 'personal', '-v': 'voidRelic', '-t': 'missionType', '-c': 'channel' }
		arguments = { }
		
		relics = { 'lith': 'VoidT1', 'meso': 'VoidT2', 'neo': 'VoidT3', 'axi': 'VoidT4', 'reqium': 'VoidT5' }
		missionTypes = { 'capture': 'MT_CAPTURE', 'defense': 'MT_DEFENSE', 'excavate': 'MT_EXCAVATE', 'interception': 'MT_TERRITORY', 'mobiledefense': 'MT_MOBILE_DEFENSE', 'rescue': 'MT_RESCUE', 'sabotage': 'MT_SABOTAGE', 'survival': 'MT_SURVIVAL'  } # Missing artifact and intel and maybe others
		
		if len(args) >= 1 and (args[0] == 'help' or args[0] == '-h'):
			await ctx.send('Usage: !wfAlert -c -v meso -t defense')
			return True
		
		for i in range(len(args)):
			if args[i] in validArguments:
				if i+1 < len(args):
					arguments[validArguments[args[i]]] = args[i+1]
				else:
					arguments[validArguments[args[i]]] = True
		try:
			era = relics[arguments['voidRelic']]
		except:
			era = False
		try:
			missionType = missionTypes[arguments['missionType']]
		except:
			missionType = False
		try:
			personal = arguments['personal']
		except:
			personal = False
		
		try:
			guildID = ctx.guild.id
		except:
			guildID = ''
		try:
			channelID = ctx.channel.id
		except:
			channelID = ''
		
		try:
			runOnce = arguments['runOnce']
		except:
			runOnce = False

		if not era and not missionType:
			return False
		print(ctx.author.id, guildID, channelID, personal, runOnce, missionType, era)
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = 'INSERT INTO `wf_voidRelics` (`ownerID`, `guildID`, `channelID`, `type`, `runOnce`, `MissionType`, `Era`) VALUES(%s, %s, %s, %s, %s, %s, %s)'
				cursor.execute(sql, (ctx.author.id, guildID, channelID, personal, runOnce, missionType, era))
				connection.commit()
				await ctx.send(f'I have created a {"PERSONAL" if personal else "CHANNEL"} alert for {era} {missionType} relic.') 
		finally:
			connection.close()
		
		self.loadAlerts()

	@wfAlert.command()
	@doThumbs()
	async def delete(self, ctx, alertID: int):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `ownerID`, `guildID`, `channelID`, `type` FROM `wf_voidRelics` WHERE `id` = %s"
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
					sql = 'DELETE FROM `wf_voidRelics` WHERE `id` = %s'
					cursor.execute(sql, (alertID))
					connection.commit()
					return True
		finally:
			connection.close()

def setup(bot):
	bot.add_cog(Warframe(bot))