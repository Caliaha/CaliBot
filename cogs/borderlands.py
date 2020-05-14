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

	@tasks.loop(minutes=60.0)
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
				description = await self.fetchNewsDescription(url)
				
				embed = discord.Embed(title=title, description=description, url=f'https://borderlands.com{url}', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
				embed.set_image(url=f'{thumbnail}') # Check if fully qualified
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