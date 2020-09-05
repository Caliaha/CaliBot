import discord
from discord.ext import commands
import json
from stuff import deleteMessage, doThumbs, fetchWebpage, superuser
#import urllib.parse

class Reddit(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(hidden=True)
	@superuser()
	@doThumbs()
	@commands.guild_only()
	async def media(self, ctx, url):
		"""Gets direct link to media from url"""
		try:
			page = await fetchWebpage(self, f'{url}.json')
		except Exception as e:
			print(e)
			await ctx.send('Could not access webpage, was that a valid url?')
			return False
		
		try:
			data = json.loads(page)
		except Exception as e:
			print(e)
			await ctx.send('That does not appear to be json')
			return False

		try:
			c = data[0]['data']['children'][0]['data']
		except:
			await ctx.send('Could not find the bit of json I need')
			return False

		try:
			if c['post_hint'] == 'hosted:video':
				await ctx.send(f"<{c['media']['reddit_video']['fallback_url']}>")
				return True
			if c['post_hint'] == 'image':
				await ctx.send(f"<{c['url']}>")
				return True
			await ctx.send('I do not know how to handle {c["post_hint"]}')
		except:
			await ctx.send('Something went wrong')
			return False

def setup(bot):
	bot.add_cog(Reddit(bot))