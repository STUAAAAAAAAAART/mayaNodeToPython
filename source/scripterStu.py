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
fileNameScriptOut = f"{fileNameMa}_cmdPrint.{dateString}.py"

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
nodeList = []
constructorList = []
parentList = [] # [ [child from nodeList , parent from file ] , ...]
jointList = []
addAttrList = []
connectionList = []
nodeCounter = 0
for node in checkList:
	addToCounter = 1
	# ============= write createNode / creation commands
	thisNodeType = mc.nodeType(node)
	if thisNodeType in nodeTypeUseCommandsConstraint: # constraints, use dedicated commands
		stu_constraintChild = mc.listConnections(node+'.constraintParentInverseMatrix', source = True , destination = False)[0]
			# this might be a bit too complex to cover all possible cases, probably TODO improve this as needed
		
		# oh my god, every constraint command has exclusive flags
		# also the constrain commands create a user-defined attribute

		# query number of targets
		
		# if many targets: comment and list names
		nodeList.append(f"mc.{thisNodeType}('!!SELECT PARENT HERE','{stu_constraintChild}', n='{node}' , maintainOffset=False)")
		# mc.command(selection) # e.g. [parent,child]
		
		# if one target: fully enumerate exact command and values
			# (especially important for poleVectorConstraint because it's being used so frequently with IK systems)

		nodeList.append(f"mc.{thisNodeType}('!!SELECT PARENT HERE','{stu_constraintChild}', n='{node}' , maintainOffset=False)")
		# mc.command(selection) # e.g. [parent,child]
		pass
	elif thisNodeType in nodeTypeShapeNodes or thisNodeType == "transform":
		"""
		CAUTION: now dealing with DAG paths with relative names and parenting hierachy
		"""
		transformAndShape = [None, None]
		if thisNodeType == "transform":
			transformAndShape[0] = node
			# f'mc.createNode("transform", n="{NAME}"", p="{parentName}") # '
			# f'mc.createNode("{shape}", n="{NAME}"", p="{transformNode}")'
		elif thisNodeType in nodeTypeShapeNodes:
			transformAndShape[1] = node
		# pre-prepare handlers with [transform , shape]
		# end up with mc.create()s for transform and shape separately
		# if thisNode is a shape
			# get transform node now
		# if this transform node has already been processed
			# skip createnode command for the transform

		# get parent transform (selection string index)
		# if transform already exist earlier in the list
			# get name and skip
			# else handle now and pop from list

		# print commands
			# warning: createNode(shape) only returns the name of the shape node, and does not return the transform node,
			# so make the transform node command first so that the script has a point for the transform
		pass
	elif thisNodeType == "joint":
		# script-only: return name of joints
		"""
		normally work would be done upon an existing skinned model with joints
		the exceptions would be with copying driver/utility joints, but those should be scripted separately

		see also the duplicate hierachy script
		"""
		# add to jointList
		# add to nodeList (for completion's sake)
		# f'"{node}" # mc.createNode("joint", n={NAME}, p={parentName})'
		pass	
	elif thisNodeType == 'ikHandle': # ikHandle, use dedicated command
		['ikRPsolver', 'ikSCsolver', 'ikSplineSolver']
		# query start joint
		# query end joint
		stu_ikhSolver = mc.ikHandle(node, query = True, solver=True)
		stu_ikhStartJoint = mc.ikHandle(node, query = True, sj=True)
		stu_ikhEffector   = mc.ikHandle(node, query = True, ee=True) # end effector node, not the joint
		stu_ikhEndJoint   = mc.listConnections(stu_ikhEffector+'.offsetParentMatrix', source = True , destination = False)[0]
		# naming the variables like this because oh boy i don't want to mix up ikHandle the variable and ikHandle the string and ikHandle the node...
		
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

		nodeList += nodeListHolder

	elif thisNodeType in nodeTypeFilterOut: # too complex, require user creation
		nodeList.append(f'nodeList[n] = "{node}" # <- nodetype: {thisNodeType}')
		#                 nodeList[n] = "nodeName" # <- nodetype: 'nodeType'

	else: # normal case
		nodeList.append(f'nodeList[{nodeCounter}] = mc.createNode("{thisNodeType}", n="{node}", skipSelect = True)')
		#                 nodeList[n]             = mc.createNode("nodeType"      , n="nName" , skipSelect = True)
		# nodeList[n] = mc.createNode("nodeType", n="nName", skipSelect = True)
		

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
		if queryConnectedNode[0] in checkList: 
			# downstream node is in selection scope, append [input, output] to list
			holdIndex = checkList.index(queryConnectedNode[0])
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

fileEnumerator.append("\n# create nodes\n")
fileEnumerator.append(f"nodeList = list(range({len(checkList)}))\n")
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