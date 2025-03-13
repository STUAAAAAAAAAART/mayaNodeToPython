import maya.cmds as mc
import maya.api.OpenMaya as om2

handleEffector = ['ikHandleExample1' , 'ikEffectorExample1']
solverType = 'ikSplineSolver' # this script only deals with splineIK for demonstration purposes

startJoint = 'joint1'
endJoint = 'joint5'

curveTransform = 'curveExample1'
curveShape = 'nurbsCurveExample1'

# -----------------------------------------------------------------------------------

startEndJointPaths = [None, None]
startEndJointPaths[0] = mc.ls(startJoint, long=True)[0]
	# mc.ls() -> ['|joint4']
	# -[0]-> '|joint4'
startEndJointPaths[1] = mc.ls(endJoint, long=True)[0]
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

# -----------------------------------------------------------------------------------

curveTransformShape = [None,None]
curveTransformShape[0] = mc.createNode('transform', n=curveTransform)
curveTransformShape[1] = mc.createNode('nurbsCurve', n=curveShape, p=curveTransformShape[0])
mc.setAttr(curveTransformShape[1]+'.cc', 3,1,0,False,3,(0,0,0,1,1,1),6,4,(0,0,0),(0,0,0),(0,0,0),(0,0,0), type="nurbsCurve")
	# this is a cubic curve with two edit points at (0,0,0), applied temporarily to make it a valid cubic curve
mc.curve(curveTransformShape[0], replace=True, ep=jointAsEPs, d=3)

# -----------------------------------------------------------------------------------
ikNewHandleEffector = mc.ikHandle(n=handleEffector[0], sj=startJoint, ee=endJoint, solver='ikSplineSolver', ccv=False, curve = curveTransformShape[0])
ikNewHandleEffector[1] = mc.rename(ikNewHandleEffector[1], handleEffector[1])

print(ikNewHandleEffector)