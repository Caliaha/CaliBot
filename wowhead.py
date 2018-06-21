import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import pymysql.cursors
import re
from stuff import doThumbs, fetchWebpage, isBotOwner

class WowHead():
	def __init__(self, bot):
		self.bot = bot
		self.bot.loop.create_task(self.background_lookup())

	async def background_lookup(self):
		await self.bot.wait_until_ready()
		while not self.bot.is_closed():
			try:
				newsPage = await fetchWebpage(self, 'http://www.wowhead.com/news')
			except:
				print('Unable to fetch wowhead.com/news')
				
			#newsPattern = re.compile()
			
			soup = BeautifulSoup(newsPage, "html.parser")

			for div in soup.find_all('div', class_ = 'news-post news-post-style-teaser'):
				embed = discord.Embed(title='Test', description='Beep', url='https://www.google.com', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
				postID = div.get('id')
				if postID is None:
				 print('PostID was None, skipping')
				 continue

				for h1 in div.find_all('h1', class_ = 'heading-size-1'):
					embed.title = h1.text

				span = div.find('span', class_ = 'date-tip')

				postTime = span.get('title')
				author = span.parent.find('a').text
				if postTime and author:
					embed.set_footer(text = 'Posted {} by {}'.format(postTime, author))
				
				for a in div.find_all('a'):
					if 'class' in a.attrs:
						if 'news-post-teaser-image' in a.get('class'):
							if 'style' in a.attrs:
								style = a.get('style')
								linkPattern = re.compile('url\(\/\/(.*?\.jpg)')
								linkMatch = linkPattern.search(style)
								
								if (linkMatch):
									embed.set_image(url='http://' + linkMatch[1])
						if 'news-post-type' in a.get('class'):
							if (a.text):
								embed.set_author(name=a.text)

							embed.url = a.get('href')

				descriptionPattern = re.compile('WH\.markup\.printHtml\(\"(.*?)\"')
				descriptionMatch = descriptionPattern.search(div.text)
				if descriptionMatch:
					description = self.subMarkup(descriptionMatch[1])
					embed.description = description

				for guild in self.bot.guilds:
					for channel in guild.text_channels:
						if channel.name == 'wowhead':
							if not await self.checkIfPosted(guild.id, postID):
								print("Not posted")
								await channel.send(embed=embed)
								await self.storePostedData(guild.id, postID)
							break
			await asyncio.sleep(120)

	def subMarkup(self, text):
		text = text.replace('[b]', '**')
		text = text.replace('[\/b]', '**')
		
		text = re.sub('\[.*?\]', '', text)
		text = re.sub(r'\\r\\n', '\n', text)
		
		return text

	async def storePostedData(self, guildID, postID):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "INSERT INTO `wowhead` (`guild`, `post`) VALUES(%s, %s)"
				cursor.execute(sql, (guildID, postID))
				connection.commit()
		except:
			print("Unable to storePostedData for wowhead")
		finally:
			connection.close()

	async def checkIfPosted(self, guildID, postID):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT * FROM `wowhead` WHERE `guild`=%s AND `post`=%s LIMIT 1"
				cursor.execute(sql, (guildID, postID))
				result = cursor.fetchone()
				if result is None:
					return False
				else:
					return True
		except:
			print("Error with checkIfPosted")
		finally:
			connection.close()
		return True

def setup(bot):
	bot.add_cog(WowHead(bot))