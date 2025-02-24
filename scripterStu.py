import maya.cmds as mc
import maya.api.OpenMaya as om2

activeSelection: om2.MSelectionList = om2.MGlobal.getActiveSelectionList()

# detection phase: get all connections strictly within selection

checkList = activeSelection.getSelectionStrings() # -> list : ["shortName", ... ]

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
	# other constrain types specifiec in maya; skip
	'normalConstraint', 'dynamicConstraint', 'pointOnPolyConstraint', 'rigidConstraint', 'symmetryConstraint', 'tangentConstraint', 
	# skinning nodes, apply in-scene or elsewhere; skip
	'skinCluster', 'cluster', 'clusterFlexorShape', 'clusterHandle', 'jointCluster', 'jointClusterManip'
]

# skipNodeFromConnectionCheck = nodeTypeUseCommandsConstraint + nodeTypeUseCommandsIK + nodeTypeFilterOut

selectionList = []
nodeList = []
constructorList = []
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
		# also the constrain commands create a user 

		# query number of targets
		
		# if many targets: comment and list names
		nodeList.append(f"mc.{thisNodeType}('!!SELECT PARENT HERE','{stu_constraintChild}', n='{node}' , maintainOffset=False)")
		# mc.command(selection) # e.g. [parent,child]
		
		# if one target: fully enumerate exact command and values
			# (especially important for poleVectorConstraint because it's being used so frequently with IK systems)

		nodeList.append(f"mc.{thisNodeType}('!!SELECT PARENT HERE','{stu_constraintChild}', n='{node}' , maintainOffset=False)")
		# mc.command(selection) # e.g. [parent,child]
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

# print phase: print all commands for creation and connections
# TODO: write text to file (honestly copying from the script editor will do for now)


print("\n# scripterStu: start print\n")

print("import maya.cmds as mc")
print("import maya.api.OpenMaya as om2\n")

print("activeSelection = om2.MGlobal.getActiveSelectionList()")

print("\n# create nodes\n")
print(f"nodeList = list(range({len(checkList)}))\n")

for printOut in nodeList:
	print(printOut)
print("\n# custom attributes\n")
for printOut in addAttrList:
	print(printOut)
print("\n# connect attributes\n")
for printOut in connectionList:
	print(printOut)

print(f"\n# scripterStu: print done\n")