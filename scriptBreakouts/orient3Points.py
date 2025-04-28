import maya.cmds as mc
import maya.api.OpenMaya as om2

def orient3Point(position, forward, other, flip=False):
	try:
		assert mc.nodeType(position) == "joint" # test if type is joint
	except:
		raise AssertionError(f"input object not a joint: {position}")
	# ==== maths =============
	toDeg =    57.29577951308232 # A * 180/pi
	toRad = 0.017453292519943295 # A * pi/180
	p0 = om2.MVector( mc.getAttr(f"{position}.worldMatrix")[-4:-1] )
	p1 = om2.MVector( mc.getAttr(f"{forward }.worldMatrix")[-4:-1] )
	p2 = om2.MVector( mc.getAttr(f"{other   }.worldMatrix")[-4:-1] )

	vFwd = (p1-p0).normal() # forward vector
	vPln = (p2-p0).normal() # coplanar vector
	vNrm = None
	if flip:
		vNrm = (vPln ^ vFwd).normal() # planar normal
	else:
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

	angleUnit = mc.currentUnit(q=True, angle=True)
	posCurrentRotate = list(mc.getAttr(f"{position}.rotate")[0])
	if angleUnit == 'deg': # scene units in degrees, convert to radians
		for i in range (3):
			posCurrentRotate[i] = posCurrentRotate[i]*toRad
	posCurrentRotate = om2.MEulerRotation(*posCurrentRotate, om2.MEulerRotation.kXYZ)
	qOrient = posCurrentRotate.inverse().asQuaternion() * qOrient

	getEuler = qOrient.asEulerRotation()
	orient = [getEuler.x, getEuler.y, getEuler.z]
	if angleUnit == 'deg': # result in radians, convert to scene units if degrees
		for i in range(3):
			orient[i] = orient[i] * toDeg

	# ==== parent handler =============
	getParentName = mc.listRelatives(position, p=True, f=True)
	if getParentName: # if not None, contains [string]
		getParentName = getParentName[0] # unpack string from list
	getChildrenNames = mc.listRelatives(position, c=True, f=True) or [] # just relative names, two nodes with a common parent can not have the same name
	holdSelf : om2.MSelectionList = om2.MSelectionList().add(position) # true pointer to object, not a bare string of temporary name
	mslChildren : om2.MSelectionList = om2.MSelectionList()
	for node in getChildrenNames:
		mslChildren.add(node)
	
	# ==== run =============
	activeSelection = om2.MGlobal.getActiveSelectionList() # selection sanitisation: gets real current selection, for some reason this script will select the last joint at times 
	if getChildrenNames: # if not []
		mc.parent(*getChildrenNames, w=True) # unparent children
	if getParentName: # if not None
		mc.parent(holdSelf.getSelectionStrings(0), w=True) # unparent from parent
		
	mc.joint(holdSelf.getSelectionStrings(0), e=True, o=orient) # apply orient of this joint

	if getParentName: # if not None
		mc.parent(holdSelf.getSelectionStrings(0), getParentName) # reparent to parent
		mc.rename(holdSelf.getSelectionStrings(0), position.split("|")[-1]) # reassert name
	if getChildrenNames: # if not []
		mc.parent(*mslChildren.getSelectionStrings(), holdSelf.getSelectionStrings(0)) # reparent children
		for i in range(len(getChildrenNames)): # reassert names
			mc.rename(mslChildren.getSelectionStrings(i), getChildrenNames[i].split("|")[-1])

	mc.select(activeSelection.getSelectionStrings()) # reassert original scene selection
	return orient