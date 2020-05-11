import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import tasks, commands
import hashlib
import pymysql.cursors
import re
from stuff import doThumbs, fetchWebpage
from urllib.parse import urlparse
import urllib.request

class Nintendo(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.updateLoop.start()

	def cog_unload(self):
		self.updateLoop.cancel()

	@tasks.loop(minutes=5.0)
	async def updateLoop(self):
		try:
			page = await fetchWebpage(self, 'https://www.nintendo.com/whatsnew/')
			linkP = re.compile('<!-- SDI include \(path: (.*?), resourceType: noa/components/content/whats-new/home/nintendo-news-list\) -->')
			link = linkP.search(page)
			if link:
				print(link[1])
				newsPage = await fetchWebpage(self, f'https://www.nintendo.com{link[1]}')
		except:
			print('Unable to fetch wowhead.com/news')
			
		#newsPattern = re.compile()
		try: # Nothing wrong with just try/excepting the whole thing is there
			soup = BeautifulSoup(newsPage, "html.parser")

			for li in reversed(soup.find_all('li')):
				embed = discord.Embed(title='Test', description='Beep', url='https://www.google.com', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
				#print(li)
				#continue
				postID = ''
				embed.url = f'https://www.nintendo.com{li.a["href"]}'
				#print(li)
				for div in li.find_all('div'):
					clas = div.attrs.get('class')[0]
					print(clas)
					if clas == 'logo':
						postID = f'{postID}{div.text.strip()}'
						if div.text.strip() != 'no-system':
							embed.set_author(name=div.text.strip().capitalize())
					if clas == 'short-body': # Title
						postID = f'{postID}{div.h2.text.strip()}'
						embed.title = div.h2.text.strip()
						embed.description = div.span.text.strip()
						print('Added title and description')
					if clas == 'banner':
						embed.set_image(url=f'https://www.nintendo.com{div.img["src"]}')
						print('Added Image', f'https://www.nintendo.com{div.img["src"]}')
					if clas == 'date':
						embed.set_footer(text = f'{div.text.strip()}')
						print('Added date')

				postID = hashlib.sha1(postID.encode()).hexdigest()
				print(postID)
				#postID = div.get('id')
				if postID is None:
				 #print('PostID was None, skipping')
				 continue

				for guild in self.bot.guilds:
					for channel in guild.text_channels:
						if channel.name == 'nintendo':
							if not await self.checkIfPosted(guild.id, postID):
								#print("Not posted")
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
				cursor.execute(sql, (guildID, 'nintendo', postID))
				connection.commit()
		except:
			print("Unable to storePostedData for nintendo")
		finally:
			connection.close()

	async def checkIfPosted(self, guildID, postID):
		#print(guildID, postID)
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT * FROM `news` WHERE `guild`=%s AND `category` = %s AND `identifier`=%s LIMIT 1"
				cursor.execute(sql, (guildID, 'nintendo', postID))
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
	bot.add_cog(Nintendo(bot))