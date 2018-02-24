import discord
from discord.ext import commands
import pymysql.cursors
from stuff import getRoleID, superuser

class Permissions():
	def __init__(self, bot):
		self.bot = bot
		self.commands = [ 'color', 'wow' ]
		self.commandsRoleRestricted = [ 'color', 'set' ] # Fix this

	@commands.command(hidden = True)
	@commands.guild_only()
	@superuser()
	async def toggle(self, ctx, command: str):
		if command not in self.commands:
			await ctx.send("I don't understand that command, please check your spelling. The options for this command are as follows: " + ', '.join(self.commands))
			return False
		
		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		guildID = ctx.guild.id
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `disabled` FROM `permissions` WHERE `guildID`=%s AND `command`=%s"
				cursor.execute(sql, (guildID, command))
				result = cursor.fetchone()
				disabled = 0
				if result is not None:
					if (result["disabled"] == 0):
						disabled = 1
					sql = "UPDATE `permissions` SET `disabled` = %s WHERE `guildID` = %s LIMIT 1"
					cursor.execute(sql, (disabled, guildID))
					connection.commit()
				else:
					sql = "INSERT INTO `permissions` (`guildID`, `command`, `disabled`) VALUES(%s, %s, %s)"
					disabled = 1
					cursor.execute(sql, (guildID, command, disabled))
					connection.commit()
				if disabled:
					await ctx.send("Commands related to " + command + " have been disabled")
				else:
					await ctx.send("Commands related to " + command + " have been enabled")
		finally:
			connection.close()
		
	@commands.command(hidden = True)
	@commands.guild_only()
	@superuser()
	async def allow(self, ctx, command: str, role: discord.Role):
		if command not in self.commandsRoleRestricted:
			await ctx.send("I don't understand that command, please check your spelling. The options for this command are as follows: " + ', '.join(self.commandsRoleRestricted))
			return False
		
		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		guildID = ctx.guild.id
		print(role.name)
		print(role.id)
		roleID = role.name
		if not role.name:
			await self.ctx('I was unable to get the role id, \@everyone and \@here is currently unsupported')
			return False
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `allowed_roles` FROM `permissions` WHERE `guildID`=%s AND `command`=%s"
				cursor.execute(sql, (guildID, command))
				result = cursor.fetchone()
				if result is not None:
					allowed_roles = result['allowed_roles'].split(',')
					print(len(allowed_roles), allowed_roles)
					if role.name not in allowed_roles:
						allowed_roles.append(role.name)
					else:
						await ctx.send(role.name + ' has already been allowed to use the ' + command + ' command.')
						return False
					allowed_roles = ','.join(allowed_roles)
					sql = "UPDATE `permissions` SET `allowed_roles` = %s WHERE `guildID` = %s AND `command`=%s LIMIT 1"
					cursor.execute(sql, (allowed_roles, guildID, command))
					connection.commit()
				else:
					sql = "INSERT INTO `permissions` (`guildID`, `command`, `allowed_roles`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (guildID, command, role.name))
					connection.commit()
				await ctx.send(role.name + ' has been allowed to use the ' + command + ' command.')
		finally:
			connection.close()

	@commands.command(hidden = True)
	@commands.guild_only()
	@superuser()
	async def deny(self, ctx, command: str, role: discord.Role):
		if command not in self.commandsRoleRestricted:
			await ctx.send("I don't understand that command, please check your spelling. The options for this command are as follows: " + ', '.join(self.commandsRoleRestricted))
			return False
		
		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		guildID = ctx.guild.id
		print(role.name)
		print(role.id)
		if not role.name:
			await ctx.send('I was unable to get the role id, \@everyone and \@here is currently unsupported')
			return False
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `allowed_roles` FROM `permissions` WHERE `guildID`=%s AND `command`=%s"
				cursor.execute(sql, (guildID, command))
				result = cursor.fetchone()
				if result is not None:
					allowed_roles = result['allowed_roles'].split(',')
					if role.name in allowed_roles:
						allowed_roles.remove(role.name)
						allowed_roles = ','.join(allowed_roles)
						sql = "UPDATE `permissions` SET `allowed_roles` = %s WHERE `guildID` = %s AND `command`=%s LIMIT 1"
						cursor.execute(sql, (allowed_roles, guildID, command))
						connection.commit()
						await ctx.send(role.name + ' was removed form the list of allowed roles for ' + command + ' command.')
						return True
				await ctx.send(role.name + ' was not found in the allowed roles for ' + command + ' command.')
				return False
		finally:
			connection.close()

	@commands.command(hidden = True)
	@commands.guild_only()
	async def allowed(self, ctx, command: str=''):
		if command not in self.commandsRoleRestricted:
			await ctx.send("I don't understand that command, please check your spelling. The options for this command are as follows: " + ', '.join(self.commandsRoleRestricted))
			return False
		
		guildID = ctx.guild.id
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `allowed_roles` FROM `permissions` WHERE `guildID`=%s AND `command`=%s"
				cursor.execute(sql, (guildID, command))
				result = cursor.fetchone()
				if result is not None and result['allowed_roles'] is not '':
					await ctx.send('The following roles are allowed to use ' + command + ' command: ' + ', '.join(result['allowed_roles'].split(',')))
					return True
				await ctx.send('No roles have been allowed to use the ' + command + ' command on this guild.')
				return False
		finally:
			connection.close()

def setup(bot):
	bot.add_cog(Permissions(bot))