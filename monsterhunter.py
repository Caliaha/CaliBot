import datetime
import discord
from discord.ext import commands
import re
from stuff import BoxIt, deleteMessage, doThumbs, superuser, fetchWebpage, postWebdata

class MHW(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.MHW_EVENTS_URL = 'http://game.capcom.com/world/steam/us/schedule.html?utc=-4'

	def unescape(self, text):
		text = text.replace('&#039;', "'")
		text = text.replace('<br />', '')

		return text

	@commands.command()
	async def events(self, ctx):
		eventsPage = await fetchWebpage(self, self.MHW_EVENTS_URL)
		eventRegex = re.compile('<tr class=".*?">(.*?)</tr>', re.DOTALL)
		
		titleRegex = re.compile('<div class="title"><span>(.*?)</span>')
		imageRegex = re.compile('<td class="image"> <img src ="(.*?)" />')
		levelRegex = re.compile('<td class="level"><span>(.*?)</span></td>')
		descriptionRegex = re.compile('<p class="txt">(.*?)<span class="addTxt">(.*?)</span></p>')
		locationRegex = re.compile('<li>Locale: <span>(.*?)<span></li>')
		requirementsRegex = re.compile('<li>Requirements: <span> (.*?) </span></li>')
		availabilityRegex = re.compile('<p class="txt"> Available <span>(\d+)/(\d+) (\d+):(\d+)<br>〜<br>(\d+)/(\d+) (\d+):(\d+)</span>')
		
		
		now = datetime.datetime.now()
		for eventRaw in eventRegex.findall(eventsPage):
			event = ' '.join(eventRaw.split())
			#print(' '.join(event.split()))
			availabilityMatch = availabilityRegex.search(event)
			if availabilityMatch:
				availabilityStart = datetime.datetime(2019, int(availabilityMatch[1]), int(availabilityMatch[2]), int(availabilityMatch[3]), int(availabilityMatch[4]))
				availabilityEnd = datetime.datetime(2019, int(availabilityMatch[5]), int(availabilityMatch[6]), int(availabilityMatch[7]), int(availabilityMatch[8]))
				if availabilityStart <= now <= availabilityEnd:
					print('Event is available')
				else:
					continue

			title = titleRegex.search(event)
			image = imageRegex.search(event)
			level = levelRegex.search(event)
			description = descriptionRegex.search(event)
			location = locationRegex.search(event)
			requirements = requirementsRegex.search(event)
			
			embed=discord.Embed(
				title = self.unescape(title[1]),
				description = '',
				url = self.MHW_EVENTS_URL,
				color = discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
			
			embed.set_footer(text=f'Available {availabilityStart} ~ {availabilityEnd}')
			
			if description:
				embed.description = self.unescape(description[1] + (f'\n{description[2]}' if description[2] else ''))
			if image:
				embed.set_image(url=image[1])
			embed.add_field(
				name = 'Quest Details',
				value = f'```Level: {level[1]}\nLocation: {location[1]}\nRequirements: {requirements[1]}```',
				inline = False)
			await ctx.send(embed=embed)
			#return
			#await ctx.send(' '.join(event.split()))

def setup(bot):
	bot.add_cog(MHW(bot))