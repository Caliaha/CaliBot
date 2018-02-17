import discord
from discord.ext import commands
import json
import os.path
from PIL import Image, ImageDraw, ImageFont
import pymysql.cursors
from stuff import cleanUserInput, fetchWebpage

class osu():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def osu(self, ctx, user=None):
		"""Look up osu! player profile"""
		if user is None or ctx.message.author.guild.get_member_named(user):
			try:
				user = ctx.message.author.guild.get_member_named(user)
			except:
				pass

			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			try:
				with connection.cursor() as cursor:
					#Check if entry exists then update or create one
					sql = "SELECT `osu` FROM `usersettings` WHERE `discordID`=%s"
					try:
						discordID = user.id
						user = user.name
					except:
						discordID = ctx.message.author.id
					cursor.execute(sql, discordID)
					result = cursor.fetchone()
					if (result and result['osu'] is not None):
						user = result['osu']
			except:
				print("Trouble with database thing")
				pass
			finally:
				connection.close()
		#user = 'Cookiezi' # Vaxei
		data = json.loads(await fetchWebpage(self, 'https://osu.ppy.sh/api/get_user?k=' + self.bot.APIKEY_OSU + '&u=' + user + '&type=string'))
		with open('osu/avatar.jpg', 'wb') as f:
			f.write(await fetchWebpage(self, 'https://a.ppy.sh/' + data[0]['user_id'], True))
		countryFlag = cleanUserInput(data[0]['country'].lower())
		if not os.path.exists('osu/{}.gif'.format(countryFlag)):
			with open('osu/{}.gif'.format(countryFlag), 'wb') as f:
				f.write(await fetchWebpage(self, 'https://s.ppy.sh/images/flags/{}.gif'.format(countryFlag), True))
		avatarImage = Image.open('osu/avatar.jpg', 'r')
		countryImage = Image.open('osu/{}.gif'.format(countryFlag), 'r')

		if avatarImage.width > 200:
			print('Cropped avatar, too wide')
			avatarImage.crop((0, 0, 200, avatarImage.height))
		if avatarImage.height > 200:
			print('Cropped avatar, too tall')
			avatarImage.crop((0, 0, avatarImage.width, 200))

		
		font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 18)
		bigFont = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 30)
		texts = {}
		texts['name'] = "{}".format(data[0]['username'])
		texts['performance'] = "Performance: {:.0f}pp (#{:,}) #{:,}".format(float(data[0]['pp_raw']), int(data[0]['pp_rank']), int(data[0]['pp_country_rank']))
		texts['rankedScore'] = "Ranked Score: {:,}".format(int(data[0]['ranked_score']))
		texts['hitAccuracy'] = "Hit Accuracy: {:.1f}".format(float(data[0]['accuracy']))
		#texts['maximumCombo'] = "Maximum Combo: {}".format(data[0][''])
		texts['level'] = "Level: {}".format(int(data[0]['level'].split('.')[0]))
		
		print(font.getsize(texts['performance']))
		countryLocation = font.getsize(texts['performance']) # For country flag placement and height reference
		offset = 0
		imageHeight = avatarImage.height
		if (countryLocation[1] + 2) * len(texts) + 64 > imageHeight:
			imageHeight = (countryLocation[1] + 2) * len(texts) + 64
		imageWidth = avatarImage.width + 2 + countryLocation[0] + countryImage.width + 2
		
		ranks = { }
		ranks['XRank'] = [ Image.open('osu/X.png', 'r'), data[0]['count_rank_ss'] ]
		ranks['SRank'] = [ Image.open('osu/S.png', 'r'), data[0]['count_rank_s'] ]
		ranks['ARank'] = [ Image.open('osu/A.png', 'r'), data[0]['count_rank_a'] ]
		
		rankOffsetX = avatarImage.width + 2
		rankOffsetY = (countryLocation[1] + 2) * len(texts)
		
		print(len(texts))
		img = Image.new('RGBA', (imageWidth + 300, imageHeight), (54, 57, 63))
		img.paste(avatarImage, (0, 0))
		img.paste(countryImage, (countryLocation[0] + avatarImage.width + 2, countryLocation[1] + 5))
		draw = ImageDraw.Draw(img)
		for text in texts:
			draw.text((avatarImage.width + 2, offset), texts[text], (255, 255, 255), font=font)
			offset = offset + countryLocation[1] + 2
		

		for rank in ranks:
			img.alpha_composite(ranks[rank][0], (rankOffsetX, rankOffsetY))
			draw.text((rankOffsetX + ranks[rank][0].width + 2, rankOffsetY + 3), ranks[rank][1], font=bigFont)
			rankOffsetX = rankOffsetX + ranks[rank][0].width + 2 + bigFont.getsize(ranks[rank][1])[0] + 5
		
		print(imageWidth, rankOffsetX, avatarImage.width + 2 + countryLocation[0] + countryImage.width + 2)
		imageWidth = avatarImage.width + 2 + countryLocation[0] + countryImage.width + 2
		if rankOffsetX > imageWidth:
			imageWidth = rankOffsetX
		if img.width > imageWidth:
			img = img.crop((0, 0, imageWidth, imageHeight))

		img.save('osu/osu.png')
		await ctx.send(file=discord.File('osu/osu.png'))
		os.remove('osu/avatar.jpg')
		os.remove('osu/osu.png')

def setup(bot):
	bot.add_cog(osu(bot))