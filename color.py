import discord
from discord.ext import commands

CLASSCOLORS_FULL = {'death knight':'C41F3B', 'deathknight':'C41F3B', 'demon hunter':'A330C9', 'demonhunter':'A330C9', 'druid':'FF7D0A','hunter':'ABD473','mage':'69CCF0','monk':'00FF96','paladin':'F58CBA','priest':'FFFFFF','rogue':'FFF569','shaman':'0070DE','warlock':'9482C9','warrior':'C79C6E'}


#def doThumbs(func):
#	async def wrapper(*args, **kwargs):
#		retval = func(*args, **kwargs)
#		print(retval)
#		return retval
#	return wrapper

#async def doThumbs():
#	async def decorator_func(func):
#		async def wrapper_func(*args, **kwargs):
#			retval = func(*args, **kwargs)
#			print("Retval: ", retval)
#			return retval
#		return wrapper_func
#	return decorator_func

class RoleColor():
	def __init__(self, bot):
		self.bot = bot

	def valid_hex_color(hex):
		regex = re.compile("^[0-9a-fA-F]{6}$")
	

	@commands.command(pass_context=True)
	async def removecolor(self, ctx):
		if ctx.message.channel.is_private is True:
			print('Private ctx.message, ignoring !colorme command')
			await self.bot.send_message(ctx.message.channel, 'Sorry, I do not support the !removecolor command through direct ctx.message.  You\'ll have to repeat this command in a channel that I\'m in and properly configured for.')
			return False
		
		memberid = ctx.message.author.id
		if memberid is None:
			await self.bot.send_message(ctx.message.channel, 'I was unable to get your memberid, this is a bug')
			return False
		colorrole = "Color: " + memberid
		print(ctx.message.author.id)
		role = discord.utils.get(ctx.message.server.roles, name=colorrole)
		try:
			await self.bot.delete_role(ctx.message.server, role)
			await self.bot.add_reaction(ctx.message, "\U0001F44D") # ThumbsUp
		except:
			await self.bot.add_reaction(ctx.message, "\U0001F44E") # ThumbsDown

	@commands.command(pass_context=True)
	async def colorme(self, ctx, *, colorcode: str):
		if ctx.message.channel.is_private is True:
			print('Private ctx.message, ignoring !colorme command')
			await self.bot.send_message(ctx.message.channel, 'Sorry, I do not support the !colorme command through direct ctx.message.  You\'ll have to repeat this command in a channel that I\'m in and properly configured for.')
			return False
		newcolor = None
		print(colorcode)
		if colorcode.startswith('#'):
			colorcode = colorcode[1:]
		if colorcode in CLASSCOLORS_FULL:
			newcolor = discord.Color(int(CLASSCOLORS_FULL[colorcode], 16))
		elif self.valid_hex_color(colorcode):
			newcolor = discord.Color(int(colorcode, 16))

		if newcolor is None:
			return False
		
		memberid = ctx.message.author.id
		if memberid is None:
			await self.bot.send_message(ctx.message.channel, 'I was unable to get your memberid, this is a bug')
			return False
		colorrole = "Color: " + memberid
		print(ctx.message.author.id)
		role = discord.utils.get(ctx.message.server.roles, name=colorrole)
		botrole = discord.utils.get(ctx.message.server.roles, name="CaliBot") or discord.utils.get(message.server.roles, name="Calibot")
		if botrole is None:
			print('CaliBot role not found in channel')
			return False
		else:
			botrole = botrole.position
			print(botrole)
		if role:
			print("Changing color for", ctx.message.author.name, "with role", role, "to", newcolor)
			failed = False

			try:
				await self.bot.edit_role(ctx.message.server, role, name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
			except:
				failed = True
				print("Failed to edit role")
			try:
				await self.bot.add_roles(ctx.message.author, role)
			except:
				failed = True
				print("Failed to add role to member")
			try:
				await self.bot.move_role(ctx.message.server, role, botrole - 1)
			except:
				failed = True
				print("Failed to move role to higher location")
  
			if failed is True:
				await self.bot.send_message(ctx.message.channel, 'I haven\'t been properly configured for that command, I need to be assigned to the CaliBot Role with Manage Roles enabled and the role needs to be at the highest position. It\'s also possible that some other error has occured.')
				return False
			return True
		else:
			failed = False
			print("Creating color for role", colorrole, "to", newcolor)
			try:
				newrole = await self.bot.create_role(ctx.message.server, name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
			except:
				failed = True
			try:
				await self.bot.add_roles(ctx.message.author, newrole)
			except:
				failed = True
			try:
				await self.bot.move_role(ctx.message.server, newrole, botrole -1)
			except:
				failed = True
  
			if failed is True:
				await self.bot.send_message(ctx.message.channel, 'I haven\'t been properly configured for that command, I need to be assigned to the CaliBot Role with Manage Roles enabled and the role needs to be at the highest position. It\'s also possible that some other error occured.')
				return False
			return True

def setup(bot):
	bot.add_cog(RoleColor(bot))