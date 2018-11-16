import asyncio
import discord
from discord.ext import commands
import pymysql.cursors
from stuff import BoxIt, checkPermissions, cleanUserInput, doThumbs, isBotOwner, superuser
from subprocess import Popen, PIPE
import time

class Announce():
	def __init__(self, bot):
		self.bot = bot
		self.file = '-w=' + self.bot.TTS_FILE
		self.paused = False
		self.ignored_channels = {}
		self.allowedGuilds = [ 332340487451312141, 254746234466729987 ]
		self.bot.loop.create_task(self.inactivityCheck())
		self.guildQueue = {}
		self.queue = {}
		
		for guild in bot.guilds:
			self.queue[guild.id] = None

	async def updateNickname(self, guild, name, action='Error'):
		if name is None:
			newName = None
		else:
			newName = f'{name} - {action}'

		try:
			await guild.me.edit(nick=newName)
		except:
			pass

	async def processQueue(self, guild):
		while True:
			print('ProcessQueueLoopStart', guild.name)
			tts = await self.queue[guild.id].get()

			#guild = tts["guild"]
			print(tts["guild"])
			print(guild.id, guild.name)
			if guild.voice_client is not None:
				if tts["action"]:
					await self.updateNickname(tts["guild"], tts["name"], tts["action"])
				process = Popen([self.bot.TTS_PROGRAM, '-l=en-US', f'-w={self.bot.TTS_FILE}-{guild.id}.wav', tts["message"]])
				(output, err) = process.communicate()
				exit_code = process.wait()

				if (not guild.voice_client.is_connected()):
					print("playTTS() not connected", 'Skipping:', tts["guild"], tts["name"])
					self.leaveVoiceChannel(guild, guild.voice_client.channel)
				else:
					try:
						guild.voice_client.play(discord.FFmpegPCMAudio(f'{self.bot.TTS_FILE}-{guild.id}.wav'))
					except Exception as e:
						print(e, 'Error in voice.play')

					print('Sleeping while playing')
					try:
						timer = time.time()
						while(guild.voice_client.is_playing() and time.time() < timer + 10): #FIX ME
							asyncio.sleep(0.1)
					except:
						pass
					print('Done sleeping')
			else:
				print("I was asked to announce for something that I do not have a voice_client for")
			await self.updateNickname(tts["guild"], None)

	async def fetchPhoneticName(self, member):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `phonetic` FROM `usersettings` WHERE `discordID`=%s"
				cursor.execute(sql, member.id)
				result = cursor.fetchone()
				if result is not None and result['phonetic'] is not None:
					return result['phonetic']

		except:
			print("Error with fetching phonetic")
		finally:
			connection.close()
		
		return cleanUserInput(member.nick or member.name)

	async def inactivityCheck(self):
		await self.bot.wait_until_ready()
		while True:
			for voiceClient in self.bot.voice_clients:
				if self.countNonBotMembers(voiceClient.channel.members) == 0:
					print('Leaving channel {} on guild {} because of inactivity'.format(voiceClient.channel, voiceClient.guild))
					await self.leaveVoiceChannel(voiceClient.guild, voiceClient.channel)
			await asyncio.sleep(60)

	def countNonBotMembers(self, members):
		count = 0
		for member in members:
			if not member.bot and member.name is not self.bot.NAME:
				count = count + 1
		return count

	async def on_voice_state_update(self, member, before, after):
		if member.bot:
			try:
				if member.name == self.bot.NAME:
					if after.channel is not None: # Bot has moved, update DB for reconnection purposes and return so we don't announce ourselves
						await self.updateDB(member.guild.id, after.channel.id)
						return
			except:
				print('Error adding ourselves to db or something weird')

			print('on_voice_state_update: {} is a bot.'.format(member.name))
			return False

		print("VOICE_STATE_UPDATE", member.name, member.guild.name, before.channel, after.channel)
		guild = member.guild
		if guild.id not in self.allowedGuilds:
		 print("Guild {} not in list of allowed guilds".format(guild.name))
		 return

		if guild.id not in self.ignored_channels:
			self.ignored_channels[guild.id] = []
			print('Adding {} to self.ignored_channels'.format(guild.name))

			try:
				connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
				with connection.cursor() as cursor:
					sql = "SELECT `mdg_ignore` FROM `guild_defaults` WHERE `guildID`=%s"
					cursor.execute(sql, (guild.id))
					result = cursor.fetchone()
					if result is not None:
						if result['mdg_ignore'] is not None:
							self.ignored_channels[guild.id] = result['mdg_ignore'].split()
			finally:
				connection.close()

		if member.guild.voice_client and guild.id in self.guildQueue:		#guild.id in self.guildQueue
			if self.countNonBotMembers(member.guild.voice_client.channel.members) == 0:

				if after.channel and str(after.channel.id) not in self.ignored_channels[guild.id]:
					print('Moving to {} because our channel is empty'.format(after.channel))
					await self.joinOrMove(guild, after.channel)
					return
				else:
					print('No members left in channel, finding another one')
					for voiceChannel in guild.voice_channels:
						if str(voiceChannel.id) not in self.ignored_channels[guild.id] and self.countNonBotMembers(voiceChannel.members) > 0:
							if await self.joinOrMove(guild, voiceChannel):
								return
					print('Left voice channel on {} because no one left in valid channels'.format(guild.name))
					await self.leaveVoiceChannel(guild, member.guild.voice_client.channel)
					await self.updateNickname(guild, None)
					return
		else:
			if after.channel and str(after.channel.id) not in self.ignored_channels[guild.id]:
				print('Joining {} because someone has entered a valid voice channel'.format(after.channel))
				await self.joinOrMove(guild, after.channel)
				return

		guild = member.guild
		voiceBefore = before.channel
		voiceAfter = after.channel
		if (before.channel == after.channel):
			print("The before and after channels were the same, weird")

		tts = { }
		tts["guild"] = guild
		tts["name"] = member.nick or member.name
		if voiceBefore is not guild.voice_client.channel and voiceAfter is guild.voice_client.channel:
			print(member.name, 'has joined the channel')
			tts["action"] = 'Join'
			tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(member) + " has joined."
			await self.queue[member.guild.id].put(tts)
			return
		if voiceBefore is guild.voice_client.channel and voiceAfter is not guild.voice_client.channel:
			if voiceAfter is not None and voiceAfter.name == "afk":
				tts["action"] = 'AFK'
				tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(member) + " has gone a f k."
			else:
				tts["action"] = 'Leave'
				tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(member) + " has left."
			print(member.name, 'has left the channel')
			await self.queue[member.guild.id].put(tts)
			return
		return

	async def removeFromDB(self, guildID, channelID):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "DELETE FROM `voice_status` WHERE `guildID`=%s"
				cursor.execute(sql, (str(guildID)))
				connection.commit()
		except:
			print('Error removing from db or something')
		finally:
			connection.close()

	async def updateDB(self, guildID, channelID):
		await self.removeFromDB(guildID, channelID)
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "INSERT INTO `voice_status` (`guildID`, `channel`) VALUES(%s, %s)"
				cursor.execute(sql, (str(guildID), str(channelID))) # FIX THIS str
				connection.commit()
		except Exception as e:
			print('Error adding to db or something', e)
		finally:
			connection.close()

	async def leaveVoiceChannel(self, guild, channel): # Fix this
		try:
			self.guildQueue[guild.id].cancel()
			self.queue[guild.id] = None
		except Exception as e:
			print(e)

		try:
			await guild.voice_client.disconnect(force=True)
		except:
			print("ERROR: Failed to disconnect from voice in leaveVoiceChannel()")
		await self.removeFromDB(guild.id, channel.id)

	async def joinOrMove(self, guild, channel): #FIX ME
		if guild.voice_client is not None:
			if guild.voice_client.channel is channel:
				print('Leaving voice channel {}'.format(channel.name))
				await self.leaveVoiceChannel(guild, channel)
				return True
			print("Attempting to change voice channels")
			if await guild.voice_client.move_to(channel):
				await self.updateDB(guild.id, channel.id)
				return True
			return False
 
		if channel is not None:
			self.guildQueue[guild.id] = self.bot.loop.create_task(self.processQueue(guild))
			self.queue[guild.id] = asyncio.Queue()
			if await channel.connect():
				print('Connectiong to voice channel {} on guild {}'.format(channel, guild))
				await self.updateDB(guild.id, channel.id)

				tts = { }
				tts["guild"] = guild
				tts["action"] = None
				tts["name"] = "CaliBot"
				tts["message"] = "<volume level='50'>Beep"
				await self.queue[guild.id].put(tts)
				return True
			return False

	async def on_ready(self):
		print("Attempting to reconnect to all voice channels")
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `guildID`, `channel` FROM `voice_status`"
				cursor.execute(sql)
				results = cursor.fetchall()
				for result in results:
					print(result['guildID'], result['channel'])
					guild = self.bot.get_guild(int(result['guildID'])) # Fix me, change these to ints in the database later
					channel = self.bot.get_channel(int(result['channel']))
					print(guild, channel)
					if guild and channel:
						print(guild.id, channel)
						await self.joinOrMove(guild, channel)
		except Exception as e:
			print("on_ready() unable to connect to db or something", e)
		finally:
			connection.close()
			
		for guild in self.bot.guilds:
			print("Resetting nickname for", guild.name)
			await self.updateNickname(guild, None)

	@commands.command()
	@commands.guild_only()
	async def announce(self, ctx):
		"""Bot announces who joins or leaves your voice channel"""
		await self.joinOrMove(ctx.guild, ctx.author.voice.channel)
	
	@commands.command(hidden=True)
	@commands.guild_only()
	@checkPermissions('voice')
	async def say(self, ctx, message):
		tts = { }
		tts["guild"] = ctx.guild
		tts["action"] = None
		tts["name"] = ctx.author.nick or ctx.author.name
		tts["message"] = message
		await self.queue[ctx.guild.id].put(tts)

	@commands.command(hidden=True)
	@isBotOwner()
	async def debugannounce(self, ctx):
		message = BoxIt()
		message.setTitle('Active Voice Clients')
		for key in self.bot.voice_clients:
			message.addRow( [ key.guild, key.guild.id, key.channel, key.channel.id, key.is_connected() ] )
			#print(key, key.server, key.server.id, key.channel, key.channel.id, key.is_connected())

		message.setHeader( [ 'Guild', 'Guild ID', 'Channel', 'Channel ID', 'Conn' ] )
		
		await ctx.send('```' + message.box() + '```')
		await ctx.send('self.paused is set to: ' + str(self.paused))

	@commands.command()
	@commands.guild_only()
	@checkPermissions('voice')
	@doThumbs()
	async def mdg(self, ctx):
		"""Moves everyone to your voice channel"""
		destinationChannel = ctx.message.author.voice.channel
		if destinationChannel is None:
			await ctx.send("You are not in a voice channel")
			return False

		ignored_channels = []
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `mdg_ignore` FROM `guild_defaults` WHERE `guildID`=%s"
				cursor.execute(sql, (ctx.message.guild.id))
				result = cursor.fetchone()
				if result is not None:
					if result['mdg_ignore'] is not None:
						ignored_channels = result['mdg_ignore'].split()
		finally:
			connection.close()

		for channel in ctx.message.guild.voice_channels:
			if (channel != destinationChannel and str(channel.id) not in ignored_channels):
				print(channel)
				listToMove = []
				count = 0
				for member in channel.members:
					print(member.name + " Added to listToMove")
					count = count + 1
					listToMove.append(member)
				print(count)
				count2 = 0
				print(len(listToMove))
				for member in listToMove: # I do this because moving during channel.voice_members iteration caused it to stop short
					count2 = count2 + 1
					try:
						await member.move_to(destinationChannel, reason='Deathgripped')
						print("Moving {} to {}".format(member.name, destinationChannel.name))
					except discord.Forbidden as e:
						print("Missing permissions to move {} to {}".format(member.name, destinationChannel.name), e)
					except discord.HTTPException as e:
						print("HTTPEXception Moving {} to {}".format(member.name, destinationChannel.name, e))
					except Exception as e:
						print("Failed moving {} to {}".format(member.name, destinationChannel.name), e)
					else:
						print("No error")
				print(count, count2)
		return True

	@commands.command()
	@commands.guild_only()
	@checkPermissions('voice')
	@doThumbs()
	async def mdgignore(self, ctx, channel : discord.VoiceChannel = None):
		"""Adds channel to ignore list, bot will not pull members from this channel"""

		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `mdg_ignore` FROM `guild_defaults` WHERE `guildID`=%s"
				cursor.execute(sql, (ctx.guild.id))
				result = cursor.fetchone()
				if result is not None:
					if result['mdg_ignore'] is not None:
						mdg_ignore = result['mdg_ignore'].split()
						if (channel is None):
							await ctx.send('I am ignoring the following channels: ' + ', '.join(self.bot.get_channel(int(c)).name for c in mdg_ignore)) #self.bot.get_channel(int(result['channel']))
							return True
					else:
						mdg_ignore = []

					if channel and str(channel.id) not in mdg_ignore:
						mdg_ignore.append(str(channel.id))
					else:
						await ctx.send(channel.name + ' has already been added to the !mdg ignore list.')
						return False
					self.ignored_channels[ctx.guild.id] = mdg_ignore
					mdg_ignore = ' '.join(mdg_ignore)
					sql = "UPDATE `guild_defaults` SET `mdg_ignore` = %s WHERE `guildID` = %s LIMIT 1"
					cursor.execute(sql, (mdg_ignore, ctx.message.guild.id))
					connection.commit()
				elif channel is not None:
					sql = "INSERT INTO `guild_defaults` (`guildID`, `mdg_ignore`) VALUES(%s, %s)"
					cursor.execute(sql, (ctx.message.guild.id, channel.id))
					connection.commit()
				else:
					ctx.send('I am not currently ignoring any channels')
				await ctx.send(channel.name + ' has been added to the !mdg ignore list.')
		except Exception as e:
			print(e)
		finally:
			connection.close()
		return True

	@commands.command()
	@commands.guild_only()
	@checkPermissions('voice')
	@doThumbs()
	async def mdgunignore(self, ctx, channel : discord.VoiceChannel):
		"""Adds channel to ignore list, bot will not pull members from this channel"""
		try:
			id = str(channel.id)
		except:
			await self.bot.say('I was unable to get the id for that channel, please double check that you spelled it correctly.')
			return False

		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `mdg_ignore` FROM `guild_defaults` WHERE `guildID`=%s"
				cursor.execute(sql, (ctx.guild.id))
				result = cursor.fetchone()
				if result is not None:
					print('Beep')
					if result['mdg_ignore'] is not None:
						mdg_ignore = result['mdg_ignore'].split()
					else:
						mdg_ignore = []
					if id in mdg_ignore:
						mdg_ignore.remove(id)
					else:
						#pass
						await ctx.send(channel.name + ' was not in the !mdg ignore list.')
						return False
					mdg_ignore = ' '.join(mdg_ignore)
					sql = "UPDATE `guild_defaults` SET `mdg_ignore` = %s WHERE `guildID` = %s LIMIT 1"
					cursor.execute(sql, (mdg_ignore, ctx.guild.id))
					connection.commit()
				await ctx.send(channel.name + ' has been removed to the !mdg ignore list.')
		finally:
			connection.close()
		return True

def setup(bot):
	bot.add_cog(Announce(bot))
