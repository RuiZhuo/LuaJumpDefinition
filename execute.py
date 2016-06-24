import sublime, sublime_plugin
import os
import re
import json
import struct

TYPE_CLASS		=	1
TYPE_VARIABLE	=	2

def init():
	print("init")
	global JSON_DATA 
	JSON_DATA = []
	for window in sublime.windows():
		rootPath = window.folders()
	readFile = open(rootPath[0] + "/.jump_definition.tags", 'rt')
	try:
		JSON_DATA = json.load(readFile)
	finally:
		readFile.close()

def plugin_loaded():
    sublime.set_timeout(init, 200)

def isLUAFounction(lineStr, lineNum, path):
	retDis = {}

	#判断是否为funciton 开头
	pattern = re.compile(r'^function+[\s]+')
	match = pattern.match(lineStr)
	subStr = ""
	if match:
		subStr = pattern.sub("", lineStr)
		funcName = subStr.split("(")[0]
		classSplitList = re.split(r'[:.]', funcName)
		if len(classSplitList) > 1:
			retDis['className'] = classSplitList[0]
			retDis['funcName'] = classSplitList[1]
		else:
			retDis['funcName'] = funcName
		retDis['lineNum'] = lineNum
		retDis['path'] = path
		retDis['type'] = TYPE_CLASS

	return retDis

def isGobalVaribale(lineStr, lineNum, path):
	retDis = {}
	#剔除空格
	formatStr = re.sub(r'\s+', "", lineStr)
	#判断是否由 大写 与 _ 组成的变量
	match = re.match(r'^[A-Z_]+=', formatStr)
	if match:
		retDis['varName'] = match.group().split("=")[0]
		retDis['lineNum'] = lineNum
		retDis['path'] = path
		retDis['type'] = TYPE_VARIABLE

	return retDis

class LuaJumpDefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global JSON_DATA
		if len(JSON_DATA) == 0:
			print("first load json")
			for window in sublime.windows():
				rootPath = window.folders()
			readFile = open(rootPath[0] + "/.jump_definition.tags", 'rt')
			try:
				JSON_DATA = json.load(readFile)
			finally:
				readFile.close()
		analyseData = ""
		type = None
		sels = self.view.sel()
		for sel in sels:
			#获得光标位置上的单词
			regionWord = self.view.word(sel.a)
			#获得单词下一个字符
			nextSymbol = self.view.substr(regionWord.b)
			#获得单词上一个字符
			preSymbol = self.view.substr(regionWord.a - 1)
			if nextSymbol == "(":
				type = TYPE_CLASS
				if preSymbol == ":" or preSymbol == ".":
					regionClass = self.view.word(regionWord.a - 2)
					analyseData = self.view.substr(regionClass) + ":" + self.view.substr(regionWord)
				else:
					analyseData = self.view.substr(regionWord)
			else:
				strVarName = self.view.substr(regionWord)
				if re.match(r'^[A-Z_]+', strVarName):
					type = TYPE_VARIABLE
					analyseData = strVarName

			if type == TYPE_CLASS:
				print("分析的方法名：" + analyseData)
			elif type == TYPE_VARIABLE:
				print("分析的全局变量名：" + analyseData)

		if analyseData == "":
			return

		jumpData = None	
		if type == TYPE_CLASS:
			funcData = analyseData.split(":")
			for data in JSON_DATA:
				if data['type'] == TYPE_VARIABLE:
					continue
				if len(funcData) > 1:
					if len(data) > 4 and data['className'] == funcData[0] and data['funcName'] == funcData[1]:
						jumpData = data
				else:
					if len(data) == 4 and data['funcName'] == funcData[0]:
						jumpData = data

		elif type == TYPE_VARIABLE:
			for data in JSON_DATA:
				if data['type'] == TYPE_CLASS:
					continue
				if data['varName'] == analyseData:
					jumpData = data

		if jumpData:
			lineNum = jumpData['lineNum'] + 1
			self.view.window().open_file(jumpData['path'] + ":%d"%lineNum, sublime.ENCODED_POSITION)
		else:
			sublime.status_message("未找到方法或变量")	
			print("未找到方法或变量")

class LuaBuildTagCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		allFuncData = []
		rootPath = ''
		rootPath = self.view.window().folders()

		#遍历根目录下的所有lua文件，包含子目录
		for root, dirs, files in os.walk(rootPath[0]):
			for file in files:
				if ".lua" in file:
					filePath = os.path.join(root,file)
					file_object = open(filePath, 'rt', encoding="utf-8")
					try:
					    all_the_text = file_object.readlines()
					    lineNum = 0
					    for test in all_the_text:
					    	funcDir = isLUAFounction(test.strip(), lineNum, filePath)
					    	if len(funcDir) > 0:
					    		allFuncData.append(funcDir)
					    	else:
					    		varDir = isGobalVaribale(test.strip(), lineNum, filePath)
					    		if len(varDir) > 0:
					    			allFuncData.append(varDir)

					    	lineNum = lineNum + 1
					finally:
					     file_object.close()

		writeFile = open(rootPath[0] + "/.jump_definition.tags", 'wt')
		try:
			global JSON_DATA
			JSON_DATA = allFuncData
			writeFile.write(json.dumps(allFuncData, indent=4))
		finally:
			writeFile.close()