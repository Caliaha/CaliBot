import asyncio
from discord.ext import commands
import pymysql.cursors
from stuff import no_pm, superuser
from subprocess import Popen, PIPE
		
class Announce():
	def __init__(self, bot):
		self.bot = bot
		self.VOICE_CHANNELS = {}
		self.DO_ANNOUNCEMENTS = []
		self.queue = asyncio.Queue()
		self.control = asyncio.Event()
		self.audio_player = self.bot.loop.create_task(self.playTTS())
		self.file = '-w=' + self.bot.TTS_FILE

	async def playTTS(self):
		while True:
			self.control.clear()
			ttsThing = await self.queue.get()
			print(ttsThing["server"])
			if ttsThing["server"] in self.VOICE_CHANNELS:
				server = ttsThing["server"]
				process = Popen([self.bot.TTS_PROGRAM, '-l=en-US', self.file, ttsThing["message"]])
				(output, err) = process.communicate()
				exit_code = process.wait()
 
				player = self.VOICE_CHANNELS[server].create_ffmpeg_player("./calibot.wav", after=self.control.set)
				player.start()
				self.VOICE_CHANNELS[server].player = player
				await self.control.wait()

	async def fetchPhoneticName(self, member):
		try:
			connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `phonetic` FROM `usersettings` WHERE `discordID`=%s"
				cursor.execute(sql, member.id)
				result = cursor.fetchone()
				if result is not None and result['phonetic'] is not None:
					return result['phonetic']
				else:
					return member.name
		except:
			return member.name
		finally:
			connection.close()

	async def on_voice_state_update(self, before, after):
		try:
			if after.name == self.bot.NAME and after.voice.voice_channel is not None: # Bot has moved, update DB for reconnection purposes and return so we don't announce ourselves
				await self.updateDB(after.server, after.voice.voice_channel)
				return
		except:
			print('Error adding ourselves to db or something weird')
		server = before.server
		voiceBefore = before.voice.voice_channel
		voiceAfter = after.voice.voice_channel
		if (server not in self.DO_ANNOUNCEMENTS or server not in self.VOICE_CHANNELS):
			return
		if voiceBefore is not self.VOICE_CHANNELS[server].channel and voiceAfter is self.VOICE_CHANNELS[server].channel:
			print(before.name,'has joined the channel')
			tts = { }
			tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(before) + " has joined."
			tts["server"] = server
			await self.queue.put(tts)
			return
		if voiceBefore is self.VOICE_CHANNELS[server].channel and voiceAfter is not self.VOICE_CHANNELS[server].channel:
			tts = { }
			tts["message"] = "<volume level='50'>" + await self.fetchPhoneticName(after) + ' has left.'
			tts["server"] = server
			print(after.name,'has left the channel')
			await self.queue.put(tts)
			return
		return

	async def removeFromDB(self, server, channel):
		try:
			connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "DELETE FROM `voice_status` WHERE `server`=%s"
				cursor.execute(sql, (server.id))
				connection.commit()
		except:
			print('Error removing from db or something')
		finally:
			connection.close()

	async def updateDB(self, server, channel):
		await self.removeFromDB(server, channel)
		try:
			connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "INSERT INTO `voice_status` (`server`, `channel`) VALUES(%s, %s)"
				cursor.execute(sql, (server.id, channel.id))
				connection.commit()
		except:
			print('Error adding to db or something')
		finally:
			connection.close()

	async def joinVoiceChannel(self, server, channel):
		print(server, channel)
		self.DO_ANNOUNCEMENTS.append(server)
		voice = await self.bot.join_voice_channel(channel)
		self.VOICE_CHANNELS[server] = voice
		await self.updateDB(server, channel)

	async def leaveVoiceChannel(self, server, channel):
		await self.VOICE_CHANNELS[server].disconnect()
		self.DO_ANNOUNCEMENTS.remove(server)
		del self.VOICE_CHANNELS[server]
		await self.removeFromDB(server, channel)

	async def joinOrMove(self, ctx):
		channel = ctx.message.author.voice.voice_channel
		server = ctx.message.author.server
 
		if server in self.VOICE_CHANNELS:
			if self.VOICE_CHANNELS[server].channel is channel or channel is None:
				await self.leaveVoiceChannel(server, channel)
			else:
				await self.VOICE_CHANNELS[server].move_to(channel)
				await self.updateDB(server, channel)
		elif channel:
			await self.joinVoiceChannel(server, channel)
		else:
			await self.bot.send_message(ctx.message.channel, "I couldn't figure out what voice channel you were in.")

	async def on_ready(self):
		print("Attempting to reconnect to all voice channels")
		connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		with connection.cursor() as cursor:
			sql = "SELECT `server`, `channel` FROM `voice_status`"
			cursor.execute(sql)
			results = cursor.fetchall()
			for result in results:
				print(result['server'], result['channel'])
				server = self.bot.get_server(result['server'])
				channel = self.bot.get_channel(result['channel'])
				if server and channel:
					await self.joinVoiceChannel(server, channel)
#		except:
#			print('Error reconnecting to voice things with db')
#		finally:
#			connection.close()

	@commands.command(pass_context=True, description="Bot will join your voice channel and announces who joins or leaves the voice channel you are in, limit one per guild")
	@no_pm()
	async def announce(self, ctx):
		"""Bot announces who joins or leaves your voice channel"""
		await self.joinOrMove(ctx)
	
	@commands.command(pass_context=True, hidden=True)
	@superuser()
	@no_pm()
	async def say(self, ctx, message):
		tts = { }
		tts["message"] = "<volume level='50'>" + message
		tts["server"] = ctx.message.author.server
		await self.queue.put(tts)

def setup(bot):
	bot.add_cog(Announce(bot))