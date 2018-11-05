import discord
from discord.ext import commands
import pymysql.cursors
import re
from stuff import checkPermission, checkPermissions, doThumbs, superuser

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

	async def bulk_remove(): # Later make this check and make sure that everyone who has a color role is still present in the guild
		pass

	async def on_ready(self):
		await self.bulk_remove()

	@commands.command()
	@commands.guild_only()
	@superuser()
	@doThumbs()
	async def removeallcolors(self, ctx, confirm=None):
		"""Removes all colors from everyone"""
		regex =re.compile("^Color: \d{18}$")
		rolesToDelete = []
		for role in ctx.guild.roles:
			if regex.match(role.name):
				rolesToDelete.append(role)
				print(role.name, 'is a color role')
		if confirm=='confirm':
			for role in rolesToDelete:
				try:
					await role.delete(reason='!removeallcolors requested by {}'.format(ctx.author.name))
				except:
					print("Failed to delete role")
		else:
			await ctx.send('The following will be deleted when this command is rerun as *!removeallcolors confirm*:\n' + ', '.join(role.name for role in rolesToDelete))
		return True

	@commands.command()
	@commands.guild_only()
	@doThumbs()
	@checkPermissions('color')
	async def removecolor(self, ctx, otherMember: discord.Member=None):
		"""Sets your color back to default"""
		if otherMember is not None:
			if await checkPermission(self, ctx, 'set') is True:
				member = otherMember
			else:
				await ctx.send("You don't have permission to use this command in this manner")
				return False
		else:
			member = ctx.message.author
		if member.id is None:
			await ctx.send('I was unable to get your memberid, this is a bug')
			return False
		colorrole = "Color: " + str(member.id)
		print('Deleting role for {} on behalf of {}.'.format(member.name, ctx.author.name))
		role = discord.utils.get(ctx.message.guild.roles, name=colorrole)
		try:
			await role.delete(reason='CaliBot !removecolor on behalf of {}'.format(ctx.author.name))
			return True
		except Exception as e:
			print(e)
			return False

	@commands.command()
	@commands.guild_only()
	@doThumbs()
	@checkPermissions('color')
	async def colorme(self, ctx, colorcode: str, otherMember: discord.Member=None):
		"""Changes your color in discord"""
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

		if otherMember is not None:
			if await checkPermission(self, ctx, 'set') is True:
				if otherMember == ctx.guild.me:
					await ctx.send('I cannot color myself')
					return False
				member = otherMember
				print('I am coloring {} on behalf of {}'.format(ctx.author.name, member.name))
			else:
				await ctx.send("You don't have permission to use this command in this manner")
				return False
		else:
			member = ctx.author
		if ctx.author.id is None:
			await ctx.send('I was unable to get your memberid, this is a bug')
			return False
		colorrole = "Color: " + str(member.id)
		print(member.id)
		role = discord.utils.get(ctx.message.guild.roles, name=colorrole)
		botrole = discord.utils.get(ctx.message.guild.roles, name=self.bot.NAME)
		if botrole is None:
			print('CaliBot role not found in guild')
			return False
		else:
			botrole = botrole.position
			print(botrole)
		failed = False
		if role:
			print("Changing color for", member.name, "with role", role, "to", newcolor)
			try:
				await role.edit(name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
			except:
				failed = True
				print("Failed to edit role")
		else:
			print("Creating color for role", colorrole, "to", newcolor)
			try:
				role = await ctx.guild.create_role(name = colorrole, permissions = discord.Permissions.none(), color = newcolor, hoist = False, mentionable = False)
			except Exception as e:
				print(e)
				failed = True

			
		try:
			await member.add_roles(role, reason = 'CaliBot !colorme', atomic=True)
		except:
			failed = True
			print("Failed to add role to member")
		try:
			await role.edit(position = botrole)
		except:
			print("Failed to move role to higher location")
  
		if failed is True:
			await ctx.send('I haven\'t been properly configured for that command, I need to be assigned to the CaliBot Role with Manage Roles enabled and the role needs to be at the highest position (or atleast higher than whoever wants to be colored). It\'s also possible that some other error has occured.')
			return False
		return True

def setup(bot):
	bot.add_cog(RoleColor(bot))