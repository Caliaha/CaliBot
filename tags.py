import discord
from discord.ext import tasks, commands
import pymysql.cursors
from stuff import doThumbs

class Tag(commands.Cog):
	"""TBD"""
	def __init__(self, bot):
		self.bot = bot

	@commands.group(invoke_without_command=True)
	@doThumbs()
	async def tag(self, ctx, *, name: str):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `text` FROM `tags` WHERE `name` = %s"
				cursor.execute(sql, (name))
				result = cursor.fetchone()
				if result is None:
					sql = "SELECT `name` FROM `tags` WHERE LOWER(`name`) LIKE %s"
					cursor.execute(sql, (f'%{name}%'))
					results = cursor.fetchall()
					if results:
						print(results)
						await ctx.send(f"Tag not found, did you mean {', '.join(result['name'] for result in results)}?")
						
						return False
					else:
						await ctx.send(f'No tag found for {name}')
						
				else:
					await ctx.send(result['text'])
					return True
		except Exception as e:
			print(e)

	@tag.command()
	@doThumbs()
	async def create(self, ctx, name: str, *, text: str):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "SELECT `name`, `owner` FROM `tags` WHERE `name` = %s"
				cursor.execute(sql, (name))
				result = cursor.fetchone()
				if result is None:
					sql = "INSERT INTO `tags` (`name`, `text`, `owner`) VALUES(%s, %s, %s)"
					cursor.execute(sql, (name, text, ctx.author.id))
					connection.commit()
					return True
				else:
					await ctx.send(f'{name} already exists and is owned by {result["owner"]}')
					return False
		except Exception as e:
			print(e)

	@tag.command()
	@doThumbs()
	async def edit(self, ctx, name: str, *, text: str):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "UPDATE `tags` SET `text` = %s WHERE LOWER(`name`) = %s AND `owner` = %s"
				cursor.execute(sql, (text, name.lower(), str(ctx.author.id)))
				connection.commit()
				if cursor.rowcount == 0:
					await ctx.send("Failed to update tag, it doesn't exist or you don't own it.")
					return False
				else:
					return True
		except Exception as e:
			print(e)

	@tag.command()
	@doThumbs()
	async def delete(self, ctx, name: str):
		try:
			connection = pymysql.connect(host=self.bot.MYSQL_HOST, user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			with connection.cursor() as cursor:
				sql = "DELETE FROM `tags` WHERE LOWER(`name`) = %s AND `owner` = %s LIMIT 1" 
				cursor.execute(sql, (name.lower(), str(ctx.author.id)))
				connection.commit()
				if cursor.rowcount == 0:
					await ctx.send("Failed to delete tag, it doesn't exist or you don't own it.")
					return False
				else:
					return True
		except Exception as e:
			print(e)

def setup(bot):
	bot.add_cog(Tag(bot))