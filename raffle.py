import aiohttp
import asyncio
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import hashlib
import pymysql.cursors
import random
import re
from stuff import doThumbs, fetchWebpage
from urllib.parse import urlparse
import urllib.request

class Raffle():
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	@doThumbs()
	async def giveticket(self, ctx, value: int, member: discord.Member=None):
		if (member is None):
			await ctx.send("Usage: !giveticket AMOUNT @member")
			return False

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
	@doThumbs()
	async def draw(self, ctx):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `discordID`, `tickets` FROM `raffle` WHERE `guildID`=%s"
				cursor.execute(sql, (ctx.guild.id))
				results = cursor.fetchall()
				print(cursor.rowcount)
				count = cursor.rowcount
				weightedList = [ ]
				for result in results:
					for i in range(int(result['tickets'])):
						if int(result['tickets']) > 0:
							weightedList.append(result['discordID'])
				print(weightedList)
				if not weightedList:
					await ctx.send("There are no members to draw from")
					return False

				secure_random = random.SystemRandom()
				winner = secure_random.choice(weightedList)
				print(winner)
				
				member = ctx.guild.get_member(int(winner))

				await ctx.send("{} has won the drawing.".format(member.nick or member.name))
		finally:
			connection.close()
		return True

def setup(bot):
	bot.add_cog(Raffle(bot))