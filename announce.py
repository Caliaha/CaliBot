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
		server = before.server
		voiceBefore = before.voice.voice_channel
		voiceAfter = after.voice.voice_channel
		if (server not in self.DO_ANNOUNCEMENTS or server not in self.VOICE_CHANNELS):
			return
		if after.name == self.bot.NAME:
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

	async def joinOrMove(self, ctx):
		channel = ctx.message.author.voice.voice_channel
		server = ctx.message.author.server
 
		if channel is None:
			await self.bot.send_message(ctx.message.channel, "I couldn't figure out what voice channel you were in.")
			return False
 
		if server in self.VOICE_CHANNELS:
			if self.VOICE_CHANNELS[server].channel is channel:
				await self.VOICE_CHANNELS[server].disconnect()
				self.DO_ANNOUNCEMENTS.remove(ctx.message.server)
				del self.VOICE_CHANNELS[server]
			else:
				print('I have moved to another channel on the same guild')
				await self.VOICE_CHANNELS[server].move_to(channel)
		else:
			self.DO_ANNOUNCEMENTS.append(ctx.message.server)
			voice = await self.bot.join_voice_channel(channel)
			self.VOICE_CHANNELS[server] = voice

	@commands.command(pass_context=True, description="Bot will join your voice channel and announces who joins or leaves the voice channel you are in, limit one per guild")
	@no_pm()
	async def announce(self, ctx):
		"""Bot announces who joins or leaves your voice channel"""
		await self.joinOrMove(ctx)
	
	@commands.command(pass_context=True, description="Force bot to leave voice channel on guild")
	@no_pm()
	async def leave(self, ctx):
		"""Makes bot leave voice channel"""
		server = ctx.message.author.server
		if server in self.VOICE_CHANNELS:
			await self.VOICE_CHANNELS[server].disconnect()
			self.DO_ANNOUNCEMENTS.remove(ctx.message.server)
			del self.VOICE_CHANNELS[server]

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