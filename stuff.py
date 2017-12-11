﻿from functools import wraps
import pymysql.cursors

def checkPermissions(command):
	def decorator(func):
		@wraps(func)
		async def wrapper(*args, **kwargs):
			self = args[0]
			ctx = args[1]
			print(command)
			if ctx.message.channel.is_private is True:
				return await func(*args, **kwargs)
			connection = pymysql.connect(host='localhost', user=self.bot.MYSQL_USER, password=self.bot.MYSQL_PASSWORD, db=self.bot.MYSQL_DB, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
			serverID = ctx.message.server.id
			try:
				with connection.cursor() as cursor:
					#Check if entry exists then update or create one
					sql = "SELECT `disabled` FROM `permissions` WHERE `serverID`=%s AND `command`=%s"
					cursor.execute(sql, [serverID, command])
					print(serverID, command)
					result = cursor.fetchone()
					if result is not None:
						print(result['disabled'])
						if (int(result['disabled']) == 1):
							await self.bot.send_message(ctx.message.channel, "I'm sorry but commands relating to " + command + " have been disabled.")
							return False
					return await func(*args, **kwargs)
			finally:
				connection.close()
		return wrapper
	return decorator

def no_pm():
	def decorator(func):
		@wraps(func)
		async def wrapper(*args, **kwargs):
			self = args[0]
			ctx = args[1]
			if ctx.message.channel.is_private is False:
				return await func(*args, **kwargs)
			await self.bot.send_message(ctx.message.channel, "I'm sorry but this command can't be used in a direct message")
			return False
		return wrapper
	return decorator

class BoxIt():
	BOX_UPPER_LEFT = u'╔'
	BOX_UPPER_RIGHT = u'╗'
	BOX_LOWER_LEFT = u'╚'
	BOX_LOWER_RIGHT = u'╝'
	BOX_HORIZ_CONNECTOR = u'═'
	BOX_VERT_CONNECTOR = u'║'
	BOX_VERT_HORIZ_CONNECTOR_LEFT = u'╠'
	BOX_VERT_HORIZ_CONNECTOR_RIGHT = u'╣'
	BOX_INTERNAL_VERT_SEPERATOR = u'│'
	BOX_HORIZ_INTERNAL_CONNECTOR_TOP = u'╤'
	BOX_HORIZ_INTERNAL_CONNECTOR_BOTTOM = u'╧'
	BOX_INTERNAL_PASSTHROUGH_VERT = u'╪'
	
	def __init__(self):
		self.title = ''
		self.data = []
		self.biggest = {}
	
	def addRow(self, row):
		self.data.append(row)

		for index, item in enumerate(row):
			if index not in self.biggest:
				self.biggest[index] = 0

			if len(str(item)) > self.biggest[index]:
				self.biggest[index] = len(str(item))

	def isEmpty(self):
		if len(self.data) == 0:
			return True
		else:
			return False

	def setTitle(self, title):
		self.title = str(title)

	
	def padString(self, string, padAmount, padStart = False, padCharacter = " "):
		if type(string) == int or type(string) == float: # Right aling integers
			padStart = True
		string = str(string)
		while len(string) < padAmount:
			if padStart:
				string = padCharacter + string
			else:
				string += padCharacter
		return string

	def centerpadString(self, string, padAmount, padCharacter = " "):
		string = str(string)
		while len(string) < padAmount:
			string = padCharacter + string + padCharacter
		return string

	def generateRow(self, data, seperator = False):
		if not seperator:
			seperator = self.BOX_INTERNAL_VERT_SEPERATOR
		row = []
		row.append(self.BOX_VERT_CONNECTOR)
		for index, item in enumerate(data):
			if index != 0:
				row.append(seperator)
			row.append(' ' + self.padString(item, self.biggest[index]) + ' ')
		row.append(self.BOX_VERT_CONNECTOR)
		return row
		
	def generateSeperatorLine(self, data, lineChar = False, seperator = False):
		if not lineChar:
			lineChar = self.BOX_HORIZ_CONNECTOR
		if not seperator:
			seperator = self.BOX_INTERNAL_PASSTHROUGH_VERT
		width = 0
		row = []
		row.append(self.BOX_VERT_HORIZ_CONNECTOR_LEFT)
		for index, item in enumerate(data):
			if index != 0:
				row.append(seperator)
			row.append(self.padString('', self.biggest[index]+2, False, lineChar))
			width += len(item)
		row.append(self.BOX_VERT_HORIZ_CONNECTOR_RIGHT)
		return row

	def generateFirstLine(self):
		seperator = self.BOX_HORIZ_INTERNAL_CONNECTOR_TOP
		row = self.generateSeperatorLine(self.data[0], False, self.BOX_HORIZ_INTERNAL_CONNECTOR_TOP)
		row[0] = self.BOX_UPPER_LEFT
		row[len(row)-1] = self.BOX_UPPER_RIGHT
		rowTemp = ''.join(row)
		rowTemp = rowTemp[0:4] + self.title + rowTemp[-(len(rowTemp)-(len(self.title)+4)):]
		row = rowTemp

		return row
	
	def generateLastLine(self):
		seperator = self.BOX_HORIZ_INTERNAL_CONNECTOR_BOTTOM
		row = []
		row.append(self.BOX_LOWER_LEFT)
		for index, item in enumerate(self.data[0]):
			if index != 0:
				row.append(seperator)
			row.append(self.padString('', self.biggest[index]+2, False, self.BOX_HORIZ_CONNECTOR))
		row.append(self.BOX_LOWER_RIGHT)
		return row

	
	def box(self):
		box = [ ]

		box.append(self.generateFirstLine())

		for index, data in enumerate(self.data):
			box.append(self.generateRow(data))
			if index==0:
				box.append(self.generateSeperatorLine(data))

		box.append(self.generateLastLine())
		
		thing = ''
		for index, row in enumerate(box):
			if index != 0:
				thing += '\n'
			for jndex, item in enumerate(row):
				thing += item
		return thing