import aiomysql
import asyncio
import discord
from discord.ext import commands
import html
import math
import pymysql.cursors
import random
import re
import secrets
from stuff import BoxIt, checkPermissions, deleteMessage, doThumbs, fetchWebpage, sendBigMessage

class Raffle(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.logs = { }


		
	@commands.command()
	async def logclear(self, ctx):
		if ctx.guild.id in self.logs:
			del self.logs[ctx.guild.id]

	@commands.command()
	async def logstart(self, ctx):
		if ctx.guild.id not in self.logs:
			self.logs[ctx.guild.id] = { }

	@commands.command()
	async def loglist(self, ctx):
		if ctx.guild.id not in self.logs:
			return False
		box = BoxIt()
		box.setTitle('Raffle Log Results')
		totalDraws = 0
		for entry in self.logs[ctx.guild.id]:
			totalDraws = totalDraws + self.logs[ctx.guild.id][entry]
		for entry in self.logs[ctx.guild.id]:
			box.addRow([ ctx.guild.get_member(int(entry)), self.logs[ctx.guild.id][entry], round((self.logs[ctx.guild.id][entry] / totalDraws) * 100, 2) ])
		
		box.setHeader([ 'User', 'Win Counts', 'Win Percentage' ])
		await sendBigMessage(self, ctx, box.box(), '```', '```')
	
	@commands.command()
	async def rafflehelp(self, ctx):
		"""Shows help for raffle related commands"""
		help = { }
		help['!tickets [@member]'] = 'Lists amount of tickets member has'
		help['!ticketlist'] = 'Lists tickets of all members in database'
		help['!odds'] = 'Simulates 10,000 draws and show statistics'
		help['!draw'] = 'Picks winner from ticket holders'
		help['!giveticket @member [amount]'] = 'Gives one or amount of tickets to member, can be negative'
		help['!removetickets @member'] = 'Removes all tickets from member'
		help['!removealltickets'] = 'Removes all tickets from all members of guild'

		helpBox = BoxIt()
		helpBox.setTitle('Raffle Commands')
		for h in help:
			helpBox.addRow([ h, help[h] ])
		
		helpBox.setHeader([ 'Command', 'Description' ])
		await sendBigMessage(self, ctx, helpBox.box(), '```', '```')

	@commands.command()
	@checkPermissions('raffle')
	@commands.guild_only()
	@doThumbs()
	async def giveticket(self, ctx, member: discord.Member, value: int = 1):
		"""Gives a member a ticket"""
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `tickets` FROM `raffle` WHERE `discordID`=%s AND `guildID`=%s"
				cursor.execute(sql, (member.id, ctx.guild.id))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `raffle` (`guildID`, `discordID`, `tickets`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (ctx.guild.id, member.id, value))
					connection.commit()
				else:
					value = result['tickets'] + value
					sql = "UPDATE `raffle` SET `tickets` = %s WHERE `discordID` = %s AND `guildID`=%s LIMIT 1"
					cursor.execute(sql, (value, member.id, ctx.guild.id))
					connection.commit()
				await ctx.send("{} now has {} tickets".format(member.nick or member.name, value))
				return True
		finally:
			connection.close()

	@commands.command()
	@checkPermissions('raffle')
	@commands.guild_only()
	@doThumbs()
	async def removetickets(self, ctx, member: discord.Member):
		"""Removes tickets from members"""
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "DELETE FROM `raffle` WHERE `discordID`=%s AND `guildID`=%s LIMIT 1"
				cursor.execute(sql, (member.id, ctx.guild.id))
				connection.commit()

				await ctx.send("{} now has no tickets".format(member.nick or member.name))
				return True
		finally:
			connection.close()

	@commands.command()
	@checkPermissions('raffle')
	@commands.guild_only()
	@doThumbs()
	async def removealltickets(self, ctx):
		"""Removes all tickets"""
		message = await ctx.send('This will remove all tickets from all members of this guild and can not be undone, react with 👌 to confirm.')

		def check(reaction, user):
			okhand_emojies = [ '👌', '👌🏻', '👌🏽', '👌🏾', '👌🏿' ]
			return user == ctx.author and str(reaction.emoji) in okhand_emojies

		try:
			reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
		except asyncio.TimeoutError:
			await message.delete()
		else:
			try:
				connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
				with connection.cursor() as cursor:
					sql = "DELETE FROM `raffle` WHERE `guildID`=%s"
					cursor.execute(sql, (ctx.guild.id))
					connection.commit()

					await ctx.send("All tickets for {} have been deleted".format(ctx.guild.name))
					await message.delete()
					return True
			finally:
				connection.close()

	@commands.command()
	@doThumbs()
	async def tickets(self, ctx, member: discord.Member=None):
		"""Shows ticket count for member"""
		if (member is None):
			member = ctx.author

		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `tickets` FROM `raffle` WHERE `discordID`=%s and `guildID`=%s"
				cursor.execute(sql, (member.id, ctx.guild.id))
				result = cursor.fetchone()
				if result is None:
					await ctx.send("{} has zero tickets. Get donating scrub.".format(member.nick or member.name))
				else:
					await ctx.send("{} has {} tickets".format(member.nick or member.name, result['tickets']))
		finally:
			connection.close()
		return True

	@commands.command()
	@checkPermissions('raffle')
	@commands.guild_only()
	@doThumbs()
	async def draw(self, ctx, threshold: int = 1):
		"""Selects a winner from ticket holders"""
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `discordID`, `tickets` FROM `raffle` WHERE `guildID`=%s"
				cursor.execute(sql, (ctx.guild.id))
				results = cursor.fetchall()
				count = cursor.rowcount

				weightedList = [ ]
				for result in results:
					for i in range(int(result['tickets'])):
						if int(result['tickets']) >= threshold:
							weightedList.append(result['discordID'])

				if not weightedList:
					await ctx.send("There are no members to draw from")
					return False

				random.shuffle(weightedList)
				secretRandom = secrets.SystemRandom()
				winner = secretRandom.choice(weightedList)
				try:
					if ctx.guild.id in self.logs:
						if winner in self.logs[ctx.guild.id]:
							self.logs[ctx.guild.id][winner] = self.logs[ctx.guild.id][winner] + 1
						else:
							self.logs[ctx.guild.id][winner] = 1
				except:
					pass

				try:
					member = ctx.guild.get_member(int(winner))
				except:
					await ctx.send("Failed to get member name from discordID: {}".format(winner))

				await ctx.send("{} has won the drawing.".format(member.mention))
		finally:
			connection.close()
		return True

	@commands.command()
	@commands.guild_only()
	@doThumbs()
	async def odds(self, ctx, testIterations: int = 10000, threshold: int = 1):
		"""Calculate and show current odds"""
		if testIterations > 10000000:
			ctx.send("I'm just going to pretend I didn't see that.")
			return False
		try:
			async with ctx.channel.typing():
				connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
				async with connection.cursor() as cursor:
					winners = { }
					tickets = { }
					actualOdds = { }
					sql = "SELECT SUM(`tickets`) total FROM `raffle` WHERE `guildID`=%s"
					await cursor.execute(sql, (ctx.guild.id))
					result = await cursor.fetchone()
					totalTickets = int(result['total'])
					
					for j in range(testIterations):
						sql = "SELECT `discordID`, `tickets` FROM `raffle` WHERE `guildID`=%s"
						await cursor.execute(sql, (ctx.guild.id))
						results = await cursor.fetchall()

						count = cursor.rowcount
						weightedList = [ ]
						for result in results:
							if result['discordID'] not in actualOdds:
								actualOdds[result['discordID']] = round(int(result['tickets'])/totalTickets * 100, 2)
							for i in range(int(result['tickets'])):
								if int(result['tickets']) >= threshold:
									tickets[result['discordID']] = result['tickets']
									weightedList.append(result['discordID'])

						random.shuffle(weightedList)
						secretRandom = secrets.SystemRandom()
						winner = secretRandom.choice(weightedList)
						#secure_random = random.SystemRandom()
						#winner = secure_random.choice(weightedList)

						if winner in winners:
							winners[winner] = winners[winner] + 1
						else:
							winners[winner] = 1
					
					box = BoxIt()
					box.setTitle('Odds over {} iterations'.format(testIterations))
					for winner in winners:
						box.addRow([ ctx.guild.get_member(int(winner)), tickets[winner], winners[winner], round((winners[winner] / testIterations) * 100, 2), actualOdds[winner] ])
					box.sort(2, True)
					box.setHeader([ 'Name', 'Tickets', 'Win Counts', 'Sampled', 'Actual' ])
					await sendBigMessage(self, ctx, box.box(), '```', '```')
		finally:
			connection.close()
		return True

	@commands.command()
	@commands.guild_only()
	@doThumbs()
	async def ticketlist(self, ctx):
		"""Shows all ticket holders"""
		try:
			async with ctx.channel.typing():
				connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
				async with connection.cursor() as cursor:
					sql = "SELECT `discordID`, `tickets` FROM `raffle` WHERE `guildID`=%s"
					await cursor.execute(sql, (ctx.guild.id))
					results = await cursor.fetchall()

					box = BoxIt()
					box.setTitle('Ticket Holders')
					totalTickets = 0
					totalHolders = 0
					for result in results:
						totalHolders += 1
						totalTickets += int(result['tickets'])
						box.addRow([ ctx.guild.get_member(int(result['discordID'])), int(result['tickets']) ])

					box.sort(1, True)
					box.setHeader([ 'Name', 'Tickets' ])
					box.setFooter([ f'{totalHolders} entrees', f'{totalTickets} tickets' ])
					await sendBigMessage(self, ctx, box.box(), '```', '```')
		finally:
			connection.close()
		return True

	@commands.command(hidden=True)
	@commands.guild_only()
	@doThumbs()
	async def rafflelist(self, ctx):
		try:
			async with ctx.channel.typing():
				connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
				async with connection.cursor() as cursor:
					sql = "SELECT `itemName`, `tickets` FROM `raffleitems` WHERE `guildID`=%s ORDER BY `itemName` ASC"
					await cursor.execute(sql, (ctx.guild.id))
					results = await cursor.fetchall()

					box = BoxIt()
					box.setTitle('Raffle Items')
					for result in results:
						box.addRow([ result['itemName'], result['tickets'] ])

					box.setHeader([ 'Item', 'Trade-in Value' ])
					await sendBigMessage(self, ctx, box.box(), '```', '```')
		finally:
			connection.close()
		return True

	@commands.command(hidden=True)
	@checkPermissions('raffle')
	@commands.guild_only()
	@doThumbs()
	async def raffleadd(self, ctx, item, tickets):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `tickets` FROM `raffleitems` WHERE `guildID`=%s AND `itemName`=%s"
				cursor.execute(sql, (ctx.guild.id, item))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `raffleitems` (`guildID`, `itemName`, `tickets`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (ctx.guild.id, item, tickets))
					connection.commit()
				else:
					sql = "UPDATE `raffleitems` SET `tickets` = %s WHERE `guildID`=%s AND `itemName`=%s LIMIT 1"
					cursor.execute(sql, (tickets, ctx.guild.id, item))
					connection.commit()
				await ctx.send(f'{item} is worth {tickets}')
				return True
		finally:
			connection.close()

	@commands.command(hidden=True)
	@commands.guild_only()
	@deleteMessage()
	@doThumbs()
	async def raffleexport(self, ctx):
		data = '^1^T'
		try:
			connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
			async with connection.cursor() as cursor:
				sql = "SELECT `itemID`, `tickets` FROM `raffleitems` WHERE `guildID`=%s ORDER BY `itemName` ASC"
				await cursor.execute(sql, (ctx.guild.id))
				results = await cursor.fetchall()
				
				for result in results:
					data = f'{data}^N{result["itemID"]}^N{result["tickets"]}'
				data = f'{data}^t^^'
		except Exception as e:
			print('Failed to do db stuff', e)
		await ctx.send(f'`{data}`')
		return True

	@commands.command(hidden=True)
	@checkPermissions('raffle')
	@commands.guild_only()
	@deleteMessage()
	@doThumbs()
	async def raffleimport(self, ctx, *, data):
		itemDataPattern = re.compile('\^N(\d+)\^N(\d+\.?\d*)')
		itemNamePattern = re.compile('<meta property="twitter:title" content="(.*?)">')
		
		itemData = itemDataPattern.findall(data)
		if not itemData:
			await ctx.send('I was unable to process that data')
			return False

		async with ctx.channel.typing():
			dataToImport = [ ]
			box = BoxIt()
			box.setTitle('Trade-in Value')
			for item in itemData:
				itemPage = await fetchWebpage(self, f'https://www.wowhead.com/item={item[0]}')
				itemName = itemNamePattern.search(itemPage)
				itemName = html.unescape(itemName[1])
				
				dataToImport.append((item[0], item[1], itemName))
				box.addRow([ itemName, item[0], item[1] ])
			box.setHeader([ 'Item Name', 'Item ID', 'per Ticket' ])
			message = await ctx.send('```' + box.box() + '\nReact with 👌 to delete old data and replace with this new stuff```')

			def check(reaction, user):
				return user == ctx.author and str(reaction.emoji) == '👌'

			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
			except asyncio.TimeoutError:
				await message.delete()
			else:
				try:
					connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
					async with connection.cursor() as cursor:
						sql = "DELETE FROM `raffleitems` WHERE `guildID`=%s"
						await cursor.execute(sql, (ctx.guild.id))
						await connection.commit()
						for item in dataToImport:
							sql = "INSERT INTO `raffleitems` (`guildID`, `itemName`, `itemID`, `tickets`) VALUES(%s, %s, %s, %s)"
							await cursor.execute(sql, (ctx.guild.id, item[2], item[0], item[1]))
						await connection.commit()
						return True
				except Exception as e:
					await ctx.send(f'Error: {e}')
				finally:
					connection.close()

	@commands.command(hidden=True)
	@checkPermissions('raffle')
	@commands.guild_only()
	@deleteMessage()
	@doThumbs()
	async def raffleedit(self, ctx):
		updateMode = True
		help = 'Commands are:\nadd "item name" tickets\nedit id item|tickets\ndel id\nstop'
		editMessage = await ctx.send(help)
		def check(m):
			return m.author == ctx.author and m.channel == ctx.channel
		while(updateMode):
			try:
				async with ctx.channel.typing():
					connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
					async with connection.cursor() as cursor:
						sql = "SELECT `id`, `itemName`, `tickets` FROM `raffleitems` WHERE `guildID`=%s ORDER BY `itemName` ASC"
						await cursor.execute(sql, (ctx.guild.id))
						results = await cursor.fetchall()

						box = BoxIt()
						box.setTitle('Trade-in Value')
						for result in results:
							box.addRow([ int(result['id']), result['itemName'], result['tickets'] ])

						box.setHeader([ 'ID', 'Item', 'Tickets' ])
						await editMessage.edit(content=f'```{box.box()}\n{help}```')
						#await sendBigMessage(self, ctx, box.box())
			finally:
				connection.close()

			try:
				msg = await self.bot.wait_for('message', timeout=180.0, check=check)
				try:
					await msg.delete()
				except:
					pass
			except asyncio.TimeoutError:
				updateMode = False
				await ctx.send('No command receieved in 180 seconds, exiting edit mode.')
			else:
				if msg.content == 'stop':
					updateMode = False
				addRegex = re.compile('^add "(.*?)" (\d+)$')
				editRegex = re.compile('^edit (\d+) (.*?|\d+)$')
				deleteRegex = re.compile('^del (\d+)$')
				addCommand = addRegex.match(msg.content)
				editCommand = editRegex.match(msg.content)
				deleteCommand = deleteRegex.match(msg.content)

				if addCommand and addCommand[1] and addCommand[2]:
					try:
						connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
						async with connection.cursor() as cursor:
							sql = "INSERT INTO `raffleitems` (`guildID`, `itemName`, `tickets`) VALUES(%s, %s, %s)"
							await cursor.execute(sql, (ctx.guild.id, addCommand[1], addCommand[2]))
							await connection.commit()
					except Exception as e:
						print(e)
					finally:
						connection.close()

				if editCommand and editCommand[1] and editCommand[2]:
						try:
							tickets = int(editCommand[2])
							sql = "UPDATE `raffleitems` SET `tickets`=%s WHERE `guildID`=%s and `id`=%s LIMIT 1"
						except:
							sql = "UPDATE `raffleitems` SET `itemName`=%s WHERE `guildID`=%s and `id`=%s LIMIT 1"
						try:
							connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
							async with connection.cursor() as cursor:
								await cursor.execute(sql, (editCommand[2], ctx.guild.id, editCommand[1]))
								await connection.commit()
						except Exception as e:
							print(e)
						finally:
							connection.close()

				if deleteCommand and deleteCommand[1]:
					try:
						connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
						async with connection.cursor() as cursor:
							sql = "DELETE FROM `raffleitems` WHERE `guildID`=%s and `id`=%s LIMIT 1"
							await cursor.execute(sql, (ctx.guild.id, deleteCommand[1]))
							await connection.commit()
					except Exception as e:
						print(e)
						await ctx.send('Error Updating Database')			
					finally:
						connection.close()
		
		try:
			await editMessage.delete()
		except:
			pass
		return True

def setup(bot):
	bot.add_cog(Raffle(bot))