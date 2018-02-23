from bs4 import BeautifulSoup
from discord.ext import commands
import pymysql.cursors
from stuff import fetchWebpage

class HOTS():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def hots(self, ctx):
		"""Show weekly Heroes of the Storm free-to-play rotation"""
		await ctx.trigger_typing()
		try:
			page = await fetchWebpage(self, 'https://us.battle.net/heroes/en/')
		except:
			await ctx.send('I was unable to access https://us.battle.net/heroes/en/')
			return False
			
		heroes = []
		try:
			soup = BeautifulSoup(page, "html.parser")

			for div in soup.find_all('div', class_ = 'HeroesOverview-item'):
				for div2 in div.find_all('div', class_ = 'HeroesOverview-itemContent'):
					for div3 in div2.find_all('div', class_ = 'HeroesOverview-group'):
						for a in div.find_all('a'):
							if 'data-analytics' in a.attrs and a.get('data-analytics') == "homepage-hero-link":
								heroes.append(a.get('data-analytics-placement').capitalize())
								print(a.get('data-analytics-placement').capitalize())
		except:
			await ctx.send('I was unable to parse the html or something')
			return False

		if heroes:
			await ctx.send('Current Heroes of the Storm Free-to-Play Rotation:\n' + ', '.join(str(hero) for hero in heroes))
		else:
			await ctx.send('I was unable to find any heroes, what\'s up with that?')

		#embed=discord.Embed(title='Test', description='Beep', url='https://www.google.com', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))

def setup(bot):
	bot.add_cog(HOTS(bot))