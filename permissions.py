import discord
from discord.ext import commands
import pymysql.cursors
from stuff import no_pm

class Permissions():
	def __init__(self, bot):
		self.bot = bot
		self.commands = [ 'color', 'wow' ]
		
	async def superuser(self, ctx):
		if (ctx.message.server.owner == ctx.message.author):
			print("checkPermissions, user is server owner")
			return True
		if (ctx.message.author.id == self.bot.ADMINACCOUNT):
			print("checkPermissions, user is bot owner")
			return True
		return False

	@commands.command(pass_context=True, hidden = True)
	@no_pm()
	async def toggle(self, ctx, command: str):
		if not await self.superuser(ctx):
			await self.bot.send_message(ctx.message.channel, "You don't have permission to use that command.")
			return False
		
		if command not in self.commands:
			await self.bot.send_message(ctx.message.channel, "I don't understand that command, please check your spelling.")
			return False
		
		connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		serverID = ctx.message.server.id
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `disabled` FROM `permissions` WHERE `serverID`=%s AND `command`=%s"
				cursor.execute(sql, [serverID, command])
				result = cursor.fetchone()
				disabled = 0
				if result is not None:
					if (result["disabled"] == 0):
						disabled = 1
					sql = "UPDATE `permissions` SET `disabled` = %s WHERE `serverID` = %s LIMIT 1"
					cursor.execute(sql, [disabled, serverID])
					connection.commit()
				else:
					sql = "INSERT INTO `permissions` (`serverID`, `command`, `disabled`) VALUES(%s, %s, %s)"
					disabled = 1
					cursor.execute(sql, [serverID, command, disabled])
					connection.commit()
				if disabled:
					await self.bot.send_message(ctx.message.channel, "Commands related to " + command + " have been disabled")
				else:
					await self.bot.send_message(ctx.message.channel, "Commands related to " + command + " have been enabled")
		finally:
			connection.close()

def setup(bot):
	bot.add_cog(Permissions(bot))