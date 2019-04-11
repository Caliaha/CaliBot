import discord
from discord.ext import commands
import pymysql.cursors
from stuff import doThumbs

class Info(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	@doThumbs()
	async def info(self, ctx, member: discord.Member):
		"""Shows info for member"""

		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `info` FROM `usersettings` WHERE `discordID`=%s"
				cursor.execute(sql, member.id)
				result = cursor.fetchone()
				if result is not None and result['info'] != None:
					if (len(result['info']) > 300):
						await ctx.send('Message too long, sent as direct message', delete_after=20)
						await ctx.author.send('Info for {}:\n{}'.format(member.name, result['info']))
					else:
						await ctx.send('Info for {}:\n{}'.format(member.name, result['info']))
					return True
				else:
					return False
		finally:
			connection.close()

	@commands.command()
	@doThumbs()
	async def setinfo(self, ctx, *, info = None):
		"""Sets info for yourself"""
		
		if info == '':
			info = None
		
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `info` FROM `usersettings` WHERE `discordID`=%s"
				cursor.execute(sql, (ctx.author.id))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `usersettings` (`discordID`, `info`) VALUES(%s, %s)"
					cursor.execute(sql, (ctx.author.id, info))
					connection.commit()
				else:
					sql = "UPDATE `usersettings` SET `info` = %s WHERE `discordID` = %s LIMIT 1"
					cursor.execute(sql, (info, ctx.author.id))
					connection.commit()
				return True
		except:
			return False
		finally:
			connection.close()

def setup(bot):
	bot.add_cog(Info(bot))