import discord
from discord.ext import commands
import pymysql.cursors
from stuff import getRoleID, no_pm, superuser

class Permissions():
	def __init__(self, bot):
		self.bot = bot
		self.commands = [ 'color', 'wow' ]
		self.commandsRoleRestricted = [ 'color', 'set' ] # Fix this

	@commands.command(pass_context=True, hidden = True)
	@no_pm()
	@superuser()
	async def toggle(self, ctx, command: str):
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
					cursor.execute(sql, (disabled, serverID))
					connection.commit()
				else:
					sql = "INSERT INTO `permissions` (`serverID`, `command`, `disabled`) VALUES(%s, %s, %s)"
					disabled = 1
					cursor.execute(sql, (serverID, command, disabled))
					connection.commit()
				if disabled:
					await self.bot.send_message(ctx.message.channel, "Commands related to " + command + " have been disabled")
				else:
					await self.bot.send_message(ctx.message.channel, "Commands related to " + command + " have been enabled")
		finally:
			connection.close()
		
	@commands.command(pass_context=True, hidden = True)
	@no_pm()
	@superuser()
	async def allow(self, ctx, command: str, role: discord.Role):
		if command not in self.commandsRoleRestricted:
			await self.bot.send_message(ctx.message.channel, "I don't understand that command, please check your spelling.")
			return False
		
		connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		serverID = ctx.message.server.id
		print(role.name)
		print(role.id)
		roleID = role.name
		if not role.name:
			await self.bot.send_message(ctx.message.channel, 'I was unable to get the role id, \@everyone and \@here is currently unsupported')
			return False
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `allowed_roles` FROM `permissions` WHERE `serverID`=%s AND `command`=%s"
				cursor.execute(sql, (serverID, command))
				result = cursor.fetchone()
				if result is not None:
					allowed_roles = result['allowed_roles'].split()
					print(len(allowed_roles), allowed_roles)
					if role.name not in allowed_roles:
						allowed_roles.append(role.name)
					else:
						await self.bot.send_message(ctx.message.channel, role.name + ' has already been allowed to use the ' + command + ' command.')
						return False
					allowed_roles = ' '.join(allowed_roles)
					sql = "UPDATE `permissions` SET `allowed_roles` = %s WHERE `serverID` = %s AND `command`=%s LIMIT 1"
					cursor.execute(sql, (allowed_roles, serverID, command))
					connection.commit()
				else:
					sql = "INSERT INTO `permissions` (`serverID`, `command`, `allowed_roles`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (serverID, command, role.name))
					connection.commit()
				await self.bot.send_message(ctx.message.channel, role.name + ' has been allowed to use the ' + command + ' command.')
		finally:
			connection.close()

	@commands.command(pass_context=True, hidden = True)
	@no_pm()
	@superuser()
	async def deny(self, ctx, command: str, role: discord.Role):
		if command not in self.commandsRoleRestricted:
			await self.bot.send_message(ctx.message.channel, "I don't understand that command, please check your spelling.")
			return False
		
		connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		serverID = ctx.message.server.id
		print(role.name)
		print(role.id)
		if not role.name:
			await self.bot.send_message(ctx.message.channel, 'I was unable to get the role id, \@everyone and \@here is currently unsupported')
			return False
		try:
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `allowed_roles` FROM `permissions` WHERE `serverID`=%s AND `command`=%s"
				cursor.execute(sql, (serverID, command))
				result = cursor.fetchone()
				if result is not None:
					allowed_roles = result['allowed_roles'].split()
					if role.name in allowed_roles:
						allowed_roles.remove(role.name)
						allowed_roles = ' '.join(allowed_roles)
						sql = "UPDATE `permissions` SET `allowed_roles` = %s WHERE `serverID` = %s AND `command`=%s LIMIT 1"
						cursor.execute(sql, (allowed_roles, serverID, command))
						connection.commit()
						await self.bot.send_message(ctx.message.channel, role.name + ' was removed form the list of allowed roles for ' + command + ' command.')
						return True
				await self.bot.send_message(ctx.message.channel, role.name + ' was not found in the allowed roles for ' + command + ' command.')
				return False
		finally:
			connection.close()

	@commands.command(pass_context=True, hidden = True)
	@no_pm()
	async def allowed(self, ctx, command: str):
		if command not in self.commandsRoleRestricted:
			await self.bot.send_message(ctx.message.channel, "I don't understand that command, please check your spelling.")
			return False
		
		serverID = ctx.message.server.id
		try:
			connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `allowed_roles` FROM `permissions` WHERE `serverID`=%s AND `command`=%s"
				cursor.execute(sql, (serverID, command))
				result = cursor.fetchone()
				if result is not None and result['allowed_roles'] is not '':
					await self.bot.send_message(ctx.message.channel, 'The following roles are allowed to use ' + command + ' command: ' + result['allowed_roles'])
					return True
				await self.bot.send_message(ctx.message.channel, 'No roles have been allowed to use the ' + command + ' command on this server.')
				return False
		finally:
			connection.close()

def setup(bot):
	bot.add_cog(Permissions(bot))