import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import tasks, commands
import pymysql.cursors
import re
from stuff import doThumbs, fetchWebpage
from urllib.parse import urlparse
import urllib.request

class WowHead(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.updateLoop.start()

	def cog_unload(self):
		self.updateLoop.cancel()

	@tasks.loop(minutes=5.0)
	async def updateLoop(self):
		try:
			newsPage = await fetchWebpage(self, 'http://www.wowhead.com/news')
		except:
			print('Unable to fetch wowhead.com/news')
			
		#newsPattern = re.compile()
		try: # Nothing wrong with just try/excepting the whole thing is there
			soup = BeautifulSoup(newsPage, "html.parser")

			for div in reversed(soup.find_all('div', class_ = 'news-post news-post-style-teaser')):
				embed = discord.Embed(title='Test', description='Beep', url='https://www.google.com', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
				postID = div.get('id')
				if postID is None:
				 #print('PostID was None, skipping')
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
							url = a.get('href')
							#print('Setting url to', url)
							if not urlparse(url).netloc:
								url = 'https://www.wowhead.com' + url
							print(f'Set URL to {url}')
							embed.url = url
							if 'style' in a.attrs:
								style = a.get('style')
								linkPattern = re.compile('url\((.*?\.(jpg|png))')
								linkMatch = linkPattern.search(style)
								
								if (linkMatch):
									#print(linkMatch[1])
									print('Added image', linkMatch[1])
									embed.set_image(url=linkMatch[1]) #url='http://' +
						if 'news-post-type' in a.get('class'):
							if (a.text):
								embed.set_author(name=a.text)

							#url = a.get('href')
							#if not urlparse(url).netloc:
							#	url = 'https://www.wowhead.com' + url
							#print(f'URL: {url}')
							#embed.url = url

				descriptionPattern = re.compile('WH\.markup\.printHtml\(\"(.*?)\", \"news')
				descriptionPattern2 = re.compile('<noscript>\n?(.*?)<\/noscript>')
				noscript = str(div.find('noscript'))
				
				if noscript:
					descriptionMatch = descriptionPattern2.search(noscript)
					if descriptionMatch:
						description = self.subMarkup(descriptionMatch[1], 'html')
						embed.description = description
						#print('html', description)
				else:
					descriptionMatch = descriptionPattern.search(div.text)
					if descriptionMatch:
						description = self.subMarkup(descriptionMatch[1], 'bb')
						embed.description = description
						#print('bb', description)

				for guild in self.bot.guilds:
					for channel in guild.text_channels:
						if channel.name == 'wowhead':
							if not await self.checkIfPosted(guild.id, postID):
								#print("Not posted")
								try:
									await channel.send(embed=embed)
								except Exception as e:
									print('Error in wowhead:', e)
								finally:
									await self.storePostedData(guild.id, postID)
							break
		except:
			pass # Bugs Squashed

	def subMarkup(self, text, type):
		def urlFix(match):
			urlPattern1 = re.compile('<a href="https://<a href="(.*?)".*?>(.*?)</a>/">')
			url1Match = urlPattern1.search(match.group(1))
			urlPattern2 = re.compile('<a href="(.*?)".*?>(.*?)</a>')
			url2Match = urlPattern2.search(match.group(1))
			url = ''
			name = ''
			
			if url1Match:
				#print(url1Match[1], url1Match[2])
				url = url1Match[1]
				name = url1Match[2]
			elif url2Match:
				#print(url2Match[1], url2Match[2])
				url = url2Match[1]
				name = url2Match[2]
			#url = match.group(1).replace('\\/', '/')
			#name = match.group(2)
			#if name == '':
			#	name = url
			if not urlparse(url).netloc:
				url = 'https://www.wowhead.com' + url
			#print('[{}]({})'.format(match.group(2), url))
			return '[{}]({})'.format(name, url)
		
		def fetchAchievementName(match):
			url = 'http://www.wowhead.com/achievement={}'.format(match.group(1))
			try:
				page = urllib.request.urlopen(url).read().decode('utf-8') # Not using async here because it's easier lol FIX ME
				achievementPattern = re.compile('<meta property=\"og\:title\" content=\"(.*?)\">')
				achievement = achievementPattern.search(page)
				name = achievement[1]
			except:
				name = 'link'
				
			return '[{}]({})'.format(name, url)
		
		text = text.replace('\\u2019', '’')
		text = text.replace('\\u201c', '“')
		text = text.replace('\\u201d', '”')
		text = text.replace('\\u00e9', 'é')
		text = text.replace('\\u2014', '—')

		if type == 'bb':
			text = text.replace('[b]', '**')
			text = text.replace('[\/b]', '**')
		
			text = text.replace('\\\"', '"')

			text = re.sub('\[achievement=(\d+)\]', fetchAchievementName, text)
			text = re.sub('\[url=(.*?)\](.*?)\[\\\/url\]', urlFix, text)
			#text = re.sub('\<a href=\\\"(.*?)\\\".*?\>(.*?)\<\\\/a\>', urlFix, text)
			#text = re.sub('<iframe.*?<\\\/iframe>', '', text)
			text = re.sub('\[html\].*?\[\\\/html\]', '', text)
			text = re.sub('\[.*?\](?!\()', '', text)
			text = re.sub(r'\\r\\n', '\n', text)
		
		if type == 'html':
			#print('Beep')
			#rint(text)
			#return
			twitchPattern = re.compile('&lt;iframe src="https:\\\/\\\/player\.twitch\.tv\\\/.*?channel=(.*?)(&amp;autoplay=false)?"')
			twitchFound = twitchPattern.search(text)
			twitchWholePattern  = re.compile('&lt;iframe src=.*?www\.twitch\.tv&lt;</a>\\\/a&gt;', re.DOTALL)
			twitchWholeFound = twitchWholePattern.search(text)
			if twitchFound:
				print('Found twitch link')
				text = re.sub(twitchWholePattern, f'[Watch {twitchFound[1]} live on twitch.](https://www.twitch.tv/{twitchFound[1]})', text)
				print(f'[Watch {twitchFound[1]} live on twitch.](https://www.twitch.tv/{twitchFound[1]})')
				#[{}]({})'.format(name, url)
			if twitchWholeFound:
				print('TwitchWHOLE')
				
			#&lt;iframe src=&quot;https:\\\/\\\/player\.twitch\.tv\\\/.*?channel=(.*?)&quot;
			#print('Start', text)
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
			text = text.replace('<br />', '')
			text = text.replace('<table>', '')
			text = text.replace('</table>', '')
			text = text.replace('<br />', '')
			text = text.replace('<tr>', '')
			text = text.replace('</tr>', '')
			text = text.replace('<td>', '')
			text = text.replace('</td>', '')
			text = re.sub('<iframe.*?</iframe>', '', text)
			text = re.sub('(<a href.*?<\/a>(/">)?)', urlFix, text)
			text = re.sub('\<br\/\>', '\n', text)
			text = re.sub(r'\\r', '', text) # Filter out weird \r's that they have added
			text = re.sub('<div.*?>(.*?)<\/div>', '$1', text)

		#print(type, text)
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
		#print(guildID, postID)
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

	@updateLoop.before_loop
	async def before_updateLoop(self):
		await self.bot.wait_until_ready()

def setup(bot):
	bot.add_cog(WowHead(bot))