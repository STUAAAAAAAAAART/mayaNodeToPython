from datetime import datetime as dt

import maya.cmds as mc
import maya.api.OpenMaya as om2

# ====== file preparation
# do file handling just in case there's a file creation error before doing all the maya node combing

# target outFile to save next to maya scene file location
fileNameMa = mc.file(q=True, sn=True, shn=True)
fileRootPathMa = mc.file(q=True, sn = True)[: -(len(fileNameMa))]
# example output: D:/Folder01/project03/
# os.getcwd() does not update in maya when an other file is opened

saveTime = dt.now()
# get timestamp in current day (24h not unix, 0-86399)
makeSecondsTimestamp = (saveTime.hour*3600) + (saveTime.minute * 60) + saveTime.second

# get system timezone, UTC offset
sysTimezone = (saveTime.astimezone().utcoffset().seconds) / 36
# format system timezone offset to hhmm
tzHalfHourValue = abs(sysTimezone) % 100 # see if UTC offset has minutes
if tzHalfHourValue:
	tzHalfHourValue = int(tzHalfHourValue * 0.6) # convert seconds to mm in hhmm
	sysTimezone = int(sysTimezone / 100) * 100 + tzHalfHourValue * (sysTimezone > 0) - tzHalfHourValue * (sysTimezone < 0)
	#           = ------------ hh -------------  --------- +mm if positive ---------   --------- -mm if negative ---------
# leading zeroes
sysTimezone = int(sysTimezone)
if sysTimezone < 0:
	sysTimezone = f"{sysTimezone:05d}" # -0800 (sign counts for leading zero)
else:
	sysTimezone = f"{sysTimezone:04d}" # 1000

# make dateString (utc0.yyyy.mm.dd.sssss)
dateString = f"{sysTimezone}.{saveTime.year:04}.{saveTime.month:02}.{saveTime.day:02}.{makeSecondsTimestamp:05}"

# filename:
fileNameScriptOut = f"{fileNameMa}_print.{dateString}.py"

outfile = None
try:
	outFile = open(f"{fileRootPathMa}/{fileNameScriptOut}","x")
	# x, not w, because w will overrite existing files, while x will only make new ones
	# also longPath used, relative path would require os.chdir(), depends on how you want to go about doing this
except:
	import os
	if os.stat(f"{fileRootPathMa}/{fileNameScriptOut}").st_size == 0:
		# open and overwrite, if existing file is 0 bytes
		outFile = open(f"{fileRootPathMa}/{fileNameScriptOut}","w")
	else:
		# there is somehow a file made with the same name down to the second, with existing data
		raise FileExistsError(f"File exists and not empty: {fileNameScriptOut}")
# ====== file name ready


activeSelection: om2.MSelectionList = om2.MGlobal.getActiveSelectionList()

# detection phase: get all connections strictly within selection

checkList : list = activeSelection.getSelectionStrings() # -> list : ["shortName", ... ]

nodeTypeShapeNodes = [ # list
	# currently supported shapes for re-creation
	"bezierCurve", "nurbsCurve"
	]

nodeTypeUseCommandsConstraint = [ # list
	# the usual constraints
		# [many parents, 1 weighted child]
		# ideally 1 parent 1 child
		# if command is used on an existing child of a constraint, the connected constraint node is reused and modified 
	'parentConstraint', 'pointConstraint', 'orientConstraint', 'aimConstraint', 'scaleConstraint', 
	# poleVectorConstraint, for IK solvers
	'poleVectorConstraint'
]

nodeTypeUseCommandsIK = [ # list
	# ikHandle from IK solvers
		# complex, depending on type of solver
	'ikHandle'
]

nodeTypeSkip = [ # list
	'ikEffector' # node created with IK nodes, rarely does the need to adjust them arise
]

nodeTypeFilterOut = [ # list
	# other constrain types specified in maya; skip
	'normalConstraint', 'dynamicConstraint', 'pointOnPolyConstraint', 'rigidConstraint', 'symmetryConstraint', 'tangentConstraint', 
	# skinning nodes, apply in-scene or elsewhere; skip
	'skinCluster', 'cluster', 'clusterFlexorShape', 'clusterHandle', 'jointCluster', 'jointClusterManip'
]

# skipNodeFromConnectionCheck = nodeTypeUseCommandsConstraint + nodeTypeUseCommandsIK + nodeTypeFilterOut

selectionList = []
parentList = [] # [ [child from nodeList , parent from file ] , ...]
constructorList = []

nodeList = []
nodeListStage2 = [] # in print order, makes referencing them a lot easier here
jointList = []
addAttrList = []
setAttrList = []
connectionList = []

nodeCounter = 0
skipList = [] # for instances like transform nodes where it has already been processed ahread of the list

for node in checkList:
	if node in skipList:
		# node found in skipList, possibly processed in advance
		skipList.pop(skipList.index(node)) # remove from skiplist to make searching tiny bit quicker
		continue

	addToCounter = 1

	# ============= write createNode / creation commands
	thisNodeType = mc.nodeType(node)
	if thisNodeType in nodeTypeUseCommandsConstraint: # constraints, use dedicated commands
		stu_constraintChild = mc.listConnections(node+'.constraintParentInverseMatrix', source = True , destination = False)[0]
			# this might be a bit too complex to cover all possible cases, probably TODO improve this as needed
		
		# oh my god, every constraint command has exclusive flags
		# also the constrain commands create a user-defined attribute

		# query number of targets

		# ///////////////////////////////////////////////////////////////////////////
		
		# if many targets: comment and list names
		nodeList.append(f"mc.{thisNodeType}('!!SELECT PARENT HERE','{stu_constraintChild}', n='{node}' , maintainOffset=False)")
		# mc.command(selection) # e.g. [parent,child]
		
		# if one target: fully enumerate exact command and values
			# (especially important for poleVectorConstraint because it's being used so frequently with IK systems)

		nodeList.append(f"mc.{thisNodeType}('!!SELECT PARENT HERE','{stu_constraintChild}', n='{node}' , maintainOffset=False)")
		# mc.command(selection) # e.g. [parent,child]

		nodeListStage2.append(node) # handoff to stage 2 
		pass

	elif thisNodeType in ["nurbsCurve", "bezierCurve"] or thisNodeType == "transform": # nurbsCurve and general transforms
		"""
		CAUTION0: now dealing with DAG paths with relative names and parenting hierachy
		CAUTION1: now dealing with object instancing, which means many transform nodes can share a single shape node

		stuff to end up with:
		- transform node
		- transform attributes
		- shape node
		- shape data
		- shape node attributes (just in case)
		"""
		# pre-prepare handlers with [[transform/s,... ] , shape]
		transformAndShape = [[], None]
		thisShapeType = ""

		# if node is transform; current state: [[], None] 
		if thisNodeType == "transform":
			# get shape
			thisNodeShapes = mc.listRelatives(n=node, s=True, ni=True)
			# if has shapes:
			if len(thisNodeShapes) > 0:
				thisShapeType = mc.nodeType(thisNodeShapes[0])
				# set transformAndShape[1]
				transformAndShape[1] = thisNodeShapes[0]
				# end up with [[], shape]
			# if no shapes:
			else:
				transformAndShape[0].append(node)
				# end up with [[node], None]

		# if node is curve shapes: current state if not transform: [[], None]
		if thisNodeType in ["nurbsCurve, bezierCurve"]:
			thisShapeType = thisNodeType
			transformAndShape[1] = node
			# end up with [[], shape]
		"""
		possible states:
		- [[], shape] ; has valid shape node
		- [[node], None] ; only transform
		"""
		# enumerate transform nodes if there is a shape
		if transformAndShape[1]:
			transformAndShape[0] = mc.listRelatives(transformAndShape[1], ap=True) # list
			# first item in list is original object, subsequent are instances
		
		# recast transform list to MSL just in case (going to use this for checking re-encounters with skipList)
		listGetSel : om2.MSelectionList = om2.MSelectionList()
		for i in transformAndShape[0]:
			listGetSel.add(i)
		transformAndShape[0] = list(listGetSel.getSelectionStrings())
		listGetSel.clear()
		del listGetSel
		
		"""
		possible states:
		- [[node], shape] ; transforms and instances, has valid shape node
		- [[node], None] ; only transform
		"""
		# don't check for list duplicates here: this branch will grab all relevant transform and/or shape relatives at once, and processes them in proper order
			# if a node (that has already been processed) is encountered down the checkList, it would be caught at the top of this if-tree before it ever reaches here
		
		# enumerate first transform
		getParent = mc.listRelatives(transformAndShape[0][0])
		if getParent:
			getParent = [f'p="{getParent[0]}"', getParent[0]]
		else:
			getParent = ['',''] # None cast to string is the word 'None' -_-
		nodeList.append(f'nodeList[{nodeCounter}] = mc.createNode("transform", n="{transformAndShape[0][0]}", {getParent[0]}, skipSelect = True) # parented under: {getParent[1]}')
		#                 nodeList[n]             = mc.createNode("transform", n="nName"                    , p="parent"    , skipSelect = True)
		# no addToCounter here, it's already 1
		nodeListStage2.append(transformAndShape[0][0])

		# enumerate shape node
		if transformAndShape[1]:
			shapeCommand = []
			shapeCommand.append(f'nodeList[{nodeCounter+1}] = mc.createNode({thisShapeType}, n="{transformAndShape[1]}", p="{transformAndShape[0][0]}", skipSelect = True)')
			#                     nodeList[n]               = mc.createNode("nurbsCurve"   , n="shapeName"             , P="transformName",             skipSelect = True)
			addToCounter += 1 # shape node
			skipList.append(transformAndShape[1])
			nodeListStage2.append(transformAndShape[1])
			if thisShapeType in ["nurbsCurve, bezierCurve"]:
				# put setAttr(".cc") command here?
				# ----------------------------------------------------------------------------------------------
				# time for om2.MPlug.getSetAttrCmds()
				getShapeMSL : om2.MSelectionList = om2.MSelectionList().add(transformAndShape[1]+".worldSpace")
				getShapePlug :om2.MPlug = getShapeMSL.getPlug(0)
				getShapeMSL.clear()
				del getShapeMSL
				melString = getShapePlug.getSetAttrCmds() # list of line strings, in MEL
				melString.pop() # don't need the last bit
				getShapeDataType = ""
				# get data type
				if "dataBezierCurve" in melString[0]:
					getShapeDataType = "dataBezierCurve"
				else:
					getShapeDataType = "nurbsCurve"
				melString.pop(0) # don't need the MEL command itself

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

				for i in range(len(melString) -3): # CV triples
					# "-2.0000000000001679 5 13.00000000000019"
					melString[i+3] = melString[i+3].replace(' ', ", ")
					# "-2.0000000000001679, 5, 13.00000000000019"
					melString[i+3] = f"[{melString[i+3]}], "
					# "[-2.0000000000001679, 5, 13.00000000000019], "
				melString[-1] = melString[-1].replace("], " , "]") # remove comma from end of last item

				buildString = ""
				for line in melString:
					buildString += line

				# ----------------------------------------------------------------------------------------------
					
				shapeCommand.append(f'mc.setAttr(f"{'{'}nodeList[{nodeCounter+1}]{'}'}.cc", {buildString}, type = "{getShapeDataType}")')
				#                     mc.setAttr(f"  {          nodeList[n]        }.cc",   {curveData}  , type = "nurbsCurve"        )
				# remember to use the .cc attribute and not the .worldSpace attribute when applying grafted curve data
			else:
				# could be polygon mesh or NURBS surface, skip for now
				# TODO: reconsider for NURBS surface, might have a chance it'd be used as a UV positional control				
				shapeCommand.append("# check maya scene for shape node type, might be polymesh or NURBS surface")
		nodeList.append(f"{shapeCommand[0]}\n{shapeCommand[1]}")
			
		# enumerate subsequent instances
		if len(transformAndShape[0]) > 1: # if there are more than one transform nodes gathered 
			for tf in transformAndShape[0][1:]: #leave out the first one, it's done above
				# make instance command
				# mc.instance( transformAndShape[0][0] , lf=False, st=False)
				# make reparenting command
				# mc.parent()
				skipList.append(tf)
				nodeListStage2.append(tf)
				addToCounter += 1 # +1 instance
		
		# script list admin
			# append all created nodes (except thisNode) into skipList
			# append all created nodes to stage 2 processing list for connection and attribute handling
			# note that transform node should have its own override to get transform attribute data and wireframe and outliner colour states
		pass

	elif thisNodeType == "joint":
		# script-only: return name of joints
		"""
		normally work would be done upon an existing skinned model with joints
		the exceptions would be with copying driver/utility joints, but those should be scripted separately or created manually

		see also the duplicate hierachy script
		"""
		# annotate joint connection properties for overview; joint connection commands will still be recorded later
		# query joint for any connections
		getConnectionsInbound = mc.listConnections(node, sh=True, s=True, d=False)
		getConnectionsOutbound = mc.listConnections(node, sh=True, s=False, d=True)
		
		grabNode:om2.MSelectionList = om2.MSelectionList()
		listInbound = []
		listOutbound = []
		for n in getConnectionsInbound:
			if mc.nodeType(n) == "nodeGraphEditorInfo":
				continue
			grabNode.clear()
			grabNode.add(n)
			grabNodeSelectionString = grabNode.getSelectionStrings(0)[0]
			if grabNodeSelectionString in listInbound:
				continue
			listInbound.append(grabNodeSelectionString)
		for n in getConnectionsOutbound:
			if mc.nodeType(n) == "nodeGraphEditorInfo":
				continue
			grabNode.clear()
			grabNode.add(n)
			grabNodeSelectionString = grabNode.getSelectionStrings(0)[0]
			if grabNodeSelectionString in listOutbound:
				continue
			listOutbound.append(grabNodeSelectionString)

		# add to jointList
		jointList.append(f'"{node}" # incoming: {listInbound} ; outgoing: {listOutbound}')
		# add to nodeList (for completion's sake)
		getParent = mc.listRelatives(node, p=True, c=False)[0]
		jointListIndex = len(jointList)-1
		nodeList += f"jointList[{jointListIndex}] # joint - {node}"
		# f'"{node}" # mc.createNode("joint", n={NAME}, p={parentName})'
		nodeListStage2.append(node)
		pass	
	elif thisNodeType == 'ikHandle': # ikHandle, use dedicated command
		# ['ikRPsolver', 'ikSCsolver', 'ikSplineSolver']
		# query start joint
		# query end joint
		stu_ikhSolver = mc.ikHandle(node, query = True, solver=True)
		stu_ikhStartJoint = mc.ikHandle(node, query = True, sj=True)
		stu_ikhEffector   = mc.ikHandle(node, query = True, ee=True) # end effector node, not the joint
		stu_ikhEndJoint   = mc.listConnections(stu_ikhEffector+'.offsetParentMatrix', source = True , destination = False)[0]
		# naming the variables like this because oh boy i don't want to mix up ikHandle the variable and ikHandle the string and ikHandle the node...
		

		# ////////////////////////////////////////////////////////////////////////////////////
		nodeListHolder = []

		nodeListHolder.append( f"ikhSplineOutput_{nodeCounter} = mc.ikHandle(n='{node}', sj='{stu_ikhStartJoint}', ee='{stu_ikhEndJoint}', solver='{stu_ikhSolver}' )" )
		#                        ikhSplineOutput_n             = mc.ikHandle(n='handleName', sj='startJoint',      ee='endJoint',          solver='ikSplineSolver')
		# ikhSplineOutput_n = mc.ikHandle(n='handleName', sj='startJoint', ee='endJoint', solver='ikSplineSolver')
		nodeListHolder.append( f"nodeList[{nodeCounter}   ] = ikhSplineOutput_{nodeCounter}[0] # ikHandle " )
		#                        nodeList[n  ]              = ikhSplineOutput_n[0]             # ikHandle
		# nodeList[n  ] = ikhSplineOutput_n[0] # ikHandle
		nodeListHolder.append( f"nodeList[{nodeCounter +1}] = ikhSplineOutput_{nodeCounter}[1] # effector " )
		#                        nodeList[n+1]              = ikhSplineOutput_n[1]             # effector
		# nodeList[n+1] = ikhSplineOutput_n[1] # effector
		
		addToCounter +=1 # one extra for invoking the ikHandle creator function

		if stu_ikhSolver == 'ikSplineSolver':
			nodeListHolder[0] = f"ikhSplineOutput_{nodeCounter} = mc.ikHandle(n='{node}', sj='{stu_ikhStartJoint}', ee='{stu_ikhEndJoint}', solver='ikSplineSolver', simplifyCurve = False )"
			# just to disable the simplifyCurve flag at the end
			nodeListHolder.append( f"nodeList[{nodeCounter +2}] = ikhSplineOutput_{nodeCounter}[2] # control curve " )
			#                        nodeList[n+2]              = ikhSplineOutput_n[2]             # control curve
			# nodeList[n+2] = ikhSplineOutput_n[2] # control curve
			addToCounter +=1 # one extra for invoking the ikHandle creator function in splineIK mode

		# append commands to nodeList
		nodeList += nodeListHolder
		# append new nodes to stage 2
		nodeListStage2 += #nodeListHolder


	elif thisNodeType in nodeTypeFilterOut: # too complex, require user creation
		nodeList.append(f'nodeList[n] = "{node}" # <- nodetype: {thisNodeType}')
		#                 nodeList[n] = "nodeName" # <- nodetype: 'nodeType'

	else: # normal case
		nodeList.append(f'nodeList[{nodeCounter}] = mc.createNode("{thisNodeType}", n="{node}", skipSelect = True)')
		#                 nodeList[n]             = mc.createNode("nodeType"      , n="nName" , skipSelect = True)
		# nodeList[n] = mc.createNode("nodeType", n="nName", skipSelect = True)

	"""
	REFACTOR: iterate through discovered list of nodes from previous step, due to DAG objects and shape/transform node discovery
	"""

# -------------- attribute checking, creation and setting
nodeListStage2Counter = -1 # lazy indexing
for node in nodeListStage2:
	nodeListStage2Counter += 1

	thisNodeType = mc.nodeType(node)
	"""
	/////////////////////////////////////////////////////////
	mc.setAttr("  transform nodes and extra commands  ")
	mostly default attributes, should come before connectAttr
	/////////////////////////////////////////////////////////
	"""
	if thisNodeType == "transform":
		# ["translate", "rotate", "scale", "wireColorRGB", "outlinerColor"]
		checkAttrList = []
		checkPlugTriples = ["translate", "rotate", "scale", "wireColorRGB", "outlinerColor"]
		checkPlug = ["use,,,"]
		for plug in ["translate", "rotate", "scale", "wireColorRGB", "outlinerColor"]:
			checkAttrList.append(node + f'.{plug}')
		# check for INCOMING connections in list of attributes to check
		
		getNodeIncomingConnections = mc.listConnections(node, )
		for plug in checkAttrList:
			# if attribute in list is not driven upstream
			if plug not in getNodeIncomingConnections:
				# record setAttr command
				setAttrList.append()
				# mc.setAttr({node}, {values}, type=datatype)
		#
		# 
		# //////////////////////////////////////////////////////////////////
		pass
	
	"""
	//////////////////////////////////////////////////////////
	mc.setAttr("  other DG nodes that would need recording  ")
	//////////////////////////////////////////////////////////
	"""
	if thisNodeType == "composeMatrix":
		checkAttrList = []
		checkPlugTriples = ["translate", "rotate", "scale"]
		pass

	"""
	/////////////////////////////////////////
	mc.addAttr("  user-defined attributes  ")
	/////////////////////////////////////////
	"""
	# ============= check for user-defined attributes and write addAttr commands
	checkAttrUD = mc.listAttr(node, userDefined=True)
		# WARNING: returns noneType if list is empty
	if checkAttrUD: # if not None, basically
		for attr in checkAttrUD:
			# query custom attr type
			checkAttrType = mc.attributeQuery(attr, n=node, attributeType = True)
			if checkAttrType in ["float","double","byte","short","long","char"]:
			# query attribute attributes (:shrug:)
				flagString = ""
				# default value
				flagString += f", defaultValue = {mc.attributeQuery(attr, n=node, listDefault = True)[0]}"
				# soft range (attribute sliders)
				if mc.attributeQuery(attr, n=node, softMinExists = True):
					flagString += f", hasSoftMinValue = True, "
					flagString += f", softMinValue = {mc.attributeQuery(attr, n=node, softMin = True)}"
				if mc.attributeQuery(attr, n=node, softMaxExists = True):
					flagString += f", hasSoftMaxValue = True, "
					flagString += f", softMaxValue = {mc.attributeQuery(attr, n=node, softMax = True)}"
				# hard range (hard limits)
				if mc.attributeQuery(attr, n=node, minExists = True):
					flagString += f", hasMinValue = True, "
					flagString += f", minValue = {mc.attributeQuery(attr, n=node, softMin = True)}"
				if mc.attributeQuery(attr, n=node, minExists = True):
					flagString += f", hasMaxValue = True, "
					flagString += f", maxValue = {mc.attributeQuery(attr, n=node, softMin = True)}"
				# hidden?
				holdBool = mc.attributeQuery(attr, n=node, hidden = True)
				flagString += f", hidden = {'True'*holdBool}{'False'*(not holdBool)}"
				# connection settings
				holdBool = mc.attributeQuery(attr, n=node, readable = True)
				flagString += f", readable = {'True'*holdBool}{'False'*(not holdBool)}"
				holdBool = mc.attributeQuery(attr, n=node, writable = True)
				flagString += f", writable = {'True'*holdBool}{'False'*(not holdBool)}"
				# animatable?
				holdBool = mc.attributeQuery(attr, n=node, keyable = True)
				flagString += f", keyable = {'True'*holdBool}{'False'*(not holdBool)}"

				# write attAttr command
				addAttrList.append( f'mc.addAttr("{node}", longName = "{attr}", attributeType = "{checkAttrType}" {flagString})')
			else:
				# complex attribute, manual consideration required for now
					# it should be surmountable within mc., but that's for another time as other utilities come
				# TODO: other types:
					# enum
						# listEnum = True 
					# compound
						# listChildren = True
						# listSiblings = True
				addAttrList.append(f'# "{checkAttrType}" type: {node}.{attr}')
	"""
	/////////////////////////////////////////
	mc.connectAttr("  connection operator  ")
	/////////////////////////////////////////
	"""
	# ============= query outgoing connections
	if thisNodeType in nodeTypeUseCommandsConstraint:
		# constraint node override, connections already made
		nodeCounter += addToCounter
		continue
	if thisNodeType in nodeTypeSkip:
		# other types of nodes to skip, see declaration above
		nodeCounter += addToCounter
		continue
	
	queryConnections = mc.listConnections(node, s=False, c=True,  d=True, p=True )  # -> list : ["shortName_from.attr", "shortName_to.attr", ... , ... ]
		# downstream command
		
	for i in range(int(len(queryConnections)*0.5)): # -> "shortName_from.attr"
		# note: script has been working with shortnames the whole time,
			# ensure node names are all consistently shortNames or longNames (and not a mix of both)
		queryConnectedNode = queryConnections[i+i+1].split('.',1) # <- "shortName_to.attr" <- ["shortName_to","attr"]
		if mc.nodeType(queryConnectedNode[0]) in nodeTypeUseCommandsConstraint:
			# constraint node override:
			# skip outgoing connections to target nodes (EXCEPT if it's target[n].weight)
			if "target[" in queryConnectedNode[1] and ".targetWeight" not in queryConnectedNode[1]:
				# examples to skip:
				#	node.target[n].targetTranslate
				#	node.target[n].targetParentMatrix
				# case to keep:
				#	node.target[n].targetWeight
				continue
		
		# filter out message connections
		if "message" in queryConnections[i+i  ].split(".",1)[1]:
			continue

		# filter out downstream connections that do not connect to selection
		if queryConnectedNode[0] in nodeListStage2: 
			# downstream node is in selection scope, append [input, output] to list
			holdIndex = nodeListStage2.index(queryConnectedNode[0])
				# error case ("thing" is not in list) should not occur because it's filtered earlier

			fromNode = 'f"{' + f"nodeList[{nodeCounter}]" + '}' + f'.{queryConnections[i+i  ].split(".")[1]}"'
			#           f"{      nodeList[      n      ]     }      .                         attribute     "
			# f"{nodeList[n]}.attribute"

			toNode   = 'f"{' + f"nodeList[{holdIndex  }]" + '}' + f'.{queryConnections[i+i+1].split(".")[1]}"'
			#           f"{      nodeList[      n      ]     }      .                         attribute     "			
			# f"{nodeList[n]}.attribute"
						
			# write connectAttr commands
			connectionList.append(f'mc.connectAttr({fromNode}, {toNode}) # {queryConnections[i+i]} -> {queryConnections[i+i+1]}')



	# next node
	nodeCounter += addToCounter



# ======= start write operation

fileEnumerator = [
	"# scripterStu: start print\n",
	f"# date created: UTC {sysTimezone} {saveTime.year:04}.{saveTime.month:02}.{saveTime.day:02} {saveTime.hour:02d}{saveTime.minute:02d}HRS \n",
	"# original file location: \n",
	f"#\t{fileRootPathMa}/{fileNameMa}\n\n",
	"import maya.cmds as mc\n",
	"import maya.api.OpenMaya as om2\n\n",
	"activeSelection = om2.MGlobal.getActiveSelectionList()\n"	
]

fileEnumerator.append("\n# list of joints\n")
fileEnumerator.append(f"jointList = list(range({len(jointList)}))\n")
for printOut in jointList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# create nodes\n")
fileEnumerator.append(f"nodeList = list(range({len(nodeListStage2)}))\n")
for printOut in nodeList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# shape nodes\n")

fileEnumerator.append("\n# custom attributes\n")
for printOut in addAttrList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# connect attributes\n")
for printOut in connectionList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n\n# end of script\n")


outFile.writelines(fileEnumerator)
outFile.close()
print(f"\n# scripterStu: print done: {fileRootPathMa}/{fileNameScriptOut}")