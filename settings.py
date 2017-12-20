import discord
from discord.ext import commands
import pymysql.cursors
from stuff import checkPermissions, getSnowflake, no_pm, superuser, isSuperUser

class Settings():
	def __init__(self, bot):
		self.bot = bot
		self.settings = [ 'phonetic', 'realm', 'character', 'battletag' ]

	@commands.command(pass_context=True)
	@no_pm()
	@checkPermissions('set')
	async def set(self, ctx, setting, value, member = ''):
		if setting not in self.settings:
			await self.bot.send_message(ctx.message.channel, 'Usage: !set variable value')
			return False
		await self.bot.send_typing(ctx.message.channel)
			
		if value == '':
			value = None
		userid = ctx.message.author.id
		if member:
			if isSuperUser(self, ctx):
				userid = getSnowflake(member)
				if not userid:
					return False
			else:
				await self.bot.send_message(ctx.message.channel, 'You do not have permission to use this command in this manner')
				return False
		else:
			member = ctx.message.author.name
			
		connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `" + setting + "` FROM `usersettings` WHERE `discordID`=%s"
				cursor.execute(sql, (userid))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `usersettings` (`discordID`, `" + setting + "`) VALUES(%s, %s)"
					cursor.execute(sql, (userid, value))
					connection.commit()
				else:
					sql = "UPDATE `usersettings` SET `" + setting + "` = %s WHERE `discordID` = %s LIMIT 1"
					cursor.execute(sql, (value, userid))
					connection.commit()
				await self.bot.send_message(ctx.message.channel, setting + ' has been set to **' + str(value) + '** for ' + member)
		finally:
			connection.close()

def setup(bot):
	bot.add_cog(Settings(bot))