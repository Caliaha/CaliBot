from dateutil.relativedelta import relativedelta
import discord
from discord.ext import commands
from io import BytesIO
import os
#from pdf2image import convert_from_path, convert_from_bytes
#import pdfkit
import pymysql.cursors
import secrets
from stuff import checkPermissions, cleanUserInput, deleteMessage, doThumbs, isBotOwner, superuser, getSnowflake, getChannel
import sys
import time
import uptime

class utils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def guildlist(self, ctx):
		"""Shows guilds that I am active in"""
		for guild in self.bot.guilds:
			try:
				message += ', ' + guild.name
			except:
				message = 'I am in the following guilds: ' + guild.name
		
		if (not message):
			message = 'I am not in any guilds'
		
		await ctx.send(message)

	@commands.command(hidden=True)
	@doThumbs()
	async def avatar(self, ctx, member: discord.Member = None):
		if not member:
			member = ctx.author
		
		try:
			await ctx.send(f'{member.avatar_url}')
			return True
		except:
			await ctx.send('Failed to get avatar url')
			return False

	@commands.command(hidden=True)
	@isBotOwner()
	@commands.guild_only()
	@doThumbs()
	async def guildowner(self, ctx):
		"""Shows guild owner"""
		await ctx.send(ctx.message.guild.owner)
		return True

	@commands.command(hidden=True)
	@commands.has_permissions(manage_guild=True)
	@commands.guild_only()
	@doThumbs()
	async def hop(self, ctx, region: str = None):
		"""Changes guild region"""
		regions = [ 'japan', 'singapore', 'eu-central', 'india', 'us-central', 'london', 'eu-west', 'amsterdam', 'brazil', 'us-west', 'hongkong', 'us-south', 'southafrica', 'us-east', 'sydney', 'frankfurt', 'russia' ]
		prefRegions = [ 'us-south', 'us-east' ]
		if region is not None and region not in regions:
			await ctx.send(f'Not a valid region!\nValid regions are: {", ".join(regions)}')
			return False
		
		if region is None:
			currentRegion = ctx.guild.region
			try:
				prefRegions.remove(str(currentRegion))
			except:
				print(f'{currentRegion} not in preferred regions')
			region = secrets.choice(prefRegions)
		
		try:
			await ctx.guild.edit(region=region)
		except Exception as e:
			await ctx.send(f'Could not change regions: {e}')
			return False
		await ctx.send(f'Setting guild region to {region}')
		return True

	@commands.command()
	@checkPermissions('utils')
	async def restart(self, ctx):
		"""Restarts CaliBot"""
		await ctx.message.channel.send('I am restarting. It will take me a moment to reconnect')
		print('Restarting script')
		#await self.bot.close() -- No point in doing it politely
		os._exit(0)

	@commands.command()
	@doThumbs()
	async def uptime(self, ctx):
		"""Uptime of bot and it's computer"""
		await ctx.send(self.bot.NAME + ' Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=time.time() - self.bot.startTime)))
		await ctx.send('Computer Uptime: ' + '{0.days:01.0f} days {0.hours:01.0f} hours {0.minutes:01.0f} minutes {0.seconds:01.0f} seconds'.format(relativedelta(seconds=uptime.uptime())))
		return True

#	def convertwebpagetopdf(self, url):
#		images = [ ]
#		pdf = pdfkit.from_url(url, False)
#		pages = convert_from_bytes(pdf)
#		for page in pages:
#			with BytesIO() as output:
#				page.save(output, format='png')
#				images.append(output.getvalue())
#		
#		return images

#	@commands.command(hidden=True)
#	@doThumbs()
#	async def renderpage(self, ctx, url: str):
#		images = await self.bot.loop.run_in_executor(None, self.convertwebpagetopdf, url)
#		for image in images:
#			await ctx.send(file=discord.File(image, 'file.png'))

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def load(self, ctx, extension_name : str):
		"""Loads an extension."""
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return False
		await ctx.send("{} loaded.".format(extension_name))
		return True

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def unload(self, ctx, extension_name : str):
		"""Unloads an extension."""
		self.bot.unload_extension(extension_name)
		await ctx.send("{} unloaded.".format(extension_name))
		return True

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def reload(self, ctx, extension_name : str):
		"""Unloads and then loads an extension."""
		self.bot.unload_extension(extension_name)
		try:
			self.bot.load_extension(extension_name)
		except (AttributeError, ImportError) as e:
			await ctx.send("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
			return False
		await ctx.send("{} has been reloaded.".format(extension_name))
		return True

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def dma(self, ctx, messageID: int, channelID = None, guildID = None):
		try:
			if (guildID):
				guild = self.bot.get_guild(int(guildID))
				print(guild.name)
			else:
				guild = ctx.guild
			if (channelID):
				channel = guild.get_channel(int(channelID))
				print(channel.name)
			else:
				channel = ctx.channel
			print('Getting message for {} in {}'.format(channel.name, guild.name))
			message = await channel.get_message(messageID)
			await message.delete()
			return True
		except:
			return False

	@commands.command(hidden=True)
	@isBotOwner()
	@doThumbs()
	async def eval(self, ctx, *, code : str):
		try:
			await ctx.send(eval(code))
		except Exception as e:
			await ctx.send(e)
			return False
		return True

	@commands.command()
	@isBotOwner()
	@doThumbs()
	async def denyall(self, ctx, *args):
		"""See no evil, Hear no evil, Smell no evil"""
		validArguments = { '-u': 'user', '-r': 'role' }
		arguments = { }
		
		if len(args) >= 1 and (args[0] == 'help' or args[0] == '-h'):
			await ctx.send('Usage: **!denyall -r ROLE** or **!denyall -u @USER**\nCapitilization must be correct')
			return True
		
		thing = None
		for i in range(len(args)):
			if args[i] in validArguments:
				if i+1 <= len(args):
					arguments[validArguments[args[i]]] = args[i+1]
				else:
					arguments[validArguments[args[i]]] = True
		print(arguments)
		if 'user' in arguments:
			try:
				thing = ctx.guild.get_member_named(arguments['user'])
			except Exception as e:
				print(e)

		if 'role' in arguments:
			if arguments['role'] == '@everyone':
				await ctx.send('That\'s going to be a no from me, dawg.')
				return False
			try:
				for role in ctx.guild.roles:
					if role.name == arguments['role']:
						thing = role
						print(role.name, role.id)
						break
			except Exception as e:
				print(e)
		
		if not thing:
			await ctx.send('No valid users or roles passed, spelling and capitalization must be exact.', delete_after=30)
			return False
		
		for channel in ctx.guild.channels:
			print(channel)
			try:
				await channel.set_permissions(thing,
					create_instant_invite=False,
					manage_channels=False,
					manage_roles=False, #manage permissions
					manage_webhooks=False,
					read_messages=False,
					send_messages=False,
					send_tts_messages=False,
					manage_messages=False,
					embed_links=False,
					attach_files=False,
					read_message_history=False,
					mention_everyone=False,
					external_emojis=False,
					add_reactions=False,
					connect=False,
					speak=False,
					mute_members=False,
					deafen_members=False,
					move_members=False,
					use_voice_activation=False,
					priority_speaker=False,
					stream=False, #go live
					)
			except discord.Forbidden:
				await ctx.send('I don\'t have permission to do that.', delete_after=30)
				return False
			except:
				await ctx.send('Something went wrong.', delete_after=30)
				return False
		return True
	
	@commands.command()
	@isBotOwner()
	@doThumbs()
	async def denynone(self, ctx, *args):
		"""Removes channel overwrites"""
		validArguments = { '-u': 'user', '-r': 'role', '-c': 'channel' }
		arguments = { }
		
		if len(args) >= 1 and (args[0] == 'help' or args[0] == '-h'):
			await ctx.send('Usage: **!denynone -r ROLE** or **!denynone -u USER**\nCan also limit to a channel with **-c CHANNEL**\nCapitilization must be correct')
			return True
		
		thing = None
		ch = None
		for i in range(len(args)):
			if args[i] in validArguments:
				if i+1 <= len(args):
					arguments[validArguments[args[i]]] = args[i+1]
					print(type(args[i+1]), getSnowflake(args[i+1]))
				else:
					arguments[validArguments[args[i]]] = True
		print(arguments)
		if 'channel' in arguments:
			try:
				sf = getChannel(arguments['channel'])
				if sf:
					print(sf)
					ch = ctx.guild.get_channel(int(sf[1]))
					if not ch:
						raise
				else:
					for channel in ctx.guild.channels:
						if channel.name == arguments['channel']:
							print(channel.name)
							ch = channel
			except:
				await ctx.send('Unable to find that channel', delete_after=30)
				return False
		if 'user' in arguments:
			try:
				sf = getSnowflake(arguments['user'])
				if sf:
					thing = ctx.guild.get_member(sf)
				else:
					thing = ctx.guild.get_member_named(arguments['user'])
			except Exception as e:
				print(e)

		if 'role' in arguments:
			if arguments['role'] == '@everyone':
				await ctx.send('That\'s going to be a no from me, dawg.')
				return False
			try:
				for role in ctx.guild.roles:
					if role.name == arguments['role']:
						thing = role
						print(role.name, role.id)
						break
			except Exception as e:
				print(e)
		if not thing:
			await ctx.send('No valid users or roles passed, spelling and capitalization must be exact.', delete_after=30)
			return False
		if ch:
			try:
				await ch.set_permissions(thing, overwrite=None)
			except discord.Forbidden:
				await ctx.send('I don\'t have permission to do that.', delete_after=30)
				return False
			except:
				await ctx.send('Something went wrong.', delete_after=30)
				return False
		else:
			for channel in ctx.guild.channels:
				print(channel)
				try:
					await channel.set_permissions(thing, overwrite=None)
				except discord.Forbidden:
					await ctx.send('I don\'t have permission to do that.', delete_after=30)
					return False
				except:
					await ctx.send('Something went wrong.', delete_after=30)
					return False
		return True

	@commands.command(hidden=True)
	@superuser()
	@commands.guild_only()
	async def purgeUser(self, ctx, user: discord.Member):
		counter = 0
		async for message in ctx.channel.history(limit=None):
			if message.author.id == user.id:
				counter = counter + 1
				await message.delete()
		await ctx.send(f'Deleted {counter} messages')

	@commands.command(hidden=True)
	@superuser()
	@commands.guild_only()
	async def purgeAll(self, ctx):
		# TODO Ask for confirmation
		counter = 0
		async for message in ctx.channel.history(limit=None):
			counter = counter + 1
			await message.delete()
		await ctx.send(f'Deleted {counter} messages')
		

	@commands.command(hidden=True)
	@superuser()
	@commands.guild_only()
	async def purge(self, ctx, amount: int = 10):
		while(amount > 0):
			if amount > 100:
				toDelete = 100
				amount = amount - 100
			else:
				toDelete = amount
				amount = 0

			await ctx.channel.delete_messages(await ctx.channel.history(limit=toDelete).flatten())

	@commands.command(hidden=True)
	@superuser()
	@commands.guild_only()
	async def reactions(self, ctx, channelID: int, messageID: int, guildID: int = 0):
		if guildID:
			guild = self.bot.get_guild(guildID)
		else:
			guild = ctx.guild
		
		channel = guild.get_channel(channelID)
		message = await channel.fetch_message(messageID)
		data = ''
		for reaction in message.reactions:
			users = await reaction.users().flatten()
			for user in users:
				data = f'{data}{reaction}:{user.name}#{user.discriminator}\n'
		await ctx.send(data)
		

	@commands.command()
	@deleteMessage()
	@commands.guild_only()
	async def dm(self, ctx):
		"""Bot will delete successful command messages"""
		connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
		try:
			with connection.cursor() as cursor:
				sql = "SELECT `deleteMessage` FROM `guild_defaults` WHERE `guildID`=%s"
				cursor.execute(sql, (ctx.guild.id))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `guild_defaults` (`guildID`, `deleteMessage`) VALUES(%s, %s)" # FIX ME, Create this when guild is joined instead of everytime we attempt an access
					cursor.execute(sql, (ctx.guild.id, True))
					connection.commit()
				else:
					dm = result['deleteMessage']
					if dm:
						await ctx.send('I will no longer delete invoking commands')
						dm = False
					else:
						dm = True
						await ctx.send('I will delete invoking commands that are successful, probably.')
					sql = "UPDATE `guild_defaults` SET `deleteMessage` = %s WHERE `guildID` = %s LIMIT 1"
					cursor.execute(sql, (dm, ctx.guild.id))
					connection.commit()
		finally:
			connection.close()

	@commands.command(hidden=True)
	async def text2number(self, ctx, *, text):
		"""Makes text hard to read"""
		table = str.maketrans('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', '⓪①②③④⑤⑥⑦⑧⑨ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ')
		await ctx.send(text.translate(table))

	@commands.command(hidden=True)
	@doThumbs()
	async def cogs(self, ctx):
		cogs = []
		for filename in os.listdir(f'./{self.bot.COG_DIRECTORY}'):
			if not os.path.isfile(f'./{self.bot.COG_DIRECTORY}/{filename}'):
				continue
			(file, ext) = os.path.splitext(filename)
			if not ext == '.py':
				continue
			cogs.append(file)
		await ctx.send(f'Enabled cogs: {", ".join(name for name in cogs)}')
		return True
	
	@commands.command(hidden=True)
	@doThumbs()
	async def enablecog(self, ctx, *, name):
		name = cleanUserInput(name)
		if os.path.isfile(f'./{self.bot.COG_DIRECTORY}/{name}.py'):
			await ctx.send('That cog already seems to be enabled.')
			return False
		try:
			os.rename(f'./{self.bot.COG_DIRECTORY_DISABLED}/{name}.py', f'./{self.bot.COG_DIRECTORY}/{name}.py')
		except Exception as e:
			await ctx.send(e)
		return True

	@commands.command(hidden=True)
	@doThumbs()
	async def disablecog(self, ctx, *, name):
		name = cleanUserInput(name)
		if os.path.isfile(f'./{self.bot.COG_DIRECTORY_DISABLED}/{name}.py'):
			await ctx.send('That cog already seems to be disabled.')
			return False
		try:
			os.rename(f'./{self.bot.COG_DIRECTORY}/{name}.py', f'./{self.bot.COG_DIRECTORY_DISABLED}/{name}.py')
		except Exception as e:
			await ctx.send(e)
		return True

def setup(bot):
	bot.add_cog(utils(bot))