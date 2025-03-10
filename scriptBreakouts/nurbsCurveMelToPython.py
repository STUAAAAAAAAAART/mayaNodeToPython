import maya.cmds as mc
import maya.api.OpenMaya as om2

def mGetNurbsCurveDefMel(worldSpaceAttr:om2.MPlug) -> list:
	"""
	UTILITY COMMAND. DO NOT MIX MEL AND PYTHON. see and use mGetNurbsCurveDefStr and mGetNurbsCurveDefPy

	gets setAttr nurbsCurve data definition from shape node,
	by getting shape.worldspace[0] and grabbing the setAttr string from openMaya

	returns list of 2:
	- first is list of string lines containing curve data, with setAttr commands and MEL statement delimiter (;) removed
	- second is string of curve data type ("nurbsCurve" or "dataBezierCurve"), for passing to mc.setAttr(Type) flag

	PLEASE USE om2.MSelectionList.getPlug() AND TEST EXTERNALLY BEFORE INPUT. DO NOT PASS ENTIRE om2.MSelectionList TO INPUT
	
	:param name:    expects om2.MObject, shape node's worldSpace or worldSpace[0] attribute

	:return:	see description
	"""
	
	testInput : om2.MPlug = worldSpaceAttr
	curveType = ""

	if type(testInput) == type (om2.MSelectionList):
		# someone tossed an MSelectionList... you know what just get them to pick one
		raise TypeError(f"mGetNurbsCurveDefMel: got entire MSelectionList, input an attribute with .getPlug()")

	if type(testInput) == type (om2.MObject):
		# it's a random MObject
		# siiiiiigh....
		# try to steer towards a valid worldspace attribute

		# recast into MSelectionlist and append ".worldSpace" to it
		# DO NOT use MFnDependencyNode.findPlug(), it returns an MPlug that
			# still points to the DG/MObject and does to work with MPlug.asMObject().apiType
		try:
			grabInputForRecast = om2.MSelectionList().add(testInput)
			# see if it's valid in the first place
		except:
			raise TypeError("mGetNurbsCurveDefMel: invalid input, input a shape.worldSpace attribute; check error line (MObjects cannot return name without a valid MFn extractor)")
		try:
			recastAttr:om2.MSelectionList = om2.MSelectionList().add(grabInputForRecast.getSelectionStrings()[0]+".worldSpace")
				# see if it has a .worldSpace attribute and recast the selection as an MPlug object via MSelectionList
			del grabInputForRecast
			testInput = recastAttr.getPlug(0)
				# get MPlug
				# pass this MPlug to the MPlug tester at next conditional
			del recastAttr
		except:
			raise TypeError(f"mGetNurbsCurveDefMel: unexpected MObject does not have worldSpace attribute, input a shape.worldSpace attribute; got: {grabInputForRecast.getSelectionStrings()[0]} ")

	if type(testInput) == type (om2.MPlug):	
		# test if it's TRULY a plug
		plugGetName = testInput.partialName(includeNodeName = True, useFullAttributePath  = True, useLongNames  = True)
		if "." in plugGetName :
			# well "anything.something" IMPLIES to be an attribute when a path is separated by a dot
			if testInput.asMObject().apiType() == om2.MFn.kNurbsCurveData:
				# this is a nurbsCurve
				curveType = "nurbsCurve"
			elif testInput.asMObject().apiType() == om2.MFn.kBezierCurveData:
				# this is a bezierCurve
				curveType = "dataBezierCurve"
			else:
				raise TypeError(f"mGetNurbsCurveDefMel: shape data is not a nurbsCurve or a dataBezierCurve, got: {testInput.asMObject().apiTypeStr}\nIf MPlug was taken from MFnDependencyNode.findPlug(), recast selection by using MSelectionList().add('[-nodeNamePath-].worldSpace').getPlug(0)")
		else:
			raise TypeError(f"mGetNurbsCurveDefMel: MPlug IS NOT AN MPlug, DO NOT USE MSelectionList.getPlug() ON THINGS THAT IS NOT AN ATTRIBUTE: {plugGetName}")
	else:
		raise TypeError(f"mGetNurbsCurveDefMel: input sanitisation fail, see documentation for expected input")


	melString = testInput.getSetAttrCmds()
	# WARNING: openMaya will crash on this command instead of raising and error if this MPlug is not an actual MPlug

	melString.pop() # don't need the last bit
	melString.pop(0) # don't need the MEL command
	return [melString, curveType]
	

def mGetNurbsCurveDefStr(name) -> list:
	"""
	utility function for maya

	gets setAttr nurbsCurve data definition from shape node,
	by getting shape.worldspace[0] and grabbing the setAttr string from openMaya

	THIS COMMAND RETURNS A STRING MEANT FOR SCRIPT EDITING. see mGetNurbsCurveDefPy for python list version

	:param name:    expects om2.MObject, either of the shape node, or the direct worldSpace or worldSpace[0] attribute (the MObject or string)

	TODO
	!! :param attr:	expects om2.MObject of target attribute, for printing out setAttr() commands
	
	:return:	string of curve data, in python requirements
	"""
	melString, curveType = mGetNurbsCurveDefMel(name)

	# REMINDER: STRINGS ARE IMMUTABLE

	for i in range(len(melString)):
		melString[i] = melString[i].replace("\t",'') # strip all indents

	melString[0] = melString[0].replace("yes", "True")
	melString[0] = melString[0].replace("no", "False")
	melString[0] = melString[0].replace(' ', ", ")
	melString[0] += ", "

		# '11 0 0 0 1 2 3 4 5 6 6 6'
	melStringKnots = melString[1].split(' ', maxsplit=1)
		# ['11', '0 0 0 1 2 3 4 5 6 6 6']
	melStringKnots[1] = melStringKnots[1].replace(' ', ', ')
		# ['11', '0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6']
	melStringKnots[1] = f"[{melStringKnots[1]}]"
		# ['11', '[0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6]']
	melString[1] = f"{melStringKnots[1]}, {melStringKnots[0]}, "
		# '[0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6], 11'

	melString[2] += ', ' # CV count

	for i in range(len(melString) -3):
		# "-2.0000000000001679 5 13.00000000000019"
		melString[i+3] = melString[i+3].replace(' ', ", ")
		# "-2.0000000000001679, 5, 13.00000000000019"
		melString[i+3] = f"[{melString[i+3]}], "
		# "[-2.0000000000001679, 5, 13.00000000000019], "
	melString[-1] = melString[-1].replace("], " , "]") # remove comma from end of last item

	buildString = ""
	for line in melString:
		buildString += line

	return [buildString, curveType]


def mGetNurbsCurveDefPy(name) -> list:
	"""
	utility function for maya

	gets setAttr nurbsCurve data definition from shape node,
	by getting shape.worldspace[0] and grabbing the setAttr string from openMaya

	THIS COMMAND RETURNS A LIST MEANT FOR UNPACKING INTO mc.setAttr(). see mGetNurbsCurveDefStr for string version

	:param name:    expects om2.MObject

	"""

	melString, curveType = mGetNurbsCurveDefMel(name)

	for i in range(len(melString)):
		melString[i] = melString[i].replace("\t",'')


	melString[0] = melString[0].split(' ')

	for i in range(len(melString[0])):
		try:
			melString[0][i] = int(melString[0][i])
		except:
			if melString[0][i] == "yes":
				melString[0][i] = True
			elif melString[0][i] == "no":
				melString[0][i] = False
			else:
				raise ValueError("problems parsing info string into int and bool")
	melString[1] = melString[1].split(' ')
	melStringKnotCount = int(melString[1].pop(0)) # remove knot count
	for i in range(len(melString[1])):
		melString[1][i] = int(melString[1][i])
		# raise default error if this can't be parsed

	buildList = []

	buildList += melString[0] # basic info
	buildList.append(melString[1]) # knot data [0,0,0,1,1,1,2,2,2...]
	buildList += [int(melString[2]), melStringKnotCount] # number of knots, number of CVs

	melStringCvs = melString[3:]

	for cv in range(len(melStringCvs)):
		# triples now
		melStringCvs[cv] = melStringCvs[cv].split(' ')
		for i in range(len(melStringCvs[cv])):
			melStringCvs[cv][i] = float(melStringCvs[cv][i])
			# raise default error if this can't be parsed
	buildList += melStringCvs

	return [buildList, curveType]