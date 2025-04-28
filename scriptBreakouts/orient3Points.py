import maya.cmds as mc
import maya.api.OpenMaya as om2

def orient3Point(position, forward, other):
	try:
		assert mc.nodeType(position) == "joint" # test if type is joint
	except:
		raise AssertionError(f"input object not a joint: {position}")
	# ==== maths =============
	p0 = om2.MVector( mc.getAttr(f"{position}.worldMatrix")[-4:-1] )
	p1 = om2.MVector( mc.getAttr(f"{forward }.worldMatrix")[-4:-1] )
	p2 = om2.MVector( mc.getAttr(f"{other   }.worldMatrix")[-4:-1] )

	vFwd = (p1-p0).normal() # forward vector
	vPln = (p2-p0).normal() # coplanar vector
	vNrm = (vFwd ^ vPln).normal() # planar normal

	qFwd = om2.MQuaternion( om2.MVector(1,0,0), vFwd, 1) # initial forward vector
	qFwdZ = om2.MQuaternion( om2.MVector(1,0,0), om2.MVector(0,0,1), 1) * qFwd # initial forward vector's z-axis
	#	rotate z-axis by forward quaternion

	alignPlane = om2.MPlane().setPlane(vFwd, 0) # plane perpendicular to triangle z-axis
	vNrm # just a reminder
	vFwdZ = (om2.MVector(1,0,0).rotateBy(qFwdZ)).normal() # is definitely on the plane
	# point on plane relative to space = space vector - rejection vector
	# rejection vector = distance from plane * normal vector
	planeNrm = (vNrm - (alignPlane.distanceToPoint(vNrm) * alignPlane.normal())).normal() # current normal
	planeFwdZ = (vFwdZ - (alignPlane.distanceToPoint(vFwdZ) * alignPlane.normal())).normal() # correct normal
	qAlign = om2.MQuaternion(planeFwdZ, planeNrm, 1) # realignment rotation adjustment
	qOrient = qFwd * qAlign # coplanar joint orient

	getEuler = qOrient.asEulerRotation()
	orient = [getEuler.x, getEuler.y, getEuler.z]

	angleUnit = mc.currentUnit(q=True, angle=True)
	if angleUnit == 'deg': # result in radians, convert to scene units
		for i in range(3):
			orient[i] = om2.MAngle(orient[i],om2.MAngle.kRadians).asDegrees()

	# ==== parent handler =============
	getParentName = mc.listRelatives(position, p=True)
	if getParentName: # if not None, contains [string]
		getParentName = getParentName[0] # unpack string from list
	getChildrenNames = mc.listRelatives(position, p=True) or [] # just relative names, two nodes with a common parent can not have the same name
	holdSelf : om2.MSelectionList = om2.MSelectionList().add(position) # true pointer to object, not a bare string of temporary name
	mslChildren : om2.MSelectionList = om2.MSelectionList()
	for node in getChildrenNames:
		mslChildren.add(node)
	
	# ==== run =============
	if getChildrenNames: # if not []
		mc.parent(*getChildrenNames, w=True) # unparent children
	if getParentName: # if not None
		mc.parent(position, w=True) # unparent from parent
		
	mc.joint(position, e=True, o=orient) # apply orient of this joint

	if getParentName: # if not None
		mc.parent(holdSelf.getSelectionStrings(0), getParentName) # reparent to parent
		mc.rename(holdSelf.getSelectionStrings(0), position) # reassert name
	if getChildrenNames: # if not []
		getString = mslChildren.getSelectionStrings()	 
		mc.parent(*getString, position) # reparent children
		for i in range(len(getChildrenNames)): # reassert names
			mc.rename(getString[i],getChildrenNames[i])
	
	return orient