import discord
from discord.ext import commands
from stuff import doThumbs, superuser, no_pm

class ServerManagement():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	@doThumbs()
	@no_pm()
	@superuser()
	async def banid(self, ctx, user_id : str):
		"""Ban member from guild by their id"""
		member = discord.Object(id=user_id)
		member.server = discord.Object(id=ctx.message.server.id)
		print(ctx.message.server.id, member.id, member.server)
		try:
			await self.bot.ban(member, delete_message_days=7)
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
	@no_pm()
	@superuser()
	async def unbanid(self, ctx, user_id : str):
		"""Unban member from guild by their id"""
		member = discord.Object(id=user_id)
		member.server = discord.Object(id=ctx.message.server.id)
		print(member.id, member.server)
		try:
			await self.bot.unban(member.server, member)
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