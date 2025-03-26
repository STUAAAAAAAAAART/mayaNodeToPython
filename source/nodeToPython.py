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
	if thisNodeType in ["nurbsCurve", "bezierCurve"] or thisNodeType == "transform": # nurbsCurve and general transforms
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
		
		# ++++++++++++++++++++++++++++++++++++++++++++++++++++
		# enumerate first transform
		# skip if node exists (especially if made by splineIK)
		# ++++++++++++++++++++++++++++++++++++++++++++++++++++
		if transformAndShape[0][0] not in nodeListStage2: # if this transform has NOT already been made
			nodeListStage2.append(transformAndShape[0][0]) # first/original transform node
			getParent = mc.listRelatives(transformAndShape[0][0])
			if getParent:
				getParent = [f'p="{getParent[0]}", ', f'parented under: {getParent[0]}']
			else:
				getParent = ['',''] # None cast to string is the word 'None' -_-
			nodeList.append(f'nodeList[{len(nodeListStage2)-1}] = mc.createNode("transform", n="{transformAndShape[0][0]}", {getParent[0]} skipSelect = True) # {getParent[1]}')
			#                 nodeList[n]             = mc.createNode("transform", n="nName"                    , p="parent"    , skipSelect = True)

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
				shapeCommand = []
				shapeCommand.append(f'nodeList[{shapeNodeListIndex}] = mc.createNode("{thisShapeType}", n="{transformAndShape[1]}", p=nodeList[{len(nodeListStage2)-2}], skipSelect = True) # transform: {transformAndShape[0][0]}')
				#                     nodeList[n]               = mc.createNode("nurbsCurve"   , n="shapeName"             , P="transformName",             skipSelect = True)
				skipList.append(transformAndShape[1])
				if thisShapeType in ["nurbsCurve, bezierCurve"]:
					# ----------------------------------------------------------------------------------------------
					# time for om2.MPlug.getSetAttrCmds()
					getShapeMSL : om2.MSelectionList = om2.MSelectionList().add(transformAndShape[1]+".worldSpace")
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
		if thisNodeType == 'ikEffector':
			handleSolverEffector[0] = mc.listConnections(node+'.handlePath', source = False , destination = True)[0]
			# ASSUME ONLY 1 HANDLE PER EFFECTOR. come back to this when an in-field exception has been created
			handleSolverEffector[1] = mc.ikHandle(handleSolverEffector[0], query = True, solver=True)
			handleSolverEffector[2] = node

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
				jointList[indexJointsStartEnd[i]] += f" # IK joint : {handleSolverEffector[0]}"
			else: # new joint encountered
				skipList.append(startEndJoints[i]) # if the script encounters this joint again, it'll skip immediately
				nodeListStage2.append(startEndJoints[i])
				indexJointsStartEnd[i] = len(nodeListStage2)-1
				holdText = ["start","end"]
				jointList.append(f"jointList[{len(jointList)}] = '{startEndJoints[i]}' # IK joint {holdText[i]} : {handleSolverEffector[0]}")
				nodeList.append(f"nodeList{indexJointsStartEnd[i]} = jointList[{len(jointList)-1}] # joint - {startEndJoints[i]}")

		ikCommands = []

		stringIfSplineIK = None
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
		nodeList.append(f"nodeList[{indexHandleEffector[0]}] = {handleSolverEffector[0]} # ikhandle, {handleSolverEffector[1]}")
		nodeListStage2.append(handleSolverEffector[2]) # ikEffector
		indexHandleEffector[1] = len(nodeListStage2)-1
		nodeList.append(f"nodeList[{indexHandleEffector[1]}] = {handleSolverEffector[1]} # ikEffector")

		# ---------------------------
		makeCommandIKH = f"nodeList[{indexHandleEffector[0]}], stuTempEffector = "
		#                  nodeList[A]                       , nodelist[B] = 
		makeCommandIKH += f"mc.ikHandle(n=nodeList[{indexHandleEffector[0]}], sj=nodeList[{indexJointsStartEnd[0]}], ee=nodeList[{indexJointsStartEnd[1]}], solver='{handleSolverEffector[1]}'{stringIfSplineIK})"
		#                   mc.ikHandle(n=nodeList[       nameHandle       ], sj=nodeList[       startJoint       ], ee=nodeList[        endJoint        ], solver='        ikhSolver        ', ccv=False, curve = ikCurve)
		makeCommandIKH += f"\n# ikHandle: {handleSolverEffector[0]} ; start/end joints: {startEndJoints} ; ikSolver: {handleSolverEffector[1]}"
		if stringIfSplineIK:
			makeCommandIKH += f" ; splineIK curve: {transformAndShape[0]}"
		makeCommandIKH += f"\nnodeList[{indexHandleEffector[1]}] = mc.rename(stuTempEffector, nodeList[{indexHandleEffector[1]}]) # ikEffector node - {handleSolverEffector[2]}"


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
		nodeList.append(f'nodeList[{len(nodeListStage2)-1}] = mc.createNode("{thisNodeType}", n="{node}", skipSelect = True)')
		#                 nodeList[n]                       = mc.createNode("nodeType"      , n="nName" , skipSelect = True)
		# nodeList[n] = mc.createNode("nodeType", n="nName", skipSelect = True)

"""
-----------
END STAGE 1
-----------
"""

# -------------- attribute checking, creation and setting
# WARNING WITH TUPLES: (value) IS value, (value,) IS TUPLE CONTAINING value
checkTransform = [ # transform node
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
	('useObjectColor',),
	('objectColor',),
	('objectColorRGB', 'objectColorR', 'objectColorG', 'objectColorB'),
	('wireColorRGB', 'wireColorR', 'wireColorG', 'wireColorB'),
	('useOutlinerColor',),
	('outlinerColor', 'outlinerColorR', 'outlinerColorG', 'outlinerColorB')
]

checkCMX = [ # composeMatrix node
	('inputQuat', 'inputQuatX', 'inputQuatY', 'inputQuatZ', 'inputQuatW'),
	('inputRotate', 'inputRotateX', 'inputRotateY', 'inputRotateZ'),
	('inputRotateOrder'),
	('inputScale', 'inputScaleX', 'inputScaleY', 'inputScaleZ'),
	('inputShear', 'inputShearX', 'inputShearY', 'inputShearZ'),
	('inputTranslate', 'inputTranslateX', 'inputTranslateY', 'inputTranslateZ'),
	('useEulerRotation',)
]

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
==========================================================
STAGE 2: attributes and connections and secondary commands
==========================================================
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
			getDriven = f"{nodeListStage2.index(getDriven)}"
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

			targetListIndexNL = []
			for t in getTargets:
				# check if target is in nodeList
				if t in nodeListStage2:
					# use nodeList Index
					targetListIndexNL.append(f"nodeList[{nodeListStage2.index(t)}]")
				else:
					# use direct name.....
					targetListIndexNL.append(f"{t}")

			"""
			connectAttr( targetWeight CONNECTION )
			writing the connectAttr command here because the main subroutine in stage 2 is going to skip constraint nodes
			"""
			queryTargetWeight = mc.listConnections(f"{node}.target[{i}].targetWeight", s=True, d=False, c=True, p=True)

			# check if targetWeight is connected to command-premade user-defined attribute on self
			if queryTargetWeight[0].split('.', 1)[0] == queryTargetWeight[1].split('.', 1)[0]: # if true, check where THAT is being connected to
				# if this connects to itself AGAIN, i am not saving the user from themselves (even if it means that'd be me)
				# reminder that this script will not be making addAttr commands for constraint nodes
				getTargetWeightConnection.append( mc.listConnections(queryTargetWeight[1], s=True, d=False, plugs=True)[0] )
			else: # it's connected to something else directly, get connection
				getTargetWeightConnection.append( queryTargetWeight[1] )
			
			# if targetWeight is connected:
			if getTargetWeightConnection[-1]: # if not None, in which case ignore and let it default
				getWeightConnectionRight = f"nodeList[{nodeListPrintIndex}]+'.target[{len(getTargetWeightConnection)-1}.targetWeight]'"
				if getTargetWeightConnection[-1].split('.')[0] in nodeListStage2: # if node is in nodelist
					# compose connectAttr command
					getWeightConnectionLeft = nodeListStage2.index(getTargetWeightConnection[-1].split('.')[0])
					getWeightConnectionLeft = f"nodeList[{getWeightConnectionLeft}]+'.{getTargetWeightConnection[-1].split('.')[1]}'"

					thisConstraintCommand += f"\nmc.connectAttr({getWeightConnectionLeft}, {getWeightConnectionRight}, force=True)"
					pass
				else:
					# compose setAttr command, but comment-out
					thisConstraintCommand += f"\n# mc.connectAttr('{getTargetWeightConnection[-1]}', {getWeightConnectionRight}, force=True)"
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
					thisConstraintCommand += f"\nmc.connectAttr('{aimVectorConnectionLeft}', {aimVectorConnectionRight}, force=True) # aim worldUpVector: {getAimVectorConnection}"
				else:
					# just print the name...
					thisConstraintCommand += f"\nmc.connectAttr('{getAimVectorConnection}', {aimVectorConnectionRight}, force=True)"
			pass

		commandObjects = ""
		for i in getTargets:
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
				getParent = f"f'nodeList[{nodeList.index(getParent)}]'" # f'nodeList[n]'
			else:
				getParent = f"'{getParent}'" # 'parentNode'
			# compose parenting command
			#                   mc.parent(            "child"              ,  "parent"      )
			parentList.append(f"mc.parent(nodeList[{nodeListPrintIndex}], {getParent} ) # child: {node} -> parent: {printParent} " )
			#                   mc.parent(            "child"              , f'nodeList[n]' )

	"""
	//////////////////////////////////////////////////////////////
	mc.setAttr("  recording transform nodes and extra commands  ")
	mostly default attributes, should come before connectAttr
	//////////////////////////////////////////////////////////////
	"""
	if thisNodeType in ["transform", "composeMatrix"]:
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
				getNodeIncomingConnections[i] = getNodeIncomingConnections[i].split('.')[-1]
			# [attr, attr, attr, ...]
		else: # listConnections returned None
			getNodeIncomingConnections = [] # just to make the following work

		printSetAttrList = []
		getPlugHelper : om2.MSelectionList = om2.MSelectionList()
		checkList = None

		# load check attribute list
		if thisNodeType == "transform":
			checkList = checkTransform
		if thisNodeType == "composeMatrix":
			checkList = checkCMX

		# for each set of attributes in checker list
		for attrSet in checkList:
			if attrSet[0] in getNodeIncomingConnections: # if main attr has incoming connections
				# main attribute is connected upstream, skip
				continue
			
			# check if main attr has any changes to its value
			mainAttrMSL : om2.MSelectionList = om2.MSelectionList().add(f"{node}.{attrSet[0]}")
			mainAttrIsDefault = mainAttrMSL.getPlug(0).isDefaultValue()
			mainAttrMSL.clear()
			del mainAttrMSL # cleanup....
			if mainAttrIsDefault: # if main attribute is all default, i.e. no change in value
				continue # skip, no point making setAttr for this

			print(f"DEBUGG ==== testing: {node}.{attrSet[0]}")

			if len(attrSet) > 1: # if this attr has subattributes
				subAttrConnected = True
				subAttrNotDefault = len(attrSet) -1
				subAttrMSL : om2.MSelectionList = om2.MSelectionList()
				for attribute in attrSet[1:]:
					# check if subattribute is connected
					subAttrConnected = subAttrConnected and (attribute in getNodeIncomingConnections)
					# check if subattribute is default value
					subAttrMSL.add(f"{node}.{attribute}")
					if subAttrMSL.getPlug(0).isDefaultValue():
						subAttrNotDefault -= 1
					subAttrMSL.clear()
				del subAttrMSL # cleanup....
				if subAttrConnected or (subAttrNotDefault > 0):
					# all subattributes are connected, or all subattributes are default
					continue
					# otherwise just make the entire setAttr command for the main attribute

			# fall-through case: make setAttr command
			getAttrValues = mc.getAttr(f'{node}.{attrSet[0]}')
			if type(getAttrValues) == type(list):
				# compound attribute, expand listple to single string
				# [(1.0, 0.0, 0.0)]
				flatString = ""
				for val in getAttrValues[0]:
					flatString += f"{val}, "
				getAttrValues = flatString.removesuffix(", ")
			getAttrType = mc.getAttr(f'{node}.{attrSet[0]}', type=True)
			# compose the command
			if attrSet[0] == "wireColorRGB":
				# wireframe command override
				setAttrList.append(f"mc.color(nodeList[{nodeListStage2.index(node)}], rgb=({getAttrValues}) )")
				#                    mc.color(               nodeList[n]            , rgb=(      1,0,0    ) )
				# CAUTION: instances of transfrom objects will share the same wireframe colour in the scene
				continue
			setAttrList.append(f"mc.setAttr(f'{'{'}nodeList[{nodeListStage2.index(node)}]{'}'}.{attrSet[0]}', {getAttrValues}, type='{getAttrType}')")
			#                               f'  {  nodeList[{               n          }]  }  .  attribute '
			#                    mc.setAttr(                       f'{nodelist[n]}.attribute'               , 1, 2, 3, 4, 5,   type='dataType'     )


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

	# types of nodes to skip:
	if thisNodeType in nodeTypeUseCommandsConstraint:
		# constraint node override, connections already made
		continue
	if thisNodeType in nodeTypeSkip:
		# other types of nodes to skip, see declaration above
		continue
	
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

				fromNode = 'f"{' + f"nodeList[{thisNodeIndex}]" + '}' + f'.{queryConnections[i+i  ].split(".")[1]}"'
				#           f"{      nodeList[       n       ]     }      .                         attribute     "
				# f"{nodeList[n]}.attribute"

				toNode   = 'f"{' + f"nodeList[{holdIndex    }]" + '}' + f'.{queryConnections[i+i+1].split(".")[1]}"'
				#           f"{      nodeList[       n       ]     }      .                         attribute     "			
				# f"{nodeList[n]}.attribute"
							
				# write connectAttr commands
				connectionList.append(f'mc.connectAttr({fromNode}, {toNode}) # {queryConnections[i+i]} -> {queryConnections[i+i+1]}')



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

fileEnumerator.append("\n# reparent new DAG nodes\n# !!! DOUBLE-CHECK AND EDIT BEFORE RUNNING SCRIPT !!!\n")
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

fileEnumerator.append("\n\n# end of script\n")


outFile.writelines(fileEnumerator)
outFile.close()
print(f"\n# scripterStu: print done: {fileRootPathMa}/{fileNameScriptOut}")