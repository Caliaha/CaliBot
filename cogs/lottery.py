import aiomysql
import asyncio
import discord
from discord.ext import commands
import pymysql.cursors
import random
import secrets
import time
from stuff import BoxIt, checkPermissions, deleteMessage, doThumbs, sendBigMessage

class Lottery(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	async def loadSettings(self, guildID):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `ticketValue`, `winPercentage`, `guildCutPercentage`, `prizePool` FROM `lotterysettings` WHERE `guildID`=%s"
				cursor.execute(sql, (guildID))
				result = cursor.fetchone()
				if result is None:
					return None, None, None, None
				else:
					return result['ticketValue'], result['winPercentage'] / 100, result['guildCutPercentage'] / 100, result['prizePool']
		except Exception as e:
			print(e)
		finally:
			connection.close()
	
	@commands.command()
	async def lotteryhelp(self, ctx):
		"""Shows help for raffle related commands"""
		help = { }
		help['!lottery setup'] = 'Change lottery settings'
		help['!tickets [@member]'] = 'Lists amount of tickets member has'
		help['!ticketlist'] = 'Lists tickets of all members in database'
		help['!odds'] = 'Simulates 10,000 draws and show statistics'
		help['!draw'] = 'Picks winner from ticket holders'
		help['!giveticket @member [amount]'] = 'Gives one or amount of tickets to member, can be negative'
		help['!removetickets @member'] = 'Removes all tickets from member'
		help['!removealltickets'] = 'Removes all tickets from all members of guild'

		helpBox = BoxIt()
		helpBox.setTitle('Lottery Commands')
		for h in help:
			helpBox.addRow([ h, help[h] ])
		
		helpBox.setHeader([ 'Command', 'Description' ])
		await sendBigMessage(self, ctx, helpBox.box(), '```', '```')

	@commands.command()
	@checkPermissions('lottery')
	@commands.guild_only()
	@doThumbs()
	async def giveticket(self, ctx, member: discord.Member, value: int = 1):
		"""Gives a member a ticket"""
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				#Check if entry exists then update or create one
				sql = "SELECT `tickets` FROM `lottery` WHERE `discordID`=%s AND `guildID`=%s"
				cursor.execute(sql, (member.id, ctx.guild.id))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `lottery` (`guildID`, `discordID`, `tickets`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (ctx.guild.id, member.id, value))
					connection.commit()
				else:
					value = result['tickets'] + value
					sql = "UPDATE `lottery` SET `tickets` = %s WHERE `discordID` = %s AND `guildID`=%s LIMIT 1"
					cursor.execute(sql, (value, member.id, ctx.guild.id))
					connection.commit()
				await ctx.send("{} now has {} tickets".format(member.nick or member.name, value))
				return True
		finally:
			connection.close()

	@commands.command()
	@checkPermissions('lottery')
	@commands.guild_only()
	@doThumbs()
	async def removetickets(self, ctx, member: discord.Member):
		"""Removes tickets from members"""
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "DELETE FROM `lottery` WHERE `discordID`=%s AND `guildID`=%s LIMIT 1"
				cursor.execute(sql, (member.id, ctx.guild.id))
				connection.commit()

				await ctx.send("{} now has no tickets".format(member.nick or member.name))
				return True
		finally:
			connection.close()

	@commands.command()
	@checkPermissions('lottery')
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
					sql = "DELETE FROM `lottery` WHERE `guildID`=%s"
					cursor.execute(sql, (ctx.guild.id))
					connection.commit()

					await ctx.send("All lottery tickets for {} have been deleted".format(ctx.guild.name))
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
				sql = "SELECT `tickets` FROM `lottery` WHERE `discordID`=%s and `guildID`=%s"
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
	@checkPermissions('lottery')
	@commands.guild_only()
	@doThumbs()
	async def draw(self, ctx, *args):
		"""Selects a winner from ticket holders"""
		guarenteedWin = False
		for arg in args:
			arg = arg.lower()
			if arg == "-g":
				guarenteedWin = True

		winner, debug = await self.drawTicket(ctx.guild.id, guarenteedWin)

		if winner is False:
			if "ERROR" in debug and debug["ERROR"] == "NOTICKETS" or debug["ERROR"] == "NOTICKETHOLDERS":
				await ctx.send('There appear to be no ticket holders to draw from')
			else:
				await ctx.send('The lottery doesn\'t appear to have been properly setup.  Please use ***!lottery setup*** to initialize the default values.')
			return False

		msg = f'A total of {debug["totalTickets"]} tickets were sold, for a total of {debug["totalTickets"]*debug["ticketValue"]}g'
		msg = f'{msg}\nThe current jackpot is {debug["prizePool"] + debug["totalTickets"]*debug["ticketValue"]}g'
		msg = f'{msg}\nThe guilds take is {debug["guildCutPercentage"]*100}% of the jackpot'
		if debug['guarenteedWin']:
			msg = f'{msg}\nA winner is guarenteed'
		else:
			msg = f'{msg}\nNo one is guarenteed to win the jackpot'
		msg = f'{msg}\nA ticket with the number {debug["drawnTicketNumber"]} was drawn.'
			
		if winner is not None:
			try:
				member = ctx.guild.get_member(int(winner))
			except:
				member = winner
			msg = f'{msg}\n{member} has won with a matching ticket'
		else:
			msg = f'{msg}\nNo winner could be found for **{debug["drawnTicketNumber"]}**'
		if debug["guildCutPercentage"] > 0:
			msg = f'{msg}\nThe guild will receive {(debug["prizePool"] + debug["totalTickets"] * debug["ticketValue"]) * debug["guildCutPercentage"]}g'
		await ctx.send(f'{msg}')
		
		newPrizePool = debug["prizePool"] - ((debug["prizePool"] + debug["totalTickets"] * debug["ticketValue"]) * debug["guildCutPercentage"])
		print(f'{debug["prizePool"]} was reduced by {(debug["prizePool"] + debug["totalTickets"] * debug["ticketValue"]) * debug["guildCutPercentage"]} to {newPrizePool}')
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "UPDATE `lotterysettings` SET `prizePool` = %s WHERE `guildID`=%s LIMIT 1"
				cursor.execute(sql, (newPrizePool, ctx.guild.id))
				connection.commit()
				return True
		except Exception as e:
			print(e)
			return False
		finally:
			connection.close()

	async def drawTicket(self, guildID, guarenteedWin=False):
		ticketValue, winPercentage, guildCutPercentage, prizePool = await self.loadSettings(guildID)
		debug = { }
		debug['ticketValue'] = ticketValue
		debug['winPercentage'] = winPercentage
		debug['guildCutPercentage'] = guildCutPercentage
		debug['prizePool'] = prizePool
		debug['guarenteedWin'] = guarenteedWin
		debug['ticketsAssigned'] = { }
		if ticketValue == None or winPercentage == None or guildCutPercentage == None or prizePool == None:
			return False, debug
		try:
			connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
			async with connection.cursor() as cursor:
				sql = "SELECT SUM(`tickets`) total FROM `lottery` WHERE `guildID`=%s"
				await cursor.execute(sql, (guildID))
				result = await cursor.fetchone()
				if result['total'] == None:
					debug["ERROR"] = 'NOTICKETS'
					return False, debug
				totalTickets = int(result['total'])
				ticketPoolSize = int(round(totalTickets / winPercentage))
				debug['totalTickets'] = totalTickets
				debug['ticketPoolSize'] = ticketPoolSize
				if guarenteedWin:
					ticketPoolSize = totalTickets
				ticketPool = [ ]
				for j in range(ticketPoolSize):
					numberAdded = False
					while not numberAdded:
						randomTicketNumber = random.randint(100000,999999)
						if randomTicketNumber not in ticketPool:
							ticketPool.append(randomTicketNumber)
							numberAdded = True


				sql = "SELECT `discordID`, `tickets` FROM `lottery` WHERE `guildID`=%s"
				await cursor.execute(sql, (guildID))
				results = await cursor.fetchall()
				if not results:
					debug["ERROR"] = "NOTICKETHOLDERS"
					return False, debug
				#playerCount = cursor.rowcount

				ticketsDistributed = { }
				#secretRandom = secrets.SystemRandom()
				tempTicketPool = ticketPool.copy()
				for result in results:
					debug['ticketsAssigned'][result['discordID']] = int(result['tickets'])
					if int(result['tickets']) < 1:
						continue
					for j in range(int(result['tickets'])):
						ticketRand = secrets.choice(tempTicketPool)
						#ticketRand = random.choice(tempTicketPool)
						tempTicketPool.remove(ticketRand)
						ticketsDistributed[ticketRand] = result['discordID']
				debug['numTicketPoolActual'] = len(ticketPool)
				debug['numTicketsDistributed'] = len(ticketsDistributed)
				debug['ticketsDistributed'] = ticketsDistributed
				drawnTicket = secrets.choice(ticketPool)

				debug['drawnTicketNumber'] = drawnTicket
				if drawnTicket in ticketsDistributed:
					return ticketsDistributed[drawnTicket], debug # Our winner

				return None, debug
		except Exception as e:
			print(e)
			return False, {}
		finally:
			connection.close()

	@commands.command()
	@commands.guild_only()
	@doThumbs()
	async def odds(self, ctx, testIterations: int = 10000, *args):
		"""Calculate and show current odds"""
		#if testIterations > 10000000:
		#	await ctx.send("I'm just going to pretend I didn't see that.")
		#	return False
		#try:
#			async with ctx.channel.typing():
		guarenteedWin = False
		for arg in args:
			arg = arg.lower()
			if arg == "-g":
				guarenteedWin = True
		winners = { }
		winners["None"] = 0
		updateMessage = await ctx.send('This may take a bit')
		lastMessageUpdate = time.time()
		for i in range(1, testIterations + 1):
			winner, debug = await self.drawTicket(ctx.guild.id, guarenteedWin)

			if winner:
				if winner in winners:
					winners[winner] = winners[winner] + 1
				else:
					winners[winner] = 1
			elif winner is None:
				winners["None"] = winners["None"] + 1
			elif winner is False:
				if "ERROR" in debug and (debug["ERROR"] == "NOTICKETS" or debug["ERROR"] == "NOTICKETHOLDERS"):
					await ctx.send('There appear to be no ticket holders to draw from')
				else:
					await ctx.send('The lottery doesn\'t appear to have been properly setup.  Please use ***!lottery setup*** to initialize the default values.')
				await updateMessage.delete()
				return False

			box = BoxIt()
			box.setTitle(f'Odds over {testIterations} iterations')
			for winner in winners:
				box.addRow([ "NONE" if winner == "None" else ctx.guild.get_member(int(winner)), winners[winner], round((winners[winner] / i) * 100, 6), round((1 - debug['winPercentage']) * 100, 6) if winner == "None" else round((debug['ticketsAssigned'][winner] / debug['ticketPoolSize']) * 100, 6) ])
			box.sort(2, True)
			box.setHeader([ 'Name', 'Win Counts', 'Sampled', 'Calculated' ])

			if i % 1000 == 0 or i == testIterations:
				debugTicketHolders = { }
				for t in debug['ticketsDistributed']:
					holder = debug['ticketsDistributed'][t]
					if holder in debugTicketHolders:
						debugTicketHolders[holder] = debugTicketHolders[holder] + 1
					else:
						debugTicketHolders[holder] = 1
				msg = f'Debug information\nticketPool: {debug["numTicketPoolActual"]} ticketPoolSize: {debug["ticketPoolSize"]} winPercentage: {debug["winPercentage"]} ticketsDistributed: {debug["numTicketsDistributed"]}'
				debug_totalTicketsAssigned = 0
				for d in debugTicketHolders:
					debug_totalTicketsAssigned = debug_totalTicketsAssigned + debugTicketHolders[d]
					msg = f'{msg}\nTicket Owner: {"HOUSE" if d == "None" else ctx.guild.get_member(int(d))} Tickets Assigned: {debugTicketHolders[d]}'
				msg = f'{msg}\n{debug_totalTicketsAssigned} tickets assigned to players leaving {debug["numTicketPoolActual"]-debug_totalTicketsAssigned} non-winning tickets in play.'
				msg = f'{msg}\n{"True" if debug_totalTicketsAssigned / debug["numTicketPoolActual"] == debug["winPercentage"] else "False"}'
				print('Updating message', i)
				await updateMessage.edit(content=f'```Iteration {i} out of {testIterations}\n{box.box()}\n{msg}```')
				if (i == testIterations):
					print('LAST UPDATE')
		return True

	@commands.command()
	@commands.guild_only()
	@doThumbs()
	async def ticketlist(self, ctx):
		"""Shows all lottery ticket holders"""
		try:
			async with ctx.channel.typing():
				connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
				async with connection.cursor() as cursor:
					sql = "SELECT `discordID`, `tickets` FROM `lottery` WHERE `guildID`=%s"
					await cursor.execute(sql, (ctx.guild.id))
					results = await cursor.fetchall()

					box = BoxIt()
					box.setTitle('Lottery Ticket Holders')
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

	@commands.group(invoke_without_command=True)
	@checkPermissions('lottery')
	@doThumbs()
	async def lottery(self, ctx):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = sql = 'SELECT * FROM `lotterysettings` WHERE `guildID` = %s'
				cursor.execute(sql, (ctx.guild.id))
				
				
				result = cursor.fetchone()
				if result:
					await ctx.send(f'The lottery is current set to a {result["winPercentage"]}% win rate with a {result["guildCutPercentage"]}% guild cut and tickets are {result["ticketValue"]} gold each.')
				else:
					await ctx.send(f'No settings found, please use ***!lottery setup*** to initialize the settings')
				return True
		finally:
			connection.close()

	@lottery.command()
	@checkPermissions('lottery')
	@doThumbs()
	async def setup(self, ctx):
		ticketValue, winPercentage, guildCutPercentage, prizePool = await self.loadSettings(ctx.guild.id)
		if winPercentage:
			winPercentage = winPercentage * 100
		if guildCutPercentage:
			guildCutPercentage = guildCutPercentage * 100
		emojis = [ '💰', '🎰', '✂️', '🏆', '✔️', '❌' ]

		message = await ctx.send(f'The ticket value is currently set to {ticketValue}\nThe win percentage is {winPercentage}\nThe guild cut is {guildCutPercentage}\nThe prize pool is {prizePool}')
		editing = True
		needCommit = False
		while editing:
			for emoji in emojis:
				await message.add_reaction(emoji)

			def check(reaction, user):
					return user == ctx.author and str(reaction.emoji) in emojis

			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
			except asyncio.TimeoutError:
				editing = False
				needCommit = False
				await message.delete()
			except Exception as e:
				print(e)
			else:
				try:
					await reaction.remove(user)
					#await user.message.delete()
				except Exception as e:
					print(e)
				for emoji in emojis:
					try:
						await message.remove_reaction(emoji, self.bot.user)
					except:
						pass
				if reaction.emoji == '💰':
					def goldCheck(m):
						return m.author == ctx.author and m.channel == ctx.channel
					waiting = True
					while waiting:
						await message.edit(content=f'Please enter a new ticket value in gold. Whole numbers only, I don\'t believe in decimals or fractions')
						response = await self.bot.wait_for('message', timeout=60.0, check=goldCheck)
						if response.content == 'stop':
							waiting = False
						try:
							g = int(response.content)
							if g > 0:
								ticketValue = g
								needCommit = True
								waiting = False
						except:
							pass
						try:
							await response.delete()
						except Exception as e:
							print(e)
				if reaction.emoji == '🎰':
					def goldCheck(m):
						return m.author == ctx.author and m.channel == ctx.channel
					waiting = True
					while waiting:
						await message.edit(content=f'Please enter a new win percentage between 1 and 100 (inclusive). Whole numbers only, I don\'t believe in decimals or fractions. Also no zero, messes with my allergies.')
						response = await self.bot.wait_for('message', timeout=60.0, check=goldCheck)
						if response.content == 'stop':
							waiting = False
						try:
							g = int(response.content)
							if g > 0 and g <= 100:
								winPercentage = g
								needCommit = True
								waiting = False
						except:
							pass
						try:
							await response.delete()
						except Exception as e:
							print(e)
				if reaction.emoji == '✂️':
					def goldCheck(m):
						return m.author == ctx.author and m.channel == ctx.channel
					waiting = True
					while waiting:
						await message.edit(content=f'Please enter a new guild cut percentage between 0 and 100 (inclusive). Whole numbers only, I don\'t believe in decimals or fractions.')
						response = await self.bot.wait_for('message', timeout=60.0, check=goldCheck)
						if response.content == 'stop':
							waiting = False
						try:
							g = int(response.content)
							if g >= 0 and g <= 100:
								guildCutPercentage = g
								needCommit = True
								waiting = False
						except:
							pass
						try:
							await response.delete()
						except Exception as e:
							print(e)
				if reaction.emoji == '🏆':
					def goldCheck(m):
						return m.author == ctx.author and m.channel == ctx.channel
					waiting = True
					while waiting:
						await message.edit(content=f'Please enter a new prize pool between -2,147,483,648 and 2,147,483,647 (inclusive). No commas please or decimals.')
						response = await self.bot.wait_for('message', timeout=60.0, check=goldCheck)
						if response.content == 'stop':
							waiting = False
						try:
							g = int(response.content)
							if g >= -2147483648 and g <= 2147483648:
								prizePool = g
								needCommit = True
								waiting = False
						except:
							pass
						try:
							await response.delete()
						except Exception as e:
							print(e)
				if reaction.emoji == '✔️':
					editing = False
				if reaction.emoji == '❌':
					editing = False
					needCommit = False
					await message.delete()
 
				print(reaction.emoji)
				try:
					await message.edit(content=f'The ticket value is currently set to {ticketValue}\nThe win percentage is {winPercentage}\nThe guild cut is {guildCutPercentage}\nThe prize pool is {prizePool}')
				except:
					pass

		if needCommit:
			try:
				connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
				with connection.cursor() as cursor:
					#Check if entry exists then update or create one
					sql = "SELECT `ticketValue`, `winPercentage`, `guildCutPercentage`, `prizePool` FROM `lotterysettings` WHERE `guildID`=%s"
					cursor.execute(sql, (ctx.guild.id))
					result = cursor.fetchone()
					if ticketValue == None:
						ticketValue = 1
					if winPercentage == None:
						winPercentage = 10
					if guildCutPercentage == None:
						guildCutPercentage = 0
					if prizePool == None:
						prizePool = 0
					if result is None:
						sql = "INSERT INTO `lotterysettings` (`guildID`, `ticketValue`, `winPercentage`, `guildCutPercentage`, `prizePool`) VALUES(%s, %s, %s, %s, %s)"
						cursor.execute(sql, (ctx.guild.id, ticketValue, winPercentage, guildCutPercentage, prizePool))
						connection.commit()
					else:
						sql = "UPDATE `lotterysettings` SET `ticketValue` = %s, `winPercentage` = %s, `guildCutPercentage` = %s, `prizePool` = %s WHERE `guildID`=%s LIMIT 1"
						cursor.execute(sql, (ticketValue, winPercentage, guildCutPercentage, prizePool, ctx.guild.id))
						connection.commit()
					return True
			finally:
				connection.close()
		return True

def setup(bot):
	bot.add_cog(Lottery(bot))