import aiomysql
import asyncio
import discord
from discord.ext import commands
import pymysql.cursors
import random
import secrets
from stuff import BoxIt, checkPermissions, doThumbs, sendBigMessage

class Raffle():
	def __init__(self, bot):
		self.bot = bot
		
	@commands.command()
	async def rafflehelp(self, ctx):
		help = { }
		help['!tickets [@member]'] = 'Lists amount of tickets member has'
		help['!ticketlist'] = 'Lists tickets of all members in database'
		help['!drawtest'] = 'Simulates 10,000 draws and show statistics'
		help['!draw'] = 'Picks winner from ticket holders'
		help['!giveticket @member [amount]'] = 'Gives one or amount of tickets to member, can be negative'
		help['!removetickets @member'] = 'Removes all tickets from member'
		help['!removealltickets'] = 'Removes all tickets from all members of guild'

		helpBox = BoxIt()
		helpBox.setTitle('Raffle Commands')
		for h in help:
			helpBox.addRow([ h, help[h] ])
		
		helpBox.setHeader([ 'Command', 'Description' ])
		await sendBigMessage(self, ctx, helpBox.box())

	@commands.command()
	@checkPermissions('raffle')
	@commands.guild_only()
	@doThumbs()
	async def giveticket(self, ctx, member: discord.Member, value: int = 1):
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
		message = await ctx.send('This will remove all tickets from all members of this guild and can not be undone, react with 👌 to confirm.')

		def check(reaction, user):
			return user == ctx.author and str(reaction.emoji) == '👌'

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

				secretRandom = secrets.SystemRandom()
				winner = secretRandom.choice(weightedList)
				#secure_random = random.SystemRandom()
				#winner = secure_random.choice(weightedList)

				try:
					member = ctx.guild.get_member(int(winner))
				except:
					await ctx.send("Failed to get member name from discordID: {}".format(winner))

				await ctx.send("{} has won the drawing.".format(member.mention))
		finally:
			connection.close()
		return True

	@commands.command()
	@doThumbs()
	async def drawtest(self, ctx, threshold: int = 1):
		try:
			async with ctx.channel.typing():
				connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
				async with connection.cursor() as cursor:
					winners = { }
					tickets = { }
					testIterations = 10000
					for j in range(testIterations):
						sql = "SELECT `discordID`, `tickets` FROM `raffle` WHERE `guildID`=%s"
						await cursor.execute(sql, (ctx.guild.id))
						results = await cursor.fetchall()

						count = cursor.rowcount
						weightedList = [ ]
						for result in results:
							for i in range(int(result['tickets'])):
								if int(result['tickets']) >= threshold:
									tickets[result['discordID']] = result['tickets']
									weightedList.append(result['discordID'])

						secretRandom = secrets.SystemRandom()
						winner = secretRandom.choice(weightedList)
						#secure_random = random.SystemRandom()
						#winner = secure_random.choice(weightedList)

						if winner in winners:
							winners[winner] = winners[winner] + 1
						else:
							winners[winner] = 1
					
					box = BoxIt()
					box.setTitle('Drawing Test with {} iterations'.format(testIterations))
					for winner in winners:
						box.addRow([ ctx.guild.get_member(int(winner)), tickets[winner], winners[winner], round((winners[winner] / testIterations) * 100, 2) ])
					box.sort(2, True)
					box.setHeader([ 'Winner', 'Tickets', 'Win Counts', 'Win Percentage' ])
					await sendBigMessage(self, ctx, box.box())
		finally:
			connection.close()
		return True

	@commands.command()
	@doThumbs()
	async def ticketlist(self, ctx):
		try:
			async with ctx.channel.typing():
				connection = await aiomysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=aiomysql.cursors.DictCursor)
				async with connection.cursor() as cursor:
					sql = "SELECT `discordID`, `tickets` FROM `raffle` WHERE `guildID`=%s"
					await cursor.execute(sql, (ctx.guild.id))
					results = await cursor.fetchall()

					box = BoxIt()
					box.setTitle('Ticket Holders')
					for result in results:
						box.addRow([ ctx.guild.get_member(int(result['discordID'])), int(result['tickets']) ])

					box.sort(1, True)
					box.setHeader([ 'Ticket Holder', 'Tickets' ])
					await sendBigMessage(self, ctx, box.box())
		finally:
			connection.close()
		return True

def setup(bot):
	bot.add_cog(Raffle(bot))