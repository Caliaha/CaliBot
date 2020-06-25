import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import tasks, commands
import hashlib
import html
import pymysql.cursors
import re
from stuff import doThumbs, fetchWebpage
from urllib.parse import urlparse
import urllib.request

class Borderlands(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.updateLoop.start()

	def cog_unload(self):
		self.updateLoop.cancel()

	async def fetchNewsDescription(self, url):
		page = await fetchWebpage(self, f'https://borderlands.com{url}')
		
		description = ''
		
		soup = BeautifulSoup(page, "html.parser")
		for div in soup.find_all('div', class_ = 'wysiwyg-content'):
			for p in div.find_all('p'):
				for p2 in p.find_all('p'):
					if len(description) + len(p2.text) + 1 <= 2048:
						description = f'{description}\n{p2.text}'
		return description

	def subMarkup(self, text):
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
				url = 'https://borderlands.com' + url
			#print('[{}]({})'.format(match.group(2), url))
			return '[{}]({})'.format(name, url)

		text = text.replace('\"', '"')
		text = text.replace('\\\\', '\\')
		text = text.replace('\/', '/')
		text = text.replace('&amp;', '&')
		text = text.replace('&quot;', '"')
		text = text.replace('&lt;', '<')
		text = text.replace('&gt;', '>')
		text = text.replace('&nbsp;', ' ')
		text = text.replace('&ldquo;', '“')
		text = text.replace('&rdquo;', '”')
		text = text.replace('&rsquo;', '’')
		text = text.replace('<b>', '**')
		text = text.replace('</b>', '**')
		text = text.replace('<strong>', '**')
		text = text.replace('</strong>', '**')
		text = text.replace('<i>', '***')
		text = text.replace('</i>', '***')
		text = text.replace('<em>', '***')
		text = text.replace('</em>', '***')
		text = text.replace('<br />', '')
		text = text.replace('<table>', '')
		text = text.replace('</table>', '')
		text = text.replace('<br />', '')
		text = text.replace('<tr>', '')
		text = text.replace('</tr>', '')
		text = text.replace('<td>', '')
		text = text.replace('</td>', '')
		text = text.replace('</p><p>', '\n')
		text = text.replace('<p>', '')
		text = text.replace('</p>', '')
		text = re.sub('<iframe.*?</iframe>', '', text)
		text = re.sub('<img src.*? />', 'IMAGE', text)
		text = re.sub('(<a href.*?<\/a>(/">)?)', urlFix, text)
		text = re.sub('\<br\/\>', '\n', text)
		text = re.sub(r'\\r', '', text) # Filter out weird \r's that they have added
		text = re.sub('<div.*?>(.*?)<\/div>', '$1', text)
		text = re.sub('<ul>.*?</ul>', '', text)
		text = re.sub('<li>.*?</li>', '', text)

		#print(type, text)
		return text

	async def fetchAltNewsDescription(self, url):
		page = await fetchWebpage(self, f'https://borderlands.com{url}')
		
		description = ''
		listItems = [ ]
		newsMatchP = re.compile('<div class="relative wysiwyg-content font-body-light leading-normal mt-md -mb-md">(.*?)</div>', re.DOTALL | re.MULTILINE)
		
		content = newsMatchP.search(page)
		if content:
			#print(content[1])
			for li in re.findall('<li>(.*?)</li>', content[1]):
				listItems.append(li)

			description = self.subMarkup(content[1]).strip()
		return description[0:2048], listItems

	@tasks.loop(minutes=10.0)
	async def updateLoop(self):
		try:
			newsPage = await fetchWebpage(self, 'https://borderlands.com/en-US/news/')
			newsPage = html.unescape(newsPage)

			newsItemPattern = re.compile('url: "(.*?)",\n\t\t\ttitle: "(.*?)",\n\t\t\tcategory: \'(.*?)\',\n\t\t\tthumb: "(.*?)",\n') #

			newsItems = newsItemPattern.findall(newsPage)

			for newsItem in reversed(newsItems):
				url = newsItem[0]
				title = newsItem[1]
				category = newsItem[2]
				thumbnail = newsItem[3]
				description, listItems = await self.fetchAltNewsDescription(url)
				
				embed = discord.Embed(title=title, description=description, url=f'https://borderlands.com{url}', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
				embed.set_image(url=f'{thumbnail}') # Check if fully qualified
				if listItems:
					li = "\n".join(listItems)
					li = li[0:2048]
					embed.add_field(name='Additional Notes', value=li)
				postID = hashlib.sha1(f'{url}{title}{thumbnail}{category}'.encode()).hexdigest() # Maybe don't do it like this
				if postID is None:
				 print('PostID was None, skipping')
				 continue

				for guild in self.bot.guilds:
					print(guild.name)
					if guild.name != 'Cheesedoodles':
						continue
					print('Beep', postID)
					for channel in guild.text_channels:
						if channel.name == 'borderlands':
							print('Found channel')
							if not await self.checkIfPosted(guild.id, postID):
								print('Posting data')
								await channel.send(embed=embed)
								await self.storePostedData(guild.id, postID)
							break
		except Exception as e:
			print(e)
			#pass # Bugs Squashed

	async def storePostedData(self, guildID, postID):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "INSERT INTO `news` (`guild`, `category`, `identifier`) VALUES(%s, %s, %s)"
				cursor.execute(sql, (guildID, 'borderlands', postID))
				connection.commit()
		except:
			print("Unable to storePostedData for borderlands")
		finally:
			connection.close()

	async def checkIfPosted(self, guildID, postID):
		#print(guildID, postID)
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT * FROM `news` WHERE `guild`=%s AND `category` = %s AND `identifier`=%s LIMIT 1"
				cursor.execute(sql, (guildID, 'borderlands', postID))
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
	bot.add_cog(Borderlands(bot))