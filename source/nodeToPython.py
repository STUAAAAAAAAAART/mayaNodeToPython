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
	outFile.close()
except:
	import os
	if os.stat(f"{fileRootPathMa}/{fileNameScriptOut}").st_size == 0:
		# open and overwrite, if existing file is 0 bytes
		outFile = open(f"{fileRootPathMa}/{fileNameScriptOut}","w")
		outFile.close()
	else:
		# there is somehow a file made with the same name down to the second, with existing data
		raise FileExistsError(f"File exists and not empty: {fileNameScriptOut}")

# ====== file name ready

"""
============
nodeToPython
============
"""

activeSelection: om2.MSelectionList = om2.MGlobal.getActiveSelectionList()

# detection phase: get all connections strictly within selection

checkList : list = activeSelection.getSelectionStrings() # -> list : ["shortName", ... ]


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
constructorList = []

nodeList = []
nodeListStage2 = [] # in print order, makes referencing them a lot easier here
jointList = []
commandList = [] # for creation commands more complex than a single createNode
constraintList = [] # create constraint nodes AFTER nodeList mc.create()
parentList = [] # [ [child from nodeList , parent from file ] , ...]
addAttrList = []
setAttrList = []
connectionList = []

skipList = [] # for instances like transform nodes where it has already been processed ahread of the list

nurbsCurveDefaultStringCC = "3,1,0,False,3,(0,0,0,1,1,1),6,4,(0,0,0),(0,0,0),(0,0,0),(0,0,0), type='nurbsCurve'"
# the minimum valid nurbsCurve data for mc.curve(replace=True) to work and not crash maya

"""
===================================================================
STAGE 1: evaluate selection and write node creation commands

creation commands composed here and not in a separate initial loop
	because of certain creation commands that create multiple nodes
===================================================================
"""


shapeNodeTypes = ["nurbsCurve", "bezierCurve", "nurbsSurface", "mesh", "locator"]

recheckTransformList=[]
# [[nodeListIndex, parentName], ...]
tfPlaceholderName = "xxxxxxxxxxxxx"

for node in checkList:
	if node in skipList:
		# node found in skipList, possibly processed in advance
		del skipList[skipList.index(node)]
	#	skipList.pop(skipList.index(node)) # remove from skiplist to make searching tiny bit quicker
		continue

	# ============= write createNode / creation commands
	thisNodeType = mc.nodeType(node)
	
	#//////////////////////
	# transform constraints
	#//////////////////////
	# handle creation command in stage 2
	# objects not in list will be given direct string of name instead
	if thisNodeType in nodeTypeUseCommandsConstraint: # constraints, use dedicated commands
		nodeList.append(f"nodeList[{len(nodeListStage2)}] = '{node}' # {thisNodeType}")
		nodeListStage2.append(node) # handoff to stage 2 
		continue

	#/////////////////////////////////////////////////////
	# curve objects, transform node and curve/bezier shapes
	#/////////////////////////////////////////////////////
	isShapeNode = thisNodeType in shapeNodeTypes
	if isShapeNode or thisNodeType == "transform": # nurbsCurve and general transforms
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
			thisNodeShapes = mc.listRelatives(node, s=True, ni=True)
			# if has shapes:
			if thisNodeShapes: # if not None
				thisShapeType = mc.nodeType(thisNodeShapes[0])
				# set transformAndShape[1]
				transformAndShape[1] = thisNodeShapes[0]
				# end up with [[], shape]
			# if no shapes:
			else:
				transformAndShape[0].append(node)
				# end up with [[node], None]

		# if node is curve shapes: current state if not transform: [[], None]
		if isShapeNode:
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
		
		# ++++++++++++++++++++++++++++++++++++++++++++++++++++
		# enumerate first transform
		# skip if node exists (especially if made by splineIK)
		# ++++++++++++++++++++++++++++++++++++++++++++++++++++
		if transformAndShape[0][0] not in nodeListStage2: # if this transform has NOT already been made
			nodeListStage2.append(transformAndShape[0][0]) # first/original transform node
			getParent = mc.listRelatives(transformAndShape[0][0], p=True)
			if getParent:
				recheckTransformList.append([len(nodeListStage2)-1 , getParent[0]])
				getParent = [f'{tfPlaceholderName}', f'parent of shape: {getParent[0]}']
			else:
				getParent = ['',''] # None cast to string is the word 'None' -_-
			nodeList.append(f'nodeList[{len(nodeListStage2)-1}] = mc.createNode("transform",\tn=f"{transformAndShape[0][0]}", {getParent[0]} skipSelect = True) # {getParent[1]}')
			#                 nodeList[n]             = mc.createNode("transform",\tn=f"nName"                    , p="parent"    , skipSelect = True)

		# ++++++++++++++++++++++++++++++++++++++++++++++++++++
		# enumerate shape node
		# skip if node exists (especially if made by splineIK)
		# ++++++++++++++++++++++++++++++++++++++++++++++++++++
		if transformAndShape[1]: # if there is a shape node in this transform
			if transformAndShape[1] not in nodeListStage2: # if shape is NOT already made
				# chained two ifs because no shape == None
				nodeListStage2.append(transformAndShape[1]) # shape node
				shapeNodeListIndex = len(nodeListStage2)-1
				# compose shape node
				shapeCommand = [] # name changed to follow transform name, very little reason to give it a name completely unique from transform
				shapeCommand.append(f'nodeList[{shapeNodeListIndex}] = mc.createNode("{thisShapeType}",\tn=f"{"{"}nodeList[{len(nodeListStage2)-2}]{"}"}Shape", p=nodeList[{len(nodeListStage2)-2}], skipSelect = True) # transform: {transformAndShape[0][0]}')
				#                     nodeList[n]                    = mc.createNode("nurbsCurve"     ,\tn=f"shapeName"             , P="transformName",                   skipSelect = True)
				skipList.append(transformAndShape[1]) # add INPUT SHAPE NODE NAME to skiplist, to check for re-encounters IN CURRENT SCENE
				if thisShapeType in ["nurbsCurve", "bezierCurve"]:
					# ----------------------------------------------------------------------------------------------
					# time for om2.MPlug.getSetAttrCmds()
					getShapeMSL : om2.MSelectionList = om2.MSelectionList().add(transformAndShape[1]+".local")
					getShapePlug :om2.MPlug = getShapeMSL.getPlug(0)
					getShapeMSL.clear()
					del getShapeMSL
					melString = getShapePlug.getSetAttrCmds() # list of line strings, in MEL
					del melString[-1] # don't need the last bit
					getShapeDataType = ""
					# get data type
					if "dataBezierCurve" in melString[0]:
						getShapeDataType = "dataBezierCurve"
					else:
						getShapeDataType = "nurbsCurve"
					del melString[0] # don't need the MEL command itself

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
						
					shapeCommand.append(f'mc.setAttr(nodeList[{shapeNodeListIndex}]+".cc", {buildString}, type = "{getShapeDataType}")')
					#                     mc.setAttr(f"         nodeList[n]+".cc"        ,   {curveData}  , type = "nurbsCurve"        )
					# remember to use the .cc attribute and not the .worldSpace attribute when applying grafted curve data
				else:
					# could be polygon mesh or NURBS surface, skip for now
					# TODO: reconsider for NURBS surface, might have a chance it'd be used as a UV positional control				
					shapeCommand.append("# check maya scene for shape node type, might be polymesh or NURBS surface")
			
				nodeList.append(f"{shapeCommand[0]}\n{shapeCommand[1]}")
			
		# +++++++++++++++++++
		# enumerate instances
		# +++++++++++++++++++
		if len(transformAndShape[0]) > 1: # if there are more than one transform nodes gathered 
			for tf in transformAndShape[0][1:]: #leave out the first one, it's done above
				nodeListStage2.append(tf) # instance of transform
				# make instance command
				nodeList.append(f"nodeList[{len(nodeListStage2)-1}] = mc.instance( nodeList[{nodeListStage2.index(tf)}], n='{tf}', lf=False, st=False) # instance of {transformAndShape[0][0]}")
				#                 mc.instance(             nodelist[n]             , n=NAME  , lf=False, st=False)
				# make reparenting command
					# this step moved to stage 2 to make querying processed nodes more easily
				skipList.append(tf)
		
		# script list admin
			# append all created nodes (except thisNode) into skipList
			# append all created nodes to stage 2 processing list for connection and attribute handling
			# note that transform node should have its own override to get transform attribute data and wireframe and outliner colour states
		pass


	#//////////////////////////////////////////////////////////////////////
	# joints
	#
	# script-only: return name of joints
	#
	# normally work would be done upon an existing skinned model with joints
	# the exceptions would be with copying driver/utility joints,
	#	but those should be scripted separately or created manually
	#
	# see also the duplicate hierachy script
	#//////////////////////////////////////////////////////////////////////
	elif thisNodeType == "joint":

		# annotate joint connection properties for overview; joint connection commands will still be recorded later
		# query joint for any connections
		getConnectionsInbound = mc.listConnections(node, sh=True, s=True, d=False)
		getConnectionsOutbound = mc.listConnections(node, sh=True, s=False, d=True)
		
		grabNode:om2.MSelectionList = om2.MSelectionList()
		listInbound = []
		listOutbound = []
		
		if getConnectionsInbound: # if not None
			for n in getConnectionsInbound:
				if mc.nodeType(n) == "nodeGraphEditorInfo":
					continue
				grabNode.clear()
				grabNode.add(n)
				grabNodeSelectionString = grabNode.getSelectionStrings(0)[0]
				if grabNodeSelectionString in listInbound: # different attribute, but same object/node
					continue # skip
				listInbound.append(grabNodeSelectionString)
		if getConnectionsOutbound: # if not None
			for n in getConnectionsOutbound:
				if mc.nodeType(n) == "nodeGraphEditorInfo":
					continue
				grabNode.clear()
				grabNode.add(n)
				grabNodeSelectionString = grabNode.getSelectionStrings(0)[0]
				if grabNodeSelectionString in listOutbound:
					continue
				listOutbound.append(grabNodeSelectionString)

		nodeListStage2.append(node) # joint
		jointListIndex = len(jointList) # new appended index, which is Nth index +1 == len(currentLength)
			# THIS IS DIFFERENT TO nodeListStage2.append(), objects are appended THEN indexed here,
			# while jointListIndex is indexed BEFORE appending
		# add to jointList
		writeConnectionsToJL = ""
		if getConnectionsInbound:
			writeConnectionsToJL += f"incoming: {listInbound}"
		if getConnectionsOutbound:
			writeConnectionsToJL += f" - outgoing: {listOutbound}"
		if writeConnectionsToJL: # if not empty string ""
			writeConnectionsToJL = "# " + writeConnectionsToJL
		jointList.append(f'jointList[{jointListIndex}] = "{node}" {writeConnectionsToJL}')
		# add to nodeList (for completion's sake)
		getParent = mc.listRelatives(node, p=True, c=False)
		writeParentToJL = ""
		if getParent: # i not None
			writeParentToJL = f"{getParent[0]}"
		nodeList.append(f"nodeList[{len(nodeListStage2)-1}] = jointList[{jointListIndex}] # joint - {node}, parent: {writeParentToJL}")
		# f'"{node}" # mc.createNode("joint", n={NAME}, p={parentName}, skipSelect=True)'
		pass
	
	#////////////////////////////////////////////////
	# ikHandle and ikEffector, plus curve for splineIK
	#
	# mc.ikHandle outputs the following where created:
	# [ikHandle, ikEffector, curve]
	#////////////////////////////////////////////////
	
	elif thisNodeType in ['ikHandle', 'ikEffector']: # ikHandle, use dedicated command
		# solver types: ['ikRPsolver', 'ikSCsolver', 'ikSplineSolver']
		
		handleSolverEffector = [None, None, None]
		startEndJoints = [None, None]

		if thisNodeType == 'ikHandle':
			handleSolverEffector[0] = node
			handleSolverEffector[1] = mc.ikHandle(node, query = True, solver=True)
			handleSolverEffector[2] = mc.ikHandle(node, query = True, ee=True)
			skipList.append(handleSolverEffector[2])
		if thisNodeType == 'ikEffector':
			handleSolverEffector[0] = mc.listConnections(node+'.handlePath', source = False , destination = True)[0]
			# ASSUME ONLY 1 HANDLE PER EFFECTOR. come back to this when an in-field exception has been created
			handleSolverEffector[1] = mc.ikHandle(handleSolverEffector[0], query = True, solver=True)
			handleSolverEffector[2] = node
			skipList.append(handleSolverEffector[0])

		startEndJoints[0] = mc.ikHandle(handleSolverEffector[0], query = True, sj=True)
		startEndJoints[1] = mc.listConnections(handleSolverEffector[2]+'.offsetParentMatrix', source = True , destination = False)[0]

		#/////////////////////////////////
		# joint selection
		# quick check if already processed 
		#/////////////////////////////////

		indexJointsStartEnd = [None,None]
		for i in [0,1]:	
			if startEndJoints[i] in nodeListStage2: # joint already enumerated
				indexJointsStartEnd[i] = nodeListStage2.index(startEndJoints[i])
				# reverse joint index from nodeList back to jointList
				getJointIndex = None
				for j in range(len(jointList)):
					if nodeListStage2[indexJointsStartEnd[i]] in jointList[j]:
						getJointIndex = j
						break
				if f" # IK joint : {handleSolverEffector[0]}" not in jointList[getJointIndex]:
					jointList[getJointIndex] += f" # IK joint : {handleSolverEffector[0]}"
			else: # new joint encountered
				skipList.append(startEndJoints[i]) # if the script encounters this joint again, it'll skip immediately
				nodeListStage2.append(startEndJoints[i])
				indexJointsStartEnd[i] = len(nodeListStage2)-1
				holdText = ["start","end"]
				jointList.append(f"jointList[{len(jointList)}] = '{startEndJoints[i]}' # IK joint {holdText[i]} : {handleSolverEffector[0]}")
				nodeList.append(f"nodeList{indexJointsStartEnd[i]} = jointList[{len(jointList)-1}] # joint - {startEndJoints[i]}")

		ikCommands = []

		stringIfSplineIK = ""
		transformAndShape = [None, None] # for curve, if this IK system is splineIK
		#//////////////////////////////////////
		# mc.ikHandle(    splineIK handler    )
		#//////////////////////////////////////
		if handleSolverEffector[1] == 'ikSplineSolver': # this is splineIK
			# get curve object: transform and shape
			transformAndShape[0] = mc.listConnections(handleSolverEffector[0]+'.inCurve', source = True , destination = False)[0]
			transformAndShape[1] = mc.listConnections(handleSolverEffector[0]+'.inCurve', source = True , destination = False, shapes=True)[0]

			#/////////////////////////////////////////////////
			# joints: get joint chain and worldspace positions
			#/////////////////////////////////////////////////
			# get selection chain between start and end joints
			startEndJointPaths = [None, None]
			startEndJointPaths[0] = mc.ls(startEndJoints[0], long=True)[0]
				# mc.ls() -> ['|joint4']
				# -[0]-> '|joint4'
			startEndJointPaths[1] = mc.ls(startEndJoints[1], long=True)[0]
				# mc.ls() -> ['|joint4|joint5|joint6|joint7|joint8']
				# -[0]-> '|joint4|joint5|joint6|joint7|joint8'
			startEndJointPaths[1] = startEndJointPaths[1].replace(startEndJointPaths[0], '', 1)
				# [0] '|joint4' ; [1] '|joint5|joint6|joint7|joint8'
			startEndJointPaths[1] = startEndJointPaths[1].split('|')[1:]
				# ['', 'joint5', 'joint6', 'joint7', 'joint8'][1:]
			
			jointAsEPs = []
			# add EPs in reverse order (it's easier to trim from the back)
			for i in range(len(startEndJointPaths[1])): 
				thisJoint = f'{startEndJointPaths[0]}|'
				for j in startEndJointPaths[1][:(len(startEndJointPaths[1])-i)]:
					thisJoint += f'|{j}'
				jointAsEPs.insert(0, mc.xform(thisJoint, q=True, ws=True, t=True))
			# add EP for the start joint
			jointAsEPs.insert(0, mc.xform(startEndJointPaths[0], q=True, ws=True, t=True))
			
			# multiply EPs by worldInverse of curve transform
			matA = mc.getAttr(transformAndShape[1]+".worldInverseMatrix")
			transformedEP = []
			for ep in jointAsEPs:
				matB = list(ep)
				matB.append(1.0)
				matMult = []
				matMult.append( matA[ 0]*matB[0] + matA[ 4]*matB[1] + matA[ 8]*matB[2] + matA[12]*matB[3] )
				matMult.append( matA[ 1]*matB[0] + matA[ 5]*matB[1] + matA[ 9]*matB[2] + matA[13]*matB[3] )
				matMult.append( matA[ 2]*matB[0] + matA[ 6]*matB[1] + matA[10]*matB[2] + matA[14]*matB[3] )
				matMult.append( matA[ 3]         + matA[ 7]         + matA[11]         + matA[15]         )
				
				# normalise components relative to W and remove W
				for i in range(len(matMult)-1):
					matMult[i] = matMult[i] / matMult[-1]
				
				transformedEP.append( tuple(matMult[:-1].copy()) )
				
			#//////////////////////////////////
			# ikHandle : curve handler override
			#//////////////////////////////////
			getCurveTransFormShapeIndex = [None,None]
			# if curve shape already exist (implies transform node also exists)
			if transformAndShape[0] in nodeListStage2:
				# get nodeList index of curveShape and carry on to ikHandle command composer
				getCurveTransFormShapeIndex[0] = nodeListStage2.index(transformAndShape[0]) # transform for ikHandle
				getCurveTransFormShapeIndex[1] = nodeListStage2.index(transformAndShape[1]) # shape for rebuilding
				
				# override detected curve shape with placeholder
				makeNode = nodeList[getCurveTransFormShapeIndex[1]].split('\n') # see curve handler
				makeNode[1] = f"mc.setAttr(nodeList[{getCurveTransFormShapeIndex[1]}]+'.cc', {nurbsCurveDefaultStringCC}) # splineIK placeholder"
				nodeList[getCurveTransFormShapeIndex[1]] = f'{makeNode[0]}\n{makeNode[1]}'
				pass
			else:
				# enumerate placeholder curve creation commands
				nodeListStage2.append(transformAndShape[0]) # transform
				getCurveTransFormShapeIndex[0] = len(nodeListStage2)-1
				nodeList.append(f"nodeList[{getCurveTransFormShapeIndex[0]}] = mc.createNode('transform', n='{transformAndShape[0]}')")
				
				nodeListStage2.append(transformAndShape[1]) # curveShape
				getCurveTransFormShapeIndex[1] = len(nodeListStage2)-1
				makeNode = []
				makeNode.append(f"nodeList[{getCurveTransFormShapeIndex[1]}] = mc.createNode('nurbsCurve', n='{transformAndShape[1]}', p=nodeList[{getCurveTransFormShapeIndex[0]}])")
				makeNode.append(f"mc.setAttr(nodeList[{getCurveTransFormShapeIndex[1]}]+'.cc', {nurbsCurveDefaultStringCC}) # splineIK placeholder")
				nodeList.append(f"{makeNode[0]}\n{makeNode[1]}")
				pass
			stringIfSplineIK = f", ccv=False, curve=nodeList[{getCurveTransFormShapeIndex[0]}]"
			
			ikCommands.append(f"mc.curve(nodeList[{getCurveTransFormShapeIndex[1]}],ep={jointAsEPs}, r=True) # default, absolute to world")
			ikCommands.append(f"# mc.curve(nodeList[{getCurveTransFormShapeIndex[1]}],ep={transformedEP}, r=True) # local to curve object transform at time of query")
			pass
			# pass to ikHandle command composer

		#///////////////////////
		# write ikHandle Command
		#///////////////////////
		indexHandleEffector = [None,None]
		nodeListStage2.append(handleSolverEffector[0]) # ikHandle
		indexHandleEffector[0] = len(nodeListStage2)-1
		nodeList.append(f"nodeList[{indexHandleEffector[0]}] = '{handleSolverEffector[0]}' # ikhandle, {handleSolverEffector[1]}")
		nodeListStage2.append(handleSolverEffector[2]) # ikEffector
		indexHandleEffector[1] = len(nodeListStage2)-1
		nodeList.append(f"nodeList[{indexHandleEffector[1]}] = '{handleSolverEffector[2]}' # ikEffector")

		# ---------------------------
		# the stuTempEffector thing: just a temporary holdover to catch the effector node and rename it to its original or indended name
		# assigning it back to the nodeList item in case of name collisions (mc.rename() will give an alternative name as fallback)
		makeCommandIKH = f"nodeList[{indexHandleEffector[0]}], stuTempEffector = "
		#                  nodeList[A]                       , nodelist[B] = 
		makeCommandIKH += f"mc.ikHandle(n=nodeList[{indexHandleEffector[0]}], sj=nodeList[{indexJointsStartEnd[0]}], ee=nodeList[{indexJointsStartEnd[1]}], solver='{handleSolverEffector[1]}'{stringIfSplineIK})"
		#                   mc.ikHandle(n=nodeList[       nameHandle       ], sj=nodeList[       startJoint       ], ee=nodeList[        endJoint        ], solver='        ikhSolver        ', ccv=False, curve = ikCurve)
		makeCommandIKH += f"\n# ikHandle: {handleSolverEffector[0]} ; start/end joints: {startEndJoints} ; ikSolver: {handleSolverEffector[1]}"
		if stringIfSplineIK:
			makeCommandIKH += f" ; splineIK curve: {transformAndShape[0]}"
		makeCommandIKH += f"\nnodeList[{indexHandleEffector[1]}] = mc.rename(stuTempEffector, nodeList[{indexHandleEffector[1]}]) # ikEffector node - {handleSolverEffector[2]}\n"


		ikCommands.append(makeCommandIKH)
		# nodeList[A], tempEffector = mc.ikHandle(n=nameHandle, sj=startJoint, ee=endJoint, solver=ikhSolver, ccv=False, curve = ikCurve)
		# nodeList[B] = mc.rename(tempEffector, nodeList[B]) # to maintain original name of effector 
		# ---------------------------
			# i am not writing the entire command on one line

		commandList += ikCommands # merge composed IK commands to commandList

	#////////////////////////////////////////////////////
	# other complex nodes with no handler (at the moment) 
	#////////////////////////////////////////////////////

	elif thisNodeType in nodeTypeFilterOut: # too complex, require user creation (see declaration above)
		nodeListStage2.append(node)
		nodeList.append(f'nodeList[n] = "{node}" # <- nodetype: {thisNodeType}')
		#                 nodeList[n] = "nodeName" # <- nodetype: 'nodeType'

	#///////////////////////////////////////////////
	# simple nodes that can be covered by createNode
	#///////////////////////////////////////////////

	else: # normal case
		nodeListStage2.append(node)
		nodeList.append(f'nodeList[{len(nodeListStage2)-1}] = mc.createNode("{thisNodeType}",\tn=f"{node}", skipSelect = True)')
		#                 nodeList[n]                       = mc.createNode("nodeType"      ,\tn=f"nName" , skipSelect = True)
		# nodeList[n] = mc.createNode("nodeType",\tn=f"nName", skipSelect = True)

# find and replace all the parents of the transform nodes
for i in range(len(recheckTransformList)):
	if recheckTransformList[i][1] in nodeListStage2:
		parentIndex = nodeListStage2.index(recheckTransformList[i][1])
		nodeList[recheckTransformList[i][0]] = nodeList[recheckTransformList[i][0]].replace(tfPlaceholderName,f"p=nodeList[{parentIndex}], ")
	else:
		nodeList[recheckTransformList[i][0]] = nodeList[recheckTransformList[i][0]].replace(tfPlaceholderName,f"p='{recheckTransformList[i][1]}', ")


"""
-----------
END STAGE 1
-----------
"""

# -------------- attribute checking, creation and setting
# WARNING WITH TUPLES: (value) IS value, (value,) IS TUPLE CONTAINING value
nodeCheckDict = {

'transform': [ # transform node
	('offsetParentMatrix',),
	('rotate', 'rotateX', 'rotateY', 'rotateZ'),
	('scale', 'scaleX', 'scaleY', 'scaleZ'),
	('translate', 'translateX', 'translateY', 'translateZ'),
	('maxRotLimit', 'maxRotXLimit', 'maxRotYLimit', 'maxRotZLimit'),
	('maxRotLimitEnable', 'maxRotXLimitEnable', 'maxRotYLimitEnable', 'maxRotZLimitEnable'),
	('maxScaleLimit', 'maxScaleXLimit', 'maxScaleYLimit', 'maxScaleZLimit'),
	('maxScaleLimitEnable', 'maxScaleXLimitEnable', 'maxScaleYLimitEnable', 'maxScaleZLimitEnable'),
	('maxTransLimit', 'maxTransXLimit', 'maxTransYLimit', 'maxTransZLimit'),
	('maxTransLimitEnable', 'maxTransXLimitEnable', 'maxTransYLimitEnable', 'maxTransZLimitEnable'),
	('minRotLimit', 'minRotXLimit', 'minRotYLimit', 'minRotZLimit'),
	('minRotLimitEnable', 'minRotXLimitEnable', 'minRotYLimitEnable', 'minRotZLimitEnable'),
	('minScaleLimit', 'minScaleXLimit', 'minScaleYLimit', 'minScaleZLimit'),
	('minScaleLimitEnable', 'minScaleXLimitEnable', 'minScaleYLimitEnable', 'minScaleZLimitEnable'),
	('minTransLimit', 'minTransXLimit', 'minTransYLimit', 'minTransZLimit'),
	('minTransLimitEnable', 'minTransXLimitEnable', 'minTransYLimitEnable', 'minTransZLimitEnable'),
	('useObjectColor',), # maya does not update the scene when the colour is being set/connected through the attribute and not a command call...
	#('objectColor',),
	#('objectColorRGB', 'objectColorR', 'objectColorG', 'objectColorB'),
	#('wireColorRGB',),
	# ('wireColorRGB', 'wireColorR', 'wireColorG', 'wireColorB'),
	('useOutlinerColor',),
	('outlinerColor', 'outlinerColorR', 'outlinerColorG', 'outlinerColorB')
],

'floatCondition' : [ # floatCondition, a pre-2024 workaround for inverting a boolean
	('floatA',),
	('floatB',)
],

'composeMatrix' : [ # composeMatrix node
	('inputQuat', 'inputQuatX', 'inputQuatY', 'inputQuatZ', 'inputQuatW'),
	('inputRotate', 'inputRotateX', 'inputRotateY', 'inputRotateZ'),
	('inputRotateOrder',),
	('inputScale', 'inputScaleX', 'inputScaleY', 'inputScaleZ'),
	('inputShear', 'inputShearX', 'inputShearY', 'inputShearZ'),
	('inputTranslate', 'inputTranslateX', 'inputTranslateY', 'inputTranslateZ'),
	('useEulerRotation',)
],

'fourByFourMatrix' : [ # fourByFourMatrix
	('in00',),('in01',),('in02',),('in03',),
	('in10',),('in11',),('in12',),('in13',),
	('in20',),('in21',),('in22',),('in23',),
	('in30',),('in31',),('in32',),('in33',),
],

'plusMinusAverage' : [ # plusMinusAverage
	# ADDITIONAL SUBROUTINE FOR input1D input2D input3D IN SCRIPT ITSELF
	('operation',)
],

'multiplyDivide' : [ # multiplyDivide
	('operation',)
],

'inverseMatrix' : [ # inverseMatrix
	('inputMatrix',),
],

'blendMatrix' : [ # blendMatrix, empty set to force it to check matrix members
],

'pickMatrix' : [ # pickMatrix
	('useTranslate',),
	('useRotate',),
	('useScale',),
	('useShear',)
],

'aimMatrix' : [ # aimMatrix
	('primaryMode',),
	('primaryInputAxis', 'primaryInputAxisX', 'primaryInputAxisY', 'primaryInputAxisZ'), # Forward Vector
	('primaryTargetVector', 'primaryTargetVectorX', 'primaryTargetVectorY', 'primaryTargetVectorZ'), # if set to Align
	('secondaryMode',),
	('secondaryInputAxis', 'secondaryInputAxisX', 'secondaryInputAxisY', 'secondaryInputAxisZ'), # Upward Vector
	('secondaryTargetVector', 'secondaryTargetVectorX', 'secondaryTargetVectorY', 'secondaryTargetVectorZ') # if set to Align
],

'curveFromSurfaceIso' : [ # curveFromSurfaceIso
	('isoparmValue',),
	('isoparmDirection',), # U or V direction
],

}





checkIKH = [ # ikHandle target, inherits attributes from transform node
	('poleVector', 'poleVectorX', 'poleVectorY', 'poleVectorZ'),
	('snapEnable',),
	('stickiness',),
	('twist',)
]

checkSplineIK = [ # splineIK, inherits ikHandle, inherits transform
	('offset',),
	('roll',),
]

checkSplineAdvancedIK = [ # splineIK attributes for advanced twist controls
	('dTwistControlEnable',),
	('d',)
]

# transform node: check if these attributes are locked
lockList = ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ"]


"""
the ikSplineSolver in the ikHandle has an advanced twist mode (and corresponding sets of control attributes)
	these serve to aim the ends of the spline joint chain to two corresponding targets (somewhat like a pole vector)
	and spread the twist values along the joint chain.
TODO: this script currently does not cover this, but it's probably worth including a handler for it later

a different ideal would be to have two splines and aim the result of the first spline (that's driving the joint chain)
	to the target points along the second spline
this method would be more fitting in a case like a snake climbing a tree (where it curves in multiple c-shapes
	grabbing both sides of the tree), but would result in a very complex node network

both methods aim to solve the problem of needing an up vector along a spline (a spline alone does not have an "upward-ness") 
"""

"""
==========================================
STAGE 2: attributes and secondary commands
==========================================
"""

nodeListPrintIndex = -1 # lazy indexing
for node in nodeListStage2:
	nodeListPrintIndex += 1 # index in nodeList output

	thisNodeType = mc.nodeType(node)

	if thisNodeType in nodeTypeUseCommandsConstraint:
		# the creation command handler for constraints
		
		"""
		get constraint type
		"""
		constraintType = thisNodeType # thankfully nodeType of constraint == maya command for constraint
		
		# mc.poleVectorConstraint(poleVector, ikHandle)
		# mc.{constraintType}(parent, parent... , child, mo=False)
		# mc.aimConstraint(parent, parent... , child, mo=False, worldUpType="type", worldUpObject=upObj)
			# mc.connectAttr(nodeList[n].worldMatrix, constraint.worldUpMatrix, force=True)
			# mc.connectAttr(uncheckedNode.worldMatrix, constraint.worldUpMatrix, force=True) # node not in selection during runtime
			# mc.connectAttr(nodeList[n].attr, constraint.worldUpVector, force=True)
			# mc.connectAttr(uncheckedNode.attr, constraint.worldUpVector, force=True) # node not in selection during runtime
		#	maintainOffset: just set them to False for now, let the user edit this after editing
		
		thisConstraintCommand = ""
		setMaintainOffset = False
		setSkip = []
		"""
		getting constrained/driven object
		"""
		getDriven = mc.listConnections(node+'.constraintParentInverseMatrix', s=True, d=False)[0]
		if getDriven in nodeListStage2:
			getDriven = f"nodeList[{nodeListStage2.index(getDriven)}]"
		else:
			getDriven = f"'{getDriven}'"

		"""
		getting Target object(s)
		"""
		# command-agnostic way to query target list
		getTargetIndex = mc.getAttr(node+'.target', mi=True) # multiple instances
		# WARNING: if there is a plug instance, but no connections going into this, getAttr WILL STILL RETURN THIS INDEX
		# also like why is there an empty instance in a constraint node
		#	i'm opting for this script to not save the user from this situation and just ignore the gaps
		#	i mean like maya really does not want users to mess with the order going into constraint nodes, so like off-roading with constraints doesn't sound like a good idea
		getTargets = [] # nodeList strings
		getTargetWeightConnection = []		
		for i in getTargetIndex:
			# get targets (does not have to be in exact index, so long as it's in order)
			queryTargets = mc.listConnections(f"{node}.target[{i}].targetParentMatrix", source=True, destination=False)
			if queryTargets == None:
				continue # gap case, skip
			getTargets.append(queryTargets[0])

			targetParentsList = []
			for t in getTargets:
				# check if target is in nodeList
				if t in nodeListStage2:
					# use nodeList Index
					targetParentsList.append(f"nodeList[{nodeListStage2.index(t)}]")
				else:
					# use direct name.....
					targetParentsList.append(f"'{t}'")

			"""
			connectAttr( targetWeight CONNECTION )
			writing the connectAttr command here because the main subroutine in stage 2 is going to skip constraint nodes
			"""
			queryTargetWeight = mc.listConnections(f"{node}.target[{i}].targetWeight", s=True, d=False, c=True, p=True)

			# check if targetWeight is connected to command-premade user-defined attribute on self
			if queryTargetWeight[0].split('.', 1)[0] == queryTargetWeight[1].split('.', 1)[0]: # if true, check where THAT is being connected to
				# if this connects to itself AGAIN, i am not saving the user from themselves (even if it means that'd be me)
				# reminder that this script will not be making addAttr commands for constraint nodes
				queryTargetWeight = mc.listConnections(queryTargetWeight[1], s=True, d=False, plugs=True)
				if queryTargetWeight: # if not none
					getTargetWeightConnection.append( queryTargetWeight[0] )
				else:
					getTargetWeightConnection.append(None)
			else: # it's connected to something else directly, get connection
				getTargetWeightConnection.append( queryTargetWeight[1] )
			
			# if targetWeight is connected:
			if getTargetWeightConnection[-1]: # if not None, in which case ignore and let it default
				getWeightConnectionRight = f"nodeList[{nodeListPrintIndex}]+'.target[{len(getTargetWeightConnection)-1}.targetWeight]'"
				if getTargetWeightConnection[-1].split('.')[0] in nodeListStage2: # if node is in nodelist
					# compose connectAttr command
					getWeightConnectionLeft = nodeListStage2.index(getTargetWeightConnection[-1].split('.')[0])
					getWeightConnectionLeft = f"nodeList[{getWeightConnectionLeft}]+'.{getTargetWeightConnection[-1].split('.')[1]}'"

					connectionList.append( f"mc.connectAttr({getWeightConnectionLeft}, {getWeightConnectionRight}, force=True)" )
					pass
				else:
					# compose setAttr command, but comment-out
					connectionList.append( f"# mc.connectAttr('{getTargetWeightConnection[-1]}', {getWeightConnectionRight}, force=True)" )
					pass
	
			pass	
		"""
		aimConstraint handler
		"""
		setAimConstraint = ""
		getAimObject = ""
		if constraintType == "aimConstraint":
			getAimType = mc.getAttr(node+".worldUpType") # CAUTION: ENUM. get as integer, as maya has different enum names depending on language
			# fortunately mc.aimConstraint(worldUpType=) allows integers (enum flags allows integer indices)
			setAimConstraint = f", worldUpType={getAimType}"

			getAimObject = mc.listConnections(node+".worldUpMatrix", s=True, d=False)
			if getAimObject: # if not None
				# check if object in list
				getAimObject = getAimObject[0]
				if getAimObject in nodeListStage2:
					setAimConstraint += f"worldUpObject=nodeList[{nodeListStage2.index(getAimObject)}]"
				else:
					setAimConstraint += f", worldUpObject='{getAimObject}'"
			
			getAimVectorConnection = mc.listConnections(node+".worldUpVector", s=True, d=False, c=True)
			"""
			connectAttr( AIM VECTOR CONNECTION )
			"""
			if getAimVectorConnection: # if not None
				# check if object in list
				# ["object.attr"]
				getAimVectorConnection: str = getAimVectorConnection[0] # "object.attr"
				aimVectorConnectionRight = f"nodeList[{nodeListPrintIndex}]+'.worldUpVector'"
				if getAimVectorConnection.split('.')[0] in nodeListStage2:
					aimVectorConnectionLeft = getAimVectorConnection[0].split('.') # ["object","attr"] 
					aimVectorConnectionLeft[0] = nodeListStage2.index(getAimVectorConnection[0]) # [nodeList[n],"attr"]
					aimVectorConnectionLeft = f"{aimVectorConnectionLeft[0]}.{aimVectorConnectionLeft[1]}"
					connectionList.append( f"mc.connectAttr('{aimVectorConnectionLeft}', {aimVectorConnectionRight}, force=True) # aim worldUpVector: {getAimVectorConnection}" )
				else:
					# just print the name...
					connectionList.append( f"mc.connectAttr('{getAimVectorConnection}', {aimVectorConnectionRight}, force=True)" )
			pass

		commandObjects = ""
		for i in targetParentsList:
			commandObjects += f"{i}, " # "parent, parent, parent..."
		commandObjects += getDriven # "child,"
		mainConstraintCommand = f"nodeList[{nodeListPrintIndex}] = mc.{constraintType}({commandObjects}, n=nodeList[{nodeListPrintIndex}], mo={setMaintainOffset} {setAimConstraint}) # {node}"
								# nodeList[          n         ] = mc.aimConstraint(    parent, child,   n=nodeList[          n         ], mo=False, worldUpType=2, wouldUpObject="object")
								# nodeList[          n         ] = mc.pointConstraint(  parent, child,   n=nodeList[          n         ], mo=False   )
								# nodeList[       n       ] = mc.poleVectorConstraint(poleVector, ikHandle, n=nodeList[       n         ], mo=False   )
		if getAimObject:
			mainConstraintCommand += f"; aim worldUpObject {getAimObject}"

		constraintList.append(mainConstraintCommand + thisConstraintCommand) # entire group of constraint command plus relevant setattrs

		continue # do not use other handlers, go to next in stage 2 list

	"""
	////////////////////////////////////////////////////////
	mc.parent("  reparenting objects on the DAG hierachy  ")
	////////////////////////////////////////////////////////
	"""
	if thisNodeType in ["transform", "ikHandle"]:
		# get parent
		getParent = mc.listRelatives(node, p=True, c=False )
		if getParent: # listRelatives has [something] and did not return None
			getParent = getParent[0]
			printParent = getParent
			if getParent in nodeListStage2:
				getParent = f"nodeList[{nodeListStage2.index(getParent)}]" # f'nodeList[n]'
			else:
				getParent = f"'{getParent}'" # 'parentNode'
			# compose parenting command
			#                   mc.parent(            "child"              ,  "parent"      )
			parentList.append(f"mc.parent(nodeList[{nodeListPrintIndex}], {getParent}, r=True ) # child: {node} -> parent: {printParent} " )
			#                   mc.parent(            "child"              , f'nodeList[n]' )

	"""
	//////////////////////////////////////////////////////////////
	mc.setAttr("  recording transform nodes and extra commands  ")
	mostly default attributes, should come before connectAttr
	//////////////////////////////////////////////////////////////
	"""
	if thisNodeType in nodeCheckDict.keys():
		"""
		end up with setAttr commands for attributes not connected and is not default value
		
		for compound attributes: if main attribute or all of the subattributes are connected, skip
		if any of the subattributes are not connected, and are not in their default attributes, just write the setAttr for the entire main attribute
		"""

		# check for INCOMING connections in list of attributes to check
		getNodeIncomingConnections = mc.listConnections(node, s=True, d=False, p=True, c=True)
		# [thisNode.attr, otherNode.attr, ... ]
		
		if getNodeIncomingConnections: # if there are [connecions] and listConnections did not return None
		# trim list to just this node
			for i in range(int(len(getNodeIncomingConnections) * 0.5)): # definitely always even
				del getNodeIncomingConnections[i+1]
			# trim strings to just the attribute that has an incoming connection
			for i in range(len(getNodeIncomingConnections)):
				getNodeIncomingConnections[i] = getNodeIncomingConnections[i].split('.', 1)[-1] # split the first dot only, for plusMinusAverage node ( plusMinusAverage.input2D[n].inputX )
			# [attr, attr, attr, ...]
		else: # listConnections returned None
			getNodeIncomingConnections = [] # just to make the following work

		printSetAttrList = []

		checkAttrList = None # flush
		# load check attribute list
		checkAttrList = list(nodeCheckDict[thisNodeType]).copy()

		# add checks for each plusMinusAverage value
		if thisNodeType == "plusMinusAverage":
			pmaList1D = mc.listAttr(node+".input1D", m=True) # 'input1D[0]'
			pmaList2D = mc.listAttr(node+".input2D", m=True) # 'input2D[0]', 'input2D[0].input2Dx', 'input2D[0].input2Dy'
			pmaList3D = mc.listAttr(node+".input3D", m=True) # 'input3D[0]', 'input3D[0].input3Dx', 'input3D[0].input3Dy', 'input3D[0].input3Dz'
			
			if pmaList1D: # if not None
				for attr in pmaList1D:
					checkAttrList.append((attr,))
			if pmaList2D: # if not None
				len2D = int(len(pmaList2D) /3.0)
				for i in range(len2D):
					checkAttrList.append((pmaList2D[i*3],pmaList2D[i*3+1],pmaList2D[i*3+2]))
			if pmaList3D: # if not None
				len3D = int(len(pmaList3D) * 0.25)
				for i in range(len3D):
					checkAttrList.append((pmaList3D[i*4],pmaList3D[i*4+1],pmaList3D[i*4+2],pmaList3D[i*4+3]))
			pass

		# add checks for each blendMatrix picker value
		if thisNodeType == "blendMatrix":
			bmxList = mc.listAttr(node+".target", m=True)
			# contains a run of the following 8 for each active item in list:
			# target[n], 'target[n].targetMatrix', 'target[n].useMatrix', 'target[n].weight', 'target[n].useScale', 'target[n].useTranslate', 'target[n].useShear', 'target[n].useRotate'
			# skip the first, add the other attributes to checklist
			if bmxList: # if not None
				bmxTargets = int(len(bmxList) * 0.125)
				for i in range(bmxTargets):
					for j in range(7):
						checkAttrList.append((bmxList[(i*8) + (j+1)],))
			pass

		# for each set of attributes in checker list
		makeSetAttrSublist = []
		removeMainSetAttr = False
		for attrSet in checkAttrList:
			if attrSet[0] == "useObjectColor": # hard override to handle wireframe colour, mc.color must be used
				wireIsColoured = mc.getAttr(f"{node}.{attrSet[0]}")
				if wireIsColoured == 0:
					# default enum value changes nothing
					continue
				elif wireIsColoured == 1: # colour index
					setAttrList.append(f"mc.color(f'{'{'}nodeList[{nodeListStage2.index(node)}]{'}'}', userDefined={mc.getAttr(f'{node}.objectColor')}) # {node} - wireframe colour")
					#                    mc.color(       nodelist[n]                                 , userDefined=7                                  )
				elif wireIsColoured == 2: # RGB value
					setAttrList.append(f"mc.color(f'{'{'}nodeList[{nodeListStage2.index(node)}]{'}'}', rgb={mc.getAttr(f'{node}.wireColorRGB')[0]}) # {node} - wireframe colour")
					#                    mc.color(       nodelist[n]                                 , rgb=(r,g,b)                            )
				continue # done - outliner colour should be handled by default case that follows:

			if attrSet[0] in getNodeIncomingConnections: # if main attr has incoming connections
				# main attribute is connected upstream, skip
				continue
			elif len(attrSet) == 1: # attribute has no subattributes
				pass # do not skip, let script check for default value
			else: # check if all subattributes are connected
				allSubAttrConnected = True
				for attr in attrSet[1:]:
					allSubAttrConnected = allSubAttrConnected and (attr in getNodeIncomingConnections)
				if allSubAttrConnected:
					continue
			
			writeAttrList = []
			# check if main attr has any changes to its value
			mainAttrMSL : om2.MSelectionList = om2.MSelectionList().add(f"{node}.{attrSet[0]}")
			mainAttrIsDefault = mainAttrMSL.getPlug(0).isDefaultValue()
			mainAttrMSL.clear()
			del mainAttrMSL # cleanup....
			if not mainAttrIsDefault: # if not default values
				writeAttrList.append(attrSet[0]) # "attr"
				pass

			# one of two states to end up in:
			# - no connections, has changes
				# mc.setAttr the entire attribute
			# - has subattributes, some connections, unconnected attrs has changes
				# mc.setAttr individual attributes

			isSubAttrMode = False
			if len(attrSet) > 1: # if this attr has subattributes
				subAttrCounter = 0 # count number of setAttr commands being made for subAttrs
				subAttrMSL : om2.MSelectionList = om2.MSelectionList()
				
				for attribute in attrSet[1:]:
					# check if subattribute is default value
					subAttrMSL.add(f"{node}.{attribute}")
					# check if subattribute has no incoming connection
					# AND it's not a default value
					if (attribute not in getNodeIncomingConnections) and (not subAttrMSL.getPlug(0).isDefaultValue()):
						writeAttrList.append(attribute) # "subAttr"
						subAttrCounter += 1
						isSubAttrMode = True
					
					subAttrMSL.clear()
				del subAttrMSL # cleanup....
				
				if writeAttrList == []:
					# all subattributes are connected, or all subattributes are default
					continue
				
				if subAttrCounter == (len(attrSet) -1) : # if there are as many setAttrs as there are subAttrs
					isSubAttrMode = False
					del writeAttrList[1:] # dump subAttrs and just write main Attr

			if isSubAttrMode: # if there are still subAttrs that need writing
				del writeAttrList[0] # dump mainAttr, split command to few

			# compose setAttr commands
			for attr in writeAttrList:
				getAttrType = ""
				try:
					getAttrType = mc.getAttr(f'{node}.{attr}', type=True)
				except: # got weird multi-attribute: workarounds for long attributes
					if thisNodeType == "plusMinusAverage": # just to be sure
						# 'input2D[n]' -> ['input2D', 'n]'] -> 'input2D'
						pmaAttr = attr.split("[")[0]
						pmaAttr = attr.split(".")[-1]
						getAttrType = mc.getAttr(f'{node}.{pmaAttr}', type=True)
				getAttrValues = mc.getAttr(f'{node}.{attr}')
				attrFlatString = f"{getAttrValues}"
				if type(getAttrValues) == type(list()):
					# compound attribute, expand list
					# "[(1.0, 2.0, 3.0)]"
					attrFlatString = attrFlatString[1:-1]
					if getAttrType in ["double2", "double3", "float2", "float3", "long2", "long3", "short2", "short3"]:
						# mc.getAttr apparently returns double3 as a single tuple, within a list-type return??
						attrFlatString = attrFlatString[1:-1]
					# "1.0, 0.0, 0.0"
				# start composing command	
				typeFlagString = ""
				if getAttrType != "bool":
					typeFlagString = f", type='{getAttrType}'"
				setAttrList.append(f"mc.setAttr(f'{'{'}nodeList[{nodeListStage2.index(node)}]{'}'}.{attr}', {attrFlatString} {typeFlagString}) # {node}.{attr}")
				#                               f'  {  nodeList[             {n}            ]  }  .  attribute '
				#                    mc.setAttr(                       f'{nodelist[n]}.attribute'         ,  1, 2, 3, 4, 5,   type='dataType'     )
	# tranform nodes: check lock status
	if thisNodeType == "transform":
		for attr in lockList:
			if mc.getAttr(F"{node}.{attr}", lock=True):
				# flags separated, maya history queue does not like having this in one go
				setAttrList.append(f"mc.setAttr(f'{'{'}nodeList[{nodeListStage2.index(node)}]{'}'}.{attr}', lock=True) # {node}.{attr}")
				setAttrList.append(f"mc.setAttr(f'{'{'}nodeList[{nodeListStage2.index(node)}]{'}'}.{attr}', keyable=False, channelBox=False) # {node}.{attr}")
				#                    mc.setAttr(f'  {nodelist[n]}  .attribute' , lock=True)
				
	pass

	"""
	/////////////////////////////////////////
	mc.addAttr("  user-defined attributes  ")

	mc.setAttr("  recording values of dynamic attributes  ")
	this is usually manual values, so set them here
	/////////////////////////////////////////
	"""
	# ============= check for user-defined attributes and write addAttr commands
	udList = mc.listAttr(node, userDefined=True)
		# WARNING: returns noneType if list is empty
	if udList: # if not None, just to skip this entire block if there are none
		printAddAttrs = f"# Dynamic Attributes for nodeList[{nodeListPrintIndex}] : {node} ========================== "
		for attr in udList:
			udFlags = ""
			getAttrType = mc.attributeQuery(attr, n=node, at=True)

			# has custom shortName
			getShortName = mc.attributeQuery(attr, n=node, sn=True)
			if attr != getShortName: # shortName defaults to longName if not set
				udFlags += f", sn='{getShortName}'"
			# has custom Nice name
				# skipping this for now. checking this will involve replicating maya's Nice Name syntax

			# parent of main Attr
			getParent = mc.attributeQuery(attr, n=node, lp=True)
			if getParent:
				udFlags += f", p='{getParent[0]}'"

			# float3: is this attribute a colour representation?
			if mc.attributeQuery(attr, n=node, usedAsColor=True):
				udFlags += ", uac=True"
			elif getAttrType == "float3":
				udFlags += ", uac=False" # leave the flag in there just as a reminder
			# main compound attribute flag
			if getAttrType == "compound":
				udFlags += f", nc='{mc.attributeQuery(attr, n=node, nc=True)[0]}'"
			# enum attribute: enum value string flag
			if getAttrType == "enum":
				udFlags += f", en='{mc.attributeQuery(attr, n=node, listEnum=True)[0]}'"	

			# insert space as attempt fot neat formatting
			if getParent == None:
				udFlags += f"{' '*(len(attr)+6)}"
			udFlags += "  \t" # spacer for ranges and attribute limiters

			# range flags
			# the following compound or attribute types do not store limits firsthand:
			if getAttrType not in ["compound","typed","bool","enum", "matrix", "fltMatrix", "char", "time", "message", "reflectance", "spectrum"]:
				if mc.attributeQuery(attr, n=node, numberOfChildren = True) == None: # if not a number-based multi-attribute
					# soft range (slider limits)
					if mc.attributeQuery(attr, n=node, softMinExists = True):
						udFlags +=  ", hasSoftMinValue = True"
						udVal = mc.attributeQuery(attr, n=node, softMin = True)
						if len(udVal) == 1:
							udVal = udVal[0]
						udFlags += f", softMinValue = {udVal}"
					if mc.attributeQuery(attr, n=node, softMaxExists = True):
						udFlags +=  ", hasSoftMaxValue = True"
						udVal = mc.attributeQuery(attr, n=node, softMax = True)
						if len(udVal) == 1:
							udVal = udVal[0]
						udFlags += f", softMaxValue = {udVal}"
					# hard range (hard limits)
					if mc.attributeQuery(attr, n=node, minExists = True):
						udFlags +=  ", hasMinValue = True"
						udVal = mc.attributeQuery(attr, n=node, min = True)
						if len(udVal) == 1:
							udVal = udVal[0]
						udFlags += f", minValue = {udVal}"
					if mc.attributeQuery(attr, n=node, maxExists = True):
						udFlags +=  ", hasMaxValue = True"
						udVal = mc.attributeQuery(attr, n=node, max = True)
						if len(udVal) == 1:
							udVal = udVal[0]
						udFlags += f", maxValue = {udVal}"
					# default value
					udFlags += f", defaultValue = {mc.attributeQuery(attr, n=node, listDefault = True)[0]}"

			# hidden?
			holdBool = mc.attributeQuery(attr, n=node, hidden = True)
			udFlags += f", hidden = {'True'*holdBool}{'False'*(not holdBool)}"
			# connection settings
			holdBool = mc.attributeQuery(attr, n=node, readable = True)
			udFlags += f", readable = {'True'*holdBool}{'False'*(not holdBool)}"
			holdBool = mc.attributeQuery(attr, n=node, writable = True)
			udFlags += f", writable = {'True'*holdBool}{'False'*(not holdBool)}"
			# animatable?
			holdBool = mc.attributeQuery(attr, n=node, keyable = True)
			udFlags += f", keyable = {'True'*holdBool}{'False'*(not holdBool)}"

			# attributeType or dataType?
			attrTypeUD = ""
			if getAttrType == "typed":
				objAttr = f"{node}.{attr}"
				attrTypeUD = f", dt='{mc.getAttr(objAttr, type=True)}'"
			else:
				attrTypeUD=f", at='{getAttrType}'"
			printAddAttrs += f"\nmc.addAttr(nodeList[{nodeListPrintIndex}], ln='{attr}'{attrTypeUD}{udFlags})"

			#-------------------
			# setAttr subroutine
			#-------------------
			if mc.getAttr(f"{node}.{attr}", type=True) == "nurbsCurve":
				# nurbsCurve handler again
				# make the nurbsCurve setAttr handler subroutine a function, it's not worth this much duplication.
				# printAddAttrs
				pass
			# get attributes that are strictly one-member only
			setAttrNotTypeUD = getAttrType not in ["compound","typed", "time", "message", "reflectance", "spectrum", "double2", "double3", "float2", "float3", "long2", "long3", "short2", "short3"]
			setAttrNotConnected = mc.listConnections(f"{node}.{attr}", s=True, d=False) == None
			if setAttrNotTypeUD and setAttrNotConnected: # if specific attribute type AND is NOT connected
				udAttrMSL : om2.MSelectionList = om2.MSelectionList().add(f"{node}.{attr}")
				udAttrIsDefault = udAttrMSL.getPlug(0).isDefaultValue()
				udAttrMSL.clear()
				del udAttrMSL
				if not udAttrIsDefault: # if NOT at default value
					getAttrValues = mc.getAttr(f'{node}.{attr}')
					attrFlatString = f"{getAttrValues}"
					if type(getAttrValues) == type(list()):
						# compound attribute, expand list
						# "[(1.0, 2.0, 3.0)]"
						attrFlatString = attrFlatString[1:-1]
						if getAttrType in ["double2", "double3", "float2", "float3", "long2", "long3", "short2", "short3"]:
							# mc.getAttr apparently returns double3 as a single tuple, within a list-type return??
							attrFlatString = attrFlatString[1:-1]
					printAddAttrs +=f"\nmc.setAttr(f'{'{'}nodeList[{nodeListPrintIndex}]{'}'}.{attr}', {attrFlatString}, type='{mc.getAttr(f'{node}.{attr}', type=True)}') # dynamic attribute setAttr"
					# mc.setAttr(f'{nodeList[n]}.attr', value, value, value, type=dataType)
					pass

		addAttrList.append(printAddAttrs)
		pass


"""
=====================================
STAGE 3: connections of nodes in list
=====================================
"""

nodeListPrintIndex = -1 # lazy indexing
for node in nodeListStage2:
	nodeListPrintIndex += 1 # index in nodeList output

	thisNodeType = mc.nodeType(node)

	# types of nodes to skip:
	if thisNodeType in nodeTypeUseCommandsConstraint:
		# constraint node override, connections already made
		continue
	if thisNodeType in nodeTypeSkip:
		# other types of nodes to skip, see declaration above
		continue
	
	"""
	/////////////////////////////////////////
	mc.connectAttr("  connection operator  ")
	/////////////////////////////////////////
	"""
	# query outgoing connections
	queryConnections = mc.listConnections(node, s=False, c=True,  d=True, p=True )  # -> list : ["shortName_from.attr", "shortName_to.attr", ... , ... ]
		# downstream command
	thisNodeIndex = nodeListPrintIndex

	if queryConnections: # if not None
		for i in range(int(len(queryConnections)*0.5)): # -> "shortName_from.attr"
			# note: script has been working with shortnames the whole time,
				# ensure node names are all consistently shortNames or longNames (and not a mix of both)
			queryConnectedNode = queryConnections[i+i+1].split('.',1) # <- "shortName_to.attr" <- ["shortName_to","attr"]
			
			if mc.nodeType(queryConnectedNode[0]) in nodeTypeUseCommandsConstraint:
				# all connections handled by constraint handler, skip
				continue
			# filter out message connections
			if "message" in queryConnections[i+i  ].split(".",1)[1]:
				continue

			# filter out downstream connections that do not connect to selection
			if queryConnectedNode[0] in nodeListStage2: 
				# downstream node is in selection scope, append [input, output] to list
				holdIndex = nodeListStage2.index(queryConnectedNode[0])
					# error case ("thing" is not in list) should not occur because it's filtered earlier

				fromNode = 'f"{' + f"nodeList[{thisNodeIndex}]" + '}' + f'.{queryConnections[i+i  ].split(".",1)[1]}"'
				#           f"{      nodeList[       n       ]     }      .                         attribute     "
				# f"{nodeList[n]}.attribute"

				toNode   = 'f"{' + f"nodeList[{holdIndex    }]" + '}' + f'.{queryConnections[i+i+1].split(".",1)[1]}"'
				#           f"{      nodeList[       n       ]     }      .                         attribute     "			
				# f"{nodeList[n]}.attribute"
							
				# write connectAttr commands
				writeConnectCommand = f'mc.connectAttr({fromNode}, {toNode},\t f=True) # {queryConnections[i+i]} -> {queryConnections[i+i+1]}'
				testFromConnection = om2.MFnAttribute( om2.MSelectionList().add(queryConnections[i+i]).getPlug(0).attribute() ).dynamic
				testToConnection = om2.MFnAttribute( om2.MSelectionList().add(queryConnections[i+i+1]).getPlug(0).attribute() ).dynamic
				if testFromConnection or testToConnection: # if any attribute side of the connection is a dynamic attribute: append to addAttr list instead
					addAttrIndexFrom = None
					if testFromConnection:
						for i in range(len(addAttrList)): # get addAttrList index
							if f"mc.addAttr(nodeList[{thisNodeIndex}]" in addAttrList[i]:
								addAttrIndexFrom = i
								break
					addAttrIndexTo = None
					if testToConnection:
						for i in range(len(addAttrList)): # get addAttrList index
							if f"mc.addAttr(nodeList[{holdIndex}]" in addAttrList[i]:
								addAttrIndexTo = i
								break
					if testFromConnection and testToConnection: # if BOTH are dynamic attributes of different nodes: check for order and append to addAttrList index
						if thisNodeIndex > holdIndex: # append to bigger/later: from
							addAttrList[addAttrIndexFrom] += f"\n{writeConnectCommand}"
						else: #append to bigger/later or equal (if equal that means it's the selfsame node): to
							addAttrList[addAttrIndexTo] += f"\n{writeConnectCommand}"
					else: # else just append to the one that has the index
						if testFromConnection:
							addAttrList[addAttrIndexFrom] += f"\n{writeConnectCommand}"
						else:
							addAttrList[addAttrIndexTo] += f"\n{writeConnectCommand}"
				else:
					connectionList.append(writeConnectCommand)



	# next node



# ======= start write operation

# blank outFile closed at the top, reopen it
outFile = open(f"{fileRootPathMa}/{fileNameScriptOut}","w")

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
fileEnumerator.append(f"jointList = [None] * {len(jointList)}\n")
for printOut in jointList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# create nodes\n")
fileEnumerator.append(f"nodeList = [None] * {len(nodeListStage2)}\n")
for printOut in nodeList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# complex node creation (e.g. ikHandles, constraints)\n")
for printOut in commandList:
	fileEnumerator.append(f"{printOut}\n")
for printOut in constraintList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# reparent new DAG nodes; use r=True to move to parent (clears transform)\n# !!! DOUBLE-CHECK AND EDIT BEFORE RUNNING SCRIPT !!!\n")
for printOut in parentList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# custom attributes\n")
for printOut in addAttrList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# write attributes\n")
for printOut in setAttrList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n# connect attributes\n")
for printOut in connectionList:
	fileEnumerator.append(f"{printOut}\n")

fileEnumerator.append("\n\n# write additional commands below this line? (e.g. skinning splines to driver joints)\n\n")

fileEnumerator.append("\n\n# end of script\n")


outFile.writelines(fileEnumerator)
outFile.close()
print(f"\n# scripterStu: print done: {fileRootPathMa}/{fileNameScriptOut}")