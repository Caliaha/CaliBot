import discord
from discord.ext import commands
import pymysql.cursors
import re
from stuff import checkPermissions, doThumbs

'''
Add these at some point to remove color role when a person leaves the guild
discord.on_member_join(member)
discord.on_member_remove(member)
'''

CLASSCOLORS_FULL = {'death knight':'C41F3B', 'deathknight':'C41F3B', 'demon hunter':'A330C9', 'demonhunter':'A330C9', 'druid':'FF7D0A','hunter':'ABD473','mage':'69CCF0','monk':'00FF96','paladin':'F58CBA','priest':'FFFFFF','rogue':'FFF569','shaman':'0070DE','warlock':'9482C9','warrior':'C79C6E'}

class RoleColor():
	def __init__(self, bot):
		self.bot = bot

	def valid_hex_color(self, hex):
		regex = re.compile("^[0-9a-fA-F]{6}$")
		return True if regex.match(hex) is not None else False

	@commands.command(pass_context=True)
	@commands.guild_only()
	@doThumbs()
	@checkPermissions('color')
	async def removecolor(self, ctx):
		memberid = ctx.message.author.id
		if memberid is None:
			await ctx.send('I was unable to get your memberid, this is a bug')
			return False
		colorrole = "Color: " + str(memberid)
		print(ctx.message.author.id)
		role = discord.utils.get(ctx.message.guild.roles, name=colorrole)
		try:
			await role.delete(reason='CaliBot !removecolor')
			return True
		except Exception as e:
			print(e)
			return False

	@commands.command(pass_context=True)
	@commands.guild_only()
	@doThumbs()
	@checkPermissions('color')
	async def colorme(self, ctx, *, colorcode: str):
		newcolor = None
		colorcode = colorcode.lower()
		print(colorcode)
		if colorcode.startswith('#'):
			colorcode = colorcode[1:]
		if colorcode in CLASSCOLORS_FULL:
			newcolor = discord.Color(int(CLASSCOLORS_FULL[colorcode], 16))
		elif self.valid_hex_color(colorcode):
			newcolor = discord.Color(int(colorcode, 16))
			print(colorcode, newcolor)

		if newcolor is None:
			return False
		
		memberid = ctx.message.author.id
		if memberid is None:
			await ctx.send('I was unable to get your memberid, this is a bug')
			return False
		colorrole = "Color: " + str(memberid)
		print(ctx.message.author.id)
		role = discord.utils.get(ctx.message.guild.roles, name=colorrole)
		botrole = discord.utils.get(ctx.message.guild.roles, name=self.bot.NAME)
		if botrole is None:
			print('CaliBot role not found in channel')
			return False
		else:
			botrole = botrole.position
			print(botrole)
		failed = False
		if role:
			print("Changing color for", ctx.message.author.name, "with role", role, "to", newcolor)
			try:
				#await self.bot.edit_role(ctx.message.server, role, name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
				await role.edit(name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
			except:
				failed = True
				print("Failed to edit role")
		else:
			print("Creating color for role", colorrole, "to", newcolor)
			try:
				#role = await self.bot.create_role(ctx.message.server, name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
				role = await ctx.guild.create_role(name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
			except Exception as e:
				print(e)
				failed = True

			
		try:
			#await self.bot.add_roles(ctx.message.author, role)
			await ctx.message.author.add_roles(role, reason = 'CaliBot !colorme', atomic=True)
		except:
			failed = True
			print("Failed to add role to member")
		try:
			#await self.bot.move_role(ctx.message.server, role, botrole)
			await role.edit(position = botrole)
		except:
			print("Failed to move role to higher location")
  
		if failed is True:
			await ctx.send('I haven\'t been properly configured for that command, I need to be assigned to the CaliBot Role with Manage Roles enabled and the role needs to be at the highest position (or atleast higher than whoever wants to be colored). It\'s also possible that some other error has occured.')
			return False
		return True

def setup(bot):
	bot.add_cog(RoleColor(bot))