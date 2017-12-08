import discord
from discord.ext import commands
import html
import re
import urllib.request

BACKPACKTF_QUALITIES = [ 'Strange', 'Unique', 'Collector\'s', 'Australium', 'Vintage', 'Genuine' ]

class TeamFortress2():
	def __init__(self, bot):
		self.bot = bot

	def fetchPricingData(self, url):
		headers = { 'User-Agent' : self.bot.USER_AGENT, 'Referer' : 'https://backpack.tf' }
		itemData = urllib.request.urlopen(urllib.request.Request('https://backpack.tf' + url, data=None, headers=headers)).read().decode('utf-8')
 
		steamMarketPriceP = re.compile('<a class="price-box" href="(https://steamcommunity.com/.*?)" data-tip="top" target="_blank" title="Steam Community Market">.*?<div class="value">.*?(\$\d+\.\d+).*?</div>.*?<div class="subtitle">.*?(\d+ sold recently)', re.DOTALL)
		keyPriceP = re.compile('<div class="value">\s+(.*?)\s+</div>.*?<div class="subtitle">(\s+)(.*?)\s+</div>', re.DOTALL)
 
		keyPrice = keyPriceP.search(itemData)
		steamPrice = steamMarketPriceP.search(itemData)
 
		if keyPrice is None:
			keyPrice = "N/A"
		else:
			keyPrice = keyPrice[1]
		if steamPrice is None:
			steamPrice = "N/A"
		else:
			steamPrice = steamPrice[2]
 
		return steamPrice, keyPrice

	@commands.command(pass_context=True)
	async def tf2(self, ctx, item: str):
		await self.bot.send_typing(ctx.message.channel)
		headers = { 'User-Agent' : self.bot.USER_AGENT, 'Referer' : 'https://backpack.tf' }
		print("Searching for", urllib.parse.quote_plus(item))
		try:
			search = urllib.request.urlopen(urllib.request.Request('https://backpack.tf/im_feeling_lucky?text=' + urllib.parse.quote_plus(item), data=None, headers=headers)).read().decode('utf-8')
		except:
			await self.bot.send_message(ctx.message.channel, 'I had trouble performing the search')
			return False

		itemNameP = re.compile('<meta property="og:title".*?content="(.*?)">', re.DOTALL)
		itemName = itemNameP.search(search)

		imageUrlP = re.compile('<meta property="og:image" content="(.*?)">')
		imageUrl = imageUrlP.search(search)
		if imageUrl is None:
			imageUrl = 'https://steamcdn-a.akamaihd.net/apps/440/icons/oh_xmas_tree.3edfe2fcf8345f13646896dd4495793cf18a826d.png' #  A Rather Festive Tree, used as a placeholder
		else:
			imageUrl = imageUrl[1]
		if re.search('^/', imageUrl): #Image is relative link
			imageUrl = 'https://backpack.tf' + imageUrl

		if itemName is None:
			itemName = item
		else:
			itemName = html.unescape(itemName[1])

		qualitiesP = re.compile('<div class="btn-group btn-group-sm stats-quality-list ">(.*?)</div>', re.DOTALL)
		qualities = qualitiesP.search(search)

		if qualities is not None:
			embed=discord.Embed(title=itemName, url='https://backpack.tf/im_feeling_lucky?text=' + urllib.parse.quote_plus(item), color=0x9cf5a0)
			embed.set_thumbnail(url=imageUrl)
			#embed.add_field(name="Unique", value="3-3.55 Keys<br>$8.74 Market", inline=True)
			#embed.add_field(name="Strange", value="6.05 Keys<br>$16.56", inline=True)

			print(itemName)
			qualityP = re.compile('<a href="(.*?)"(.*?)>\s*?(\w.*?\w)\s*?</a>', re.DOTALL)
			#print(qualities[1])
			print("Found qualities")
			found = False
			for match in qualityP.findall(qualities[1]):
				found = True
				itemQuality = html.unescape(match[2])
				if itemQuality not in BACKPACKTF_QUALITIES:
					continue
				steamPrice, keyPrice = self.fetchPricingData(match[0])
				embed.add_field(name=itemQuality, value=keyPrice + '\n' + steamPrice + ' Market', inline=True)
				print(match[2] + ' is currently ' + steamPrice + ' ' + keyPrice)
			if found is True:
				try:
					await self.bot.send_message(ctx.message.channel, embed=embed)
				except discord.HTTPException as e:
					print(e)
					return False
				return True
			await self.bot.send_message(ctx.message.channel, 'Item lookup has failed, please check your spelling')
			return False

def setup(bot):
	bot.add_cog(TeamFortress2(bot))