import discord
from discord.ext import commands
import json
import urllib.request
from stuff import BoxIt

class WynnCraft():
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def wynncraft(self, ctx, character):
		with open('wynncraft.json') as json_data:
			data = json.load(json_data)

		print(data['username'], data['global']['total_level'], data['global']['mobs_killed'], data['global']['chests_found'], data['global']['deaths'])
		embed=discord.Embed(title='Wynncraft', color=discord.Color(int(self.bot.DEFAULT_EMBED_COLOR, 16)))
		box=BoxIt()
		for char in data['classes']:
			print(char)
			print(data['classes'][char]['level'], data['classes'][char]['questsAmount'], data['classes'][char]['skills']['Dexterity'])
			print("Intelligence -> " + str(data['classes'][char]['skills']['Intelligence']) + "\n" + "Dexterity -> " + str(data['classes'][char]['skills']['Dexterity']) + "\n" + "Strength -> " + str(data['classes'][char]['skills']['Strength']) + "\n" + "Defense -> " + str(data['classes'][char]['skills']['Defense']) + "\n" + "Agility -> " + str(data['classes'][char]['skills']['Agility']) + "\n")
			embed.add_field(name=char.capitalize(), value=u'╔' + "Intelligence -> " + str(data['classes'][char]['skills']['Intelligence']) + "\n" + "Dexterity -> " + str(data['classes'][char]['skills']['Dexterity']) + "\n" + "Strength -> " + str(data['classes'][char]['skills']['Strength']) + "\n" + "Defense -> " + str(data['classes'][char]['skills']['Defense']) + "\n" + "Agility -> " + str(data['classes'][char]['skills']['Agility']) + "\n")
		await self.bot.send_message(ctx.message.channel, embed=embed)
			
def setup(bot):
	bot.add_cog(WynnCraft(bot))