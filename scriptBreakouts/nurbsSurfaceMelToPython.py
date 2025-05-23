import maya.cmds as mc
import maya.api.OpenMaya as om2

def mGetNurbsSurfaceDefMel(worldSpaceAttr:om2.MPlug) -> list:
	"""
	UTILITY COMMAND. DO NOT MIX MEL AND PYTHON. see and use mGetNurbsSurfaceDefStr and mGetNurbsSurfaceDefPy

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
		raise TypeError(f"mGetNurbsSurfaceDefMel: got entire MSelectionList, input an attribute with .getPlug()")

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
			raise TypeError("mGetNurbsSurfaceDefMel: invalid input, input a shape.worldSpace attribute; check error line (MObjects cannot return name without a valid MFn extractor)")
		try:
			recastAttr:om2.MSelectionList = om2.MSelectionList().add(grabInputForRecast.getSelectionStrings()[0]+".worldSpace")
				# see if it has a .worldSpace attribute and recast the selection as an MPlug object via MSelectionList
			del grabInputForRecast
			testInput = recastAttr.getPlug(0)
				# get MPlug
				# pass this MPlug to the MPlug tester at next conditional
			del recastAttr
		except:
			raise TypeError(f"mGetNurbsSurfaceDefMel: unexpected MObject does not have worldSpace attribute, input a shape.worldSpace attribute; got: {grabInputForRecast.getSelectionStrings()[0]} ")

	if type(testInput) == type (om2.MPlug):	
		# test if it's TRULY a plug
		plugGetName = testInput.partialName(includeNodeName = True, useFullAttributePath  = True, useLongNames  = True)
		if "." in plugGetName :
			# well "anything.something" IMPLIES to be an attribute when a path is separated by a dot
			if testInput.asMObject().apiType() == om2.MFn.kNurbsSurfaceData:
				# this is a nurbsSurface
				curveType = "nurbsSurface"
			else:
				raise TypeError(f"mGetNurbsSurfaceDefMel: shape data is not a nurbsSurface, got: {testInput.asMObject().apiTypeStr}\nIf MPlug was taken from MFnDependencyNode.findPlug(), recast selection by using MSelectionList().add('[-nodeNamePath-].worldSpace').getPlug(0)")
		else:
			raise TypeError(f"mGetNurbsSurfaceDefMel: MPlug IS NOT AN MPlug, DO NOT USE MSelectionList.getPlug() ON THINGS THAT IS NOT AN ATTRIBUTE: {plugGetName}")
	else:
		raise TypeError(f"mGetNurbsSurfaceDefMel: input sanitisation fail, see documentation for expected input")


	melString = testInput.getSetAttrCmds()
	# WARNING: openMaya will crash on this command instead of raising and error if this MPlug is not an actual MPlug

	del melString[-2:] # don't need the last bit
	del melString[4] # don't need blank double-tab line
	del melString[0] # don't need the MEL command
	return [melString, curveType]
	

def mGetNurbsSurfaceDefStr(name) -> list:
	"""
	utility function for maya

	gets setAttr nurbsCurve data definition from shape node,
	by getting shape.worldspace[0] and grabbing the setAttr string from openMaya

	THIS COMMAND RETURNS A STRING MEANT FOR SCRIPT EDITING. see mGetNurbsSurfaceDefPy for python list version

	:param name:    expects om2.MObject, either of the shape node, or the direct worldSpace or worldSpace[0] attribute (the MObject or string)

	TODO
	!! :param attr:	expects om2.MObject of target attribute, for printing out setAttr() commands
	
	:return:	string of curve data, in python requirements
	"""
	melString, surfaceType = mGetNurbsSurfaceDefMel(name)

	# REMINDER: STRINGS ARE IMMUTABLE

	for i in range(len(melString)):
		melString[i] = melString[i].replace("\t",'') # strip all indents

	melString[0] = melString[0].replace("yes", "True")
	melString[0] = melString[0].replace("no", "False")
	melString[0] = melString[0].replace(' ', ", ")
	melString[0] += ", "

	for i in [1,2]:
			# '11 0 0 0 1 2 3 4 5 6 6 6'
		melStringKnots = melString[i].split(' ', maxsplit=1)
			# ['11', '0 0 0 1 2 3 4 5 6 6 6']
		melStringKnots[1] = melStringKnots[1].replace(' ', ', ')
			# ['11', '0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6']
		melStringKnots[1] = f"[{melStringKnots[1]}]"
			# ['11', '[0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6]']
		melString[i] = f"{melStringKnots[1]}, {melStringKnots[0]}, "
			# '[0, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6], 11'

	melString[3] += ', ' # CV-triple count
	cvList = []

	for i in range(len(melString) -3):
		# '\t\t0.19991679083637276 -1 0.19991679083637268'
		melString[i+3] = melString[i+3].replace('\t', '')
		# '0.19991679083637276 -1 0.19991679083637268'
		melString[i+3] = melString[i+3].replace(' ', ", ")
		# "0.19991679083637276, -1, 0.19991679083637268"
		melString[i+3] = f"({melString[i+3]}), "
		# "[0.19991679083637276, -1, 0.19991679083637268], "
	melString[-1] = melString[-1].replace("), " , ")") # remove comma from end of last item

	buildString = ""
	for line in melString:
		buildString += line

	return [buildString, surfaceType]


def mGetNurbsSurfaceDefPy(name) -> list:
	"""
	utility function for maya

	gets setAttr nurbsSurface data definition from shape node,
	by getting shape.worldspace[0] and grabbing the setAttr string from openMaya

	THIS COMMAND RETURNS A LIST MEANT FOR UNPACKING INTO mc.setAttr(). see mGetNurbsSurfaceDefStr for string version

	:param name:    expects om2.MObject

	"""

	melString, surfaceType = mGetNurbsSurfaceDefMel(name)

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
	for i in [1,2]:
		# '9 0 0 0 1 2 3 4 4 4'
		melString[i] = melString[1].split(' ')
		melStringKnotCount = int(melString[i].pop(0)) # remove knot count
		for j in range(len(melString[i])):
			melString[i][j] = int(melString[i][j])
			# raise default error if this can't be parsed
		melString[i] = [melString[i].copy(), melStringKnotCount]

	buildList = []

	buildList += melString[0] # basic info
	buildList += melString[1] # first knot data [0,0,0,1,1,1,2,2,2...], n
	buildList += melString[2] # second knot data [0,0,0,1,1,1,2,2,2...], n
	buildList.append(int(melString[3])) # cv count

	melStringCvs = melString[4:]

	for cv in range(len(melStringCvs)):
		# triples now
		melStringCvs[cv] = melStringCvs[cv].split(' ')
		for i in range(len(melStringCvs[cv])):
			melStringCvs[cv][i] = float(melStringCvs[cv][i])
			# raise default error if this can't be parsed
	buildList += melStringCvs

	return [buildList, surfaceType]