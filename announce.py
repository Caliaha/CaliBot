import asyncio
import discord
from discord.ext import commands
import pymysql.cursors
from stuff import BoxIt, checkPermissions, cleanUserInput, doThumbs, isBotOwner, superuser
from subprocess import Popen, PIPE

class Announce():
	def __init__(self, bot):
		self.bot = bot
		self.VOICE_CHANNELS = {}
		self.queue = asyncio.Queue()
		self.control = asyncio.Event()
		self.audio_player = self.bot.loop.create_task(self.playTTS())
		self.file = '-w=' + self.bot.TTS_FILE
		self.paused = False

	async def checkIfConnected(self): # Redo this or something; this only checks actual voice; not if we believe we are in a voice channel but aren't
		for voice in self.bot.voice_clients:
			if voice.guild.id not in self.VOICE_CHANNELS:
				self.VOICE_CHANNELS[voice.guild.id] = voice
				print('We appear to be in a voice channel that was not in VOICE_CHANNELS, Fixed maybe')

	async def updateNickname(self, guild, name, action='Error'):
		print(guild.me, name, self.bot.NAME)
		if name is None:
			newName = None
		else:
			newName = name + ' - ' + action

		try:
			await guild.me.edit(nick=newName)
			#await self.bot.change_nickname(guild.me, newName)
		except:
			print("Unable to change nickname")

	async def playTTS(self):
		while not self.bot.is_closed():
			#self.control.clear()
			tts = await self.queue.get()
			print(tts["guild"])
			if tts["guild"].id in self.VOICE_CHANNELS:
				guild = tts["guild"]
				if tts["action"]:
					await self.updateNickname(tts["guild"], tts["name"], tts["action"])
				process = Popen([self.bot.TTS_PROGRAM, '-l=en-US', self.file, tts["message"]])
				(output, err) = process.communicate()
				exit_code = process.wait()
 
				voice = self.VOICE_CHANNELS[guild.id]
				
				if (not voice.is_connected()):
					print("playTTS() not connected", 'Skipping:', tts["guild"], tts["name"])
					# Add reconnect logic here
					if guild.id in self.VOICE_CHANNELS:
						await self.joinVoiceChannel(guild.id, self.VOICE_CHANNELS[guild.id].channel)
					else:
						print("Bot is disconnected from voice and is unable to reconnect, removing from self.VOICE_CHANNELS")
						print(guild.name, guild.id)
						self.VOICE_CHANNELS.remove(guild.id)
				else:
					try:
						voice.play(discord.FFmpegPCMAudio("./calibot.wav"))
					except Exception as e:
						print(e, 'Error in voice.play')
					#player = self.VOICE_CHANNELS[guild.id].FFmpegPCMAudio("./calibot.wav", after=self.control.set)
					#player.start()
					#self.VOICE_CHANNELS[guild.id].player = player
					#await self.control.wait()
					print('Sleeping while playing')
					while(voice.is_playing()): #FIX ME
						#print('sleeping')
						asyncio.sleep(0.1)
					print('Done sleeping')
					await self.updateNickname(tts["guild"], None)
			else:
				print("I was asked to announce for something that is not or no longer in self.VOICE_CHANNELS")

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
		
		if member.nick is not None:
			return cleanUserInput(member.nick)
		else:
			return cleanUserInput(member.name)

	async def on_voice_state_update(self, member, before, after):
		print("VOICE_STATE_UPDATE", member.name, member.guild.name, before.channel, after.channel)
		try:
			if member.name == self.bot.NAME:
				if after.channel is not None: # Bot has moved, update DB for reconnection purposes and return so we don't announce ourselves
					await self.updateDB(member.guild.id, after.channel.id)
				return
		except:
			print('Error adding ourselves to db or something weird')
		if self.paused:
			return
		guild = member.guild
		voiceBefore = before.channel
		voiceAfter = after.channel
		if (before.channel == after.channel):
			print("The before and after channels were the same, weird")
		#await self.checkIfConnected()
		if (guild.id not in self.VOICE_CHANNELS):
			return
		if voiceBefore is not self.VOICE_CHANNELS[guild.id].channel and voiceAfter is self.VOICE_CHANNELS[guild.id].channel:
			print(member.name, 'has joined the channel')
			tts = { }
			tts["name"] = member.nick or member.name
			tts["action"] = 'Join'
			tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(member) + " has joined."
			tts["guild"] = guild
			await self.queue.put(tts)
			return
		if voiceBefore is self.VOICE_CHANNELS[guild.id].channel and voiceAfter is not self.VOICE_CHANNELS[guild.id].channel:
			tts = { }
			tts["name"] = member.nick or member.name
			tts["guild"] = guild
			if voiceAfter is not None and voiceAfter.name == "afk":
				tts["action"] = 'AFK'
				tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(member) + " has gone a f k."
			else:
				tts["action"] = 'Leave'
				tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(member) + " has left."
			print(member.name, 'has left the channel')
			await self.queue.put(tts)
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

	async def joinVoiceChannel(self, guildID, channel):
		print("joinVoiceChannel", guildID, channel)
		#print(channel.permissions_for(self.bot))
		try:
			voice = await channel.connect()
			self.VOICE_CHANNELS[guildID] = voice
			await self.updateDB(guildID, channel.id)
		except Exception as e:
			print("Failed to joinVoiceChannel", e)
		
		return voice or None

	async def leaveVoiceChannel(self, guildID, channel):
		try:
			await self.VOICE_CHANNELS[guildID].disconnect()
		except:
			print("ERROR: Failed to disconnect from voice in leaveVoiceChannel()")
		try:
			del self.VOICE_CHANNELS[guildID]
		except:
			print("ERROR: Failed to remove guild from VOICE_CHANNELS in leaveVoiceChannel()")

		await self.removeFromDB(guildID, channel)

	async def joinOrMove(self, ctx):
		channel = ctx.message.author.voice.channel
		guildID = ctx.guild.id
 
		if guildID in self.VOICE_CHANNELS:
			if self.VOICE_CHANNELS[guildID].channel is channel or channel is None:
				await self.leaveVoiceChannel(guildID, channel)
			else:
				await self.VOICE_CHANNELS[guildID].move_to(channel)
				await self.updateDB(guildID, channel.id)
		elif channel:
			await self.joinVoiceChannel(guildID, channel)
		else:
			await ctx.send("I couldn't figure out which voice channel you were in.")

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
						await self.joinVoiceChannel(guild.id, channel)
		except:
			print("on_ready() unable to connect to db or something")
		finally:
			connection.close()
			
		for guild in self.bot.guilds:
			print("Resetting nickname for", guild.name)
			await self.updateNickname(guild, None)

	@commands.command(pass_context=True, description="Bot will join your voice channel and announces who joins or leaves the voice channel you are in, limit one per guild")
	@commands.guild_only()
	async def announce(self, ctx):
		"""Bot announces who joins or leaves your voice channel"""
		await self.checkIfConnected()
		await self.joinOrMove(ctx)
	
	@commands.command(pass_context=True, hidden=True)
	@commands.guild_only()
	@superuser()
	async def say(self, ctx, message):
		tts = { }
		tts["message"] = "<volume level='50'>" + cleanUserInput(message)
		tts["guild"] = ctx.message.author.guild
		tts["action"] = None
		await self.queue.put(tts)

	@commands.command(pass_context=True)
	@commands.guild_only()
	@checkPermissions('voice')
	async def forcereconnect(self, ctx):
		"""Bot attempts to leave and rejoin channel"""
		await ctx.send('I will attempt to disconnect and rejoin the voice channel, this may not work.')
		await self.checkIfConnected()
		if ctx.guild.id in self.VOICE_CHANNELS:
			guild = self.VOICE_CHANNELS[ctx.guild.id]
			try:
				await self.leaveVoiceChannel(ctx.guild.id, guild.channel) 
			except:
				print("ERROR: Unable to leave voice channel in forcereconnect()")
			try:
				await self.joinVoiceChannel(ctx.guild.id, guild.channel)
			except:
				print("ERROR: Failed to join voice channel in forcereconnect()")

	@commands.command(hidden=True)
	@isBotOwner()
	async def debugannounce(self, ctx):
		message = BoxIt()
		message.setTitle('Voice Channels - Announce')
		for guild, client in self.VOICE_CHANNELS.items():
			message.addRow( [ client.guild, client.guild.id, client.channel, client.channel.id, client.is_connected() ] )
			#print(server, client.server, client.server.id, client.channel, client.channel.id, client.is_connected())
		
		message2 = BoxIt()
		message2.setTitle('Voice Channels - Actual')
		for key in self.bot.voice_clients:
			message2.addRow( [ key.guild, key.guild.id, key.channel, key.channel.id, key.is_connected() ] )
			#print(key, key.server, key.server.id, key.channel, key.channel.id, key.is_connected())

		message.setHeader( [ 'Guild', 'Guild ID', 'Channel', 'Channel ID', 'Conn' ] )
		message2.setHeader( [ 'Guild', 'Guild ID', 'Channel', 'Channel ID', 'Conn' ] )
		
		await ctx.send('```' + message.box() + '```')
		await ctx.send('```' + message2.box() + '```')
		await ctx.send('self.paused is set to: ' + str(self.paused))
		await ctx.send('There should be no discrepancy between the previous two statements')

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

		self.paused = True
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
						#await self.bot.move_member(member, destinationChannel)
						await member.move_to(destinationChannel, reason='Deathgripped')
						print("Moving {} to {}".format(member.name, destinationChannel.name))
					except discord.Forbidden as e:
						print("Missing permissions to move {} to {}".format(member.name, destinationChannel.name), e)
					except discord.HTTPException as e:
						print("HTTPEXception Moving {} to {}".format(member.name, destinationChannel.name, e))
					except Exception as e:
						print("Failed moving {} to {}".format(member.name, destinationChannel.name), e)
					except:
						print("Normal except Failed moving {} to {}".format(member.name, destinationChannel.name))
					else:
						print("No error")
				print(count, count2)
		#try:
			#pass
			#self.control.clear()
			#player = self.VOICE_CHANNELS[ctx.message.guild.id].create_ffmpeg_player("./media/getoverhere.mp3", after=self.control.set)
			#player.start()
			#await self.control.wait()
		#except:
			#print("Could not play get over here sound")
		self.paused = False
		return True

	@commands.command()
	@commands.guild_only()
	@checkPermissions('voice')
	@doThumbs()
	async def mdgignore(self, ctx, channel : discord.VoiceChannel = None):
		"""Adds channel to ignore list, bot will not pull members from this channel"""
		print(channel)
#		try:
#			id = channel.id
#		except:
#			await self.bot.say('I was unable to get the id for that channel, please double check that you spelled it correctly.')
#			return False

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
					#print(len(allowed_roles), allowed_roles)
					if channel and str(channel.id) not in mdg_ignore:
						mdg_ignore.append(str(channel.id))
					else:
						await ctx.send(channel.name + ' has already been added to the !mdg ignore list.')
						return False
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
