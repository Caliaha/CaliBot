import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import hashlib
import pymysql.cursors
import re
from stuff import doThumbs, fetchWebpage
from urllib.parse import urlparse
import urllib.request

class MapleStory():
	def __init__(self, bot):
		self.bot = bot
		self.bot.loop.create_task(self.background_lookup())

	async def background_lookup(self):
		await self.bot.wait_until_ready()
		while not self.bot.is_closed():
			try:
				newsPage = await fetchWebpage(self, 'http://maplestory2.nexon.net/en/news')
			except:
				print('Unable to fetch http://maplestory2.nexon.net/en/news')
			
			soup = BeautifulSoup(newsPage, "html.parser")

			for figure in soup.find_all('figure', class_ = 'news-item'):
				figureString = str(figure)
				embed = discord.Embed(title='Test', description='Beep', url='https://www.google.com', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))

				urlPattern = re.compile('<a class="news-item-link" href="(.*?)">')
				datePattern = re.compile('<time>(.*?)</time')
				titlePattern = re.compile('<h2>(.*?)</h2>')
				textPattern = re.compile('<div class="short-post-text">(.*?)</div>')
				categoryPattern = re.compile('<span class="news-category-tag.*?">(.*?)</span>')
				imagePattern = re.compile('<div class="news-item-image" style="background-image:url\(\'(.*?)\'\)"></div>')

				urlMatch = urlPattern.search(figureString)
				dateMatch = datePattern.search(figureString)
				titleMatch = titlePattern.search(figureString)
				textMatch = textPattern.search(figureString)
				categoryMatch = categoryPattern.search(figureString)
				imageMatch = imagePattern.search(figureString)
				
				if urlMatch:
					url = urlMatch[1]
					if not urlparse(url).netloc:
						url = 'https://maplestory2.nexon.net' + url
					embed.url = url
				
				if dateMatch:
					embed.set_footer(text = 'Posted {}'.format(dateMatch[1]))
				
				if imageMatch:
					embed.set_image(url=imageMatch[1])
				
				if categoryMatch:
					embed.set_author(name=categoryMatch[1])
					
				if textMatch:
					embed.description = textMatch[1]
				
				if titleMatch:
					embed.title = titleMatch[1]
					
				postToHash = '{}:{}:{}'.format(titleMatch[1], textMatch[1], dateMatch[1])

				postHash = hashlib.sha512(bytes(postToHash, "utf8")).hexdigest()

				for guild in self.bot.guilds:
					for channel in guild.text_channels:
						if channel.name == 'maplestory':
							if not await self.checkIfPosted(guild.id, postHash):
								await channel.send(embed=embed)
								await self.storePostedData(guild.id, postHash)
							break
			await asyncio.sleep(600)

	def subMarkup(self, text, type):
		def urlFix(match):
			url = match.group(1).replace('\\/', '/')
			name = match.group(2)
			if name == '':
				name = url
			if not urlparse(url).netloc:
				url = 'https://maplestory2.nexon.com' + url
			#print('[{}]({})'.format(match.group(2), url))
			return '[{}]({})'.format(name, url)

		if type == 'bb':
			text = text.replace('[b]', '**')
			text = text.replace('[\/b]', '**')
		
			text = text.replace('\\\"', '"')
			text = re.sub('\[url=(.*?)\](.*?)\[\\\/url\]', urlFix, text)
			#text = re.sub('\<a href=\\\"(.*?)\\\".*?\>(.*?)\<\\\/a\>', urlFix, text)
			#text = re.sub('<iframe.*?<\\\/iframe>', '', text)
			text = re.sub('\[html\].*?\[\\\/html\]', '', text)
			text = re.sub('\[.*?\](?!\()', '', text)
			text = re.sub(r'\\r\\n', '\n', text)
		
		if type == 'html':
			print('Start', text)
			text = text.replace('\"', '"')
			text = text.replace('\\\\', '\\')
			text = text.replace('\/', '/')
			text = text.replace('&amp;', '&')
			text = text.replace('&quot;', '"')
			text = text.replace('&lt;', '<')
			text = text.replace('&gt;', '>')
			text = text.replace('&nbsp;', ' ')
			text = text.replace('<b>', '**')
			text = text.replace('</b>', '**')
			text = text.replace('<i>', '***')
			text = text.replace('</i>', '***')
			text = re.sub('<iframe.*?</iframe>', '', text)
			text = re.sub('<a href=\"(.*?)\".*?>(.*?)<\/a>', urlFix, text)
			text = re.sub('\<br\/\>', '\n', text)
			text = re.sub(r'\\r', '', text) # Filter out weird \r's that they have added
			text = re.sub('<div.*?>(.*?)<\/div>', '$1', text)

		print(type, text)
		return text

	async def storePostedData(self, guildID, postHash):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "INSERT INTO `maplestory` (`guild`, `postHash`) VALUES(%s, %s)"
				cursor.execute(sql, (guildID, postHash))
				connection.commit()
		except:
			print("Unable to storePostedData for maplestory")
		finally:
			connection.close()

	async def checkIfPosted(self, guildID, postHash):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT * FROM `maplestory` WHERE `guild`=%s AND `postHash`=%s LIMIT 1"
				cursor.execute(sql, (guildID, postHash))
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
	bot.add_cog(MapleStory(bot))