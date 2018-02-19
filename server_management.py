import discord
from discord.ext import commands
from stuff import doThumbs, superuser

class ServerManagement():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	@doThumbs()
	@commands.guild_only()
	@superuser()
	async def banid(self, ctx, user_id : str):
		"""Ban member from guild by their id"""
		member = discord.Object(id=user_id)
		print(ctx.message.guild.id, member.id)
		try:
			await ctx.guild.ban(member, reason='Banhammer on behalf of ' + ctx.author.name, delete_message_days=7)
		except discord.HTTPException as e:
			print(e)
		except discord.Forbidden as e:
			print(e)
		except Exception as e:
			print(e)
		else:
			return True
		return False

	@commands.command(pass_context=True)
	@doThumbs()
	@commands.guild_only()
	@superuser()
	async def unbanid(self, ctx, user_id : str):
		"""Unban member from guild by their id"""
		member = discord.Object(id=user_id)
		print(member.id)
		try:
			await ctx.guild.unban(member, reason='Unbanhammer on behalf of ' + ctx.author.name)
		except discord.HTTPException as e:
			print(e)
		except discord.Forbidden as e:
			print(e)
		except Exception as e:
			print(e)
		else:
			return True
		return False

def setup(bot):
	bot.add_cog(ServerManagement(bot))