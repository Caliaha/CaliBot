import datetime
import discord
from discord.ext import tasks, commands
import re
from stuff import BoxIt, deleteMessage, doThumbs, superuser, fetchWebpage, postWebdata, sendBigMessage

class MHW(commands.Cog):
	"""Posts latest Monster Hunter World Events"""
	def __init__(self, bot):
		self.bot = bot
		self.MHW_EVENTS_URL = 'http://game.capcom.com/world/steam/us/schedule.html?utc=-4'
		self.guilds = { } #activeEvents, existingPosts: List of events currently on website as available, currently existing posts
		self.updateLoop.start()

	def cog_unload(self):
		self.updateLoop.cancel()

	@commands.command(hidden=True)
	async def mhwtest(self, ctx):
		try:
			await sendBigMessage(self, ctx, f'{", ".join(self.guilds[ctx.guild]["activeEvents"])}\n{", ".join(self.guilds[ctx.guild]["existingPosts"])}')
		except Exception as e:
			print('mhwtest', e)

	async def purgeOldEvents(self):
		"""Should remove any previously posted event that is no longer active"""
		for guild in self.guilds:
			for channel in guild.text_channels:
				if channel.name == 'mhw-events':
					async for message in channel.history():
						if message.author != guild.me:
							continue
						for embed in message.embeds:
							if embed.title not in self.guilds[guild]['existingPosts']:
								self.guilds[guild]['existingPosts'].append(embed.title)
							if self.guilds[guild]['activeEvents'] and embed.title not in self.guilds[guild]['activeEvents']:
								try:
									self.guilds[guild]['existingPosts'].remove(embed.title)
									print('Deleting old event', embed.title)
									await message.delete()
								except Exception as e:
									print('purgeOldEvents', e)
			

	def unescape(self, text):
		text = text.replace('&#039;', "'")
		text = text.replace('<br />', '')
		text = text.replace('&amp;', '&') 

		return text

	
	@tasks.loop(minutes=10.0)
	async def updateLoop(self):
		await self.purgeOldEvents()
		for guild in self.guilds: # We delete posts that aren't in here so need to empty it out occasionally
				self.guilds[guild]['activeEvents'].clear()
		try:
			eventsPage = await fetchWebpage(self, self.MHW_EVENTS_URL)
		except:
			print('Unable to fetch mhw events page')
			return
		eventRegex = re.compile('<tr class=".*?">(.*?)</tr>', re.DOTALL)
		titleRegex = re.compile('<div class="title"><span>(.*?)</span>')
		imageRegex = re.compile('<td class="image"> <img src ="(.*?)" />')
		levelRegex = re.compile('<td class="level"><span>(.*?)</span></td>')
		descriptionRegex = re.compile('<p class="txt">(.*?)<span class="addTxt">(.*?)</span></p>')
		locationRegex = re.compile('<li>Locale: <span>(.*?)<span></li>')
		requirementsRegex = re.compile('<li>Requirements: <span> (.*?) </span></li>')
		availabilityRegex = re.compile('<p class="txt"> Available <span>(\d+)/(\d+) (\d+):(\d+)<br>〜<br>(\d+)/(\d+) (\d+):(\d+)</span>')
		availabilityRegex2 = re.compile('<p class="terms"><span>Availability</span> (\d+)-(\d+) (\d+):(\d+) 〜 (\d+)-(\d+) (\d+):(\d+)<br> </p>')



		now = datetime.datetime.now()
		for eventRaw in eventRegex.findall(eventsPage):
			event = ' '.join(eventRaw.split())
			#print(' '.join(event.split()))
			availabilityMatch = availabilityRegex.search(event)
			availabilityMatch2 = availabilityRegex2.search(event)
			if availabilityMatch:
				#print('availabilityMatch')
				availabilityStart = datetime.datetime(2019, int(availabilityMatch[1]), int(availabilityMatch[2]), int(availabilityMatch[3]), int(availabilityMatch[4]))
				availabilityEnd = datetime.datetime(2019, int(availabilityMatch[5]), int(availabilityMatch[6]), int(availabilityMatch[7]), int(availabilityMatch[8]))
				if not (availabilityStart <= now <= availabilityEnd):
					#print(availabilityStart, now, availabilityEnd)
					continue
			elif availabilityMatch2:
				#print('availabilityMatch2')
				availabilityStart = datetime.datetime(2019, int(availabilityMatch2[1]), int(availabilityMatch2[2]), int(availabilityMatch2[3]), int(availabilityMatch2[4]))
				availabilityEnd = datetime.datetime(2019, int(availabilityMatch2[5]), int(availabilityMatch2[6]), int(availabilityMatch2[7]), int(availabilityMatch2[8]))
				if not (availabilityStart <= now <= availabilityEnd):
					#print(availabilityStart, now, availabilityEnd)
					continue
			else:
				#print(event)
				print('Couldn\'t find availability dates, skipping')
				continue

			title = titleRegex.search(event)
			image = imageRegex.search(event)
			level = levelRegex.search(event)
			description = descriptionRegex.search(event)
			location = locationRegex.search(event)
			requirements = requirementsRegex.search(event)
			
			if not title:
				print('mhw, title not found, skipping')
				continue
			
			embed=discord.Embed(
				title = self.unescape(title[1]),
				description = '',
				url = self.MHW_EVENTS_URL,
				color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
			
			if availabilityStart and availabilityEnd:
				embed.set_footer(text=f'Available {availabilityStart} ~ {availabilityEnd}')
			
			if description:
				embed.description = self.unescape(description[1] + (f'\n{description[2]}' if description[2] else ''))
			if image:
				embed.set_image(url=image[1])
			if level and location and requirements:
				embed.add_field(
					name = 'Quest Details',
					value = f'```Level: {self.unescape(level[1])}\nLocation: {self.unescape(location[1])}\nRequirements: {self.unescape(requirements[1])}```',
					inline = False)
			for guild in self.guilds:
				if embed.title not in self.guilds[guild]['existingPosts']:
					try:
						await self.guilds[guild]['channel'].send(embed=embed)
					except Exception as e:
						print('Error posting mhw event', e)
					finally:
						self.guilds[guild]['existingPosts'].append(embed.title)
				if embed.title not in self.guilds[guild]['activeEvents']:
					self.guilds[guild]['activeEvents'].append(embed.title)

	@updateLoop.before_loop
	async def before_updateLoop(self):
		await self.bot.wait_until_ready()
		guild = self.bot.get_guild(254746234466729987)
		for channel in guild.text_channels:
			if channel.name == 'mhw-events':
				print(f'Will manage {channel.name} for {guild.name}')
				self.guilds[guild] = {
					'activeEvents': [ ],
					'existingPosts': [ ],
					'channel': channel,
				}

def setup(bot):
	bot.add_cog(MHW(bot))