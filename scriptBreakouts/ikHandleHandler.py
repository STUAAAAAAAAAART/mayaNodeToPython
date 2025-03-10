import maya.cmds as mc
import maya.api.OpenMaya as om2

startJoint = 'joint1'
endJoint = 'joint3'
nameHandle = 'ikhTestHandle1'
ikCurve = 'curve1'

controlPV = 'locator1'
namePV = 'pvc_jointsIK1'

#ikhSolver = 'ikRPsolver'
ikhSolver = 'ikSplineSolver'

getIK = mc.ikHandle(n=nameHandle, sj=startJoint, ee=endJoint, solver=ikhSolver)
print(getIK)

getIK = mc.ikHandle(n=nameHandle, sj=startJoint, ee=endJoint, solver=ikhSolver, ccv=False, curve = ikCurve)
print(getIK)
"""
main reason to provide a curve instead of letting the command make one
	is because there are fairly common cases where the joint chain will move
	due to the ikHandle command's generated curve not being fitted well

consider making the curve BEFORE invoking mc.ikHandle()
mc.ikHandle(n=nameHandle, sj=startJoint, ee=endJoint, solver=ikhSolver, ccv=False, curve = ikCurve)
"""


mc.ikHandle(nameHandle, query = True, solver=True)

makePV = mc.poleVectorConstraint(controlPV, nameHandle, n=namePV)
print(makePV)

"""
return values of creation commands:

if ikRPsolver:
mc.ikHandle will return the following:
[handle, effector]

if ikSplineSolver and curve is not specified:
mc.ikHandle will return the following:
[handle, effector, curve]

if ikSplineSolver BUT curve is provided:
mc.ikHandle(n=nameHandle, sj=startJoint, ee=endJoint, solver=ikhSolver, ccv=False, curve = ikCurve)
mc.ikHandle will return the following:
[handle, effector]


mc.poleVectorConstraint will return the following:
[constraint]

"""

"""
connections and commands to figure out the local node graph for the local IK system:

getting the end effector node or the IK handle from either: look for this connection
effector.handlePath -> ikHandle.endEffector

getting the type of IK system:
mc.ikHandle(node, query = True, solver=True) -> str
# return string is immediately compatible to ikHandle creation command

getting the control curve of the IK system:


getting pole vector controller:

"""