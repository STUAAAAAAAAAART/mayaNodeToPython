import maya.cmds as mc
import maya.api.OpenMaya as om2

"""
/////
setup
/////
"""
# example list of edit points from querying xform world position of joint chain
jointEP = [(0.0, 0.0, 0.0), (5.0, -1.9999999999999998, 0.0), (10.0, -3.0, 0.0), (15.0, -1.9999999999999993, 0.0), (20.00000000000002, -1.5543122344752192e-15, 0.0)]

# create the curve object

curveTf = mc.createNode('transform', name="curveTest1")
curveSh = mc.createNode('nurbsCurve', name="curveTestShape1", p=curveTf)




"""
/////////////////////////////////////////////////////////////
begin test (run code snippet between this section separately)
/////////////////////////////////////////////////////////////
"""

# reset curve to valid cubic zero
mc.setAttr( 'curveShape1.cc' , 3,1,0,False,3,(0,0,0,1,1,1),6,4,(0,0,0),(0,0,0),(0,0,0),(0,0,0), type="nurbsCurve")

# get worldInverseMatrix of transform
getWIM = mc.getAttr(curveTf+'.worldInverseMatrix')


# -----------------------------------------------------------------------------------------------
"""
matrix multiplication

IMPORTANT:
affine transforms in maths education is usually in the form
	where the position component is at the COLUMN ON THE RIGHT

MAYA'S IMPLEMENTATION HAS TRANSPOSED MATRICES OF THE AFFINE TRANSFORM
	where the position component is at the ROW ON THE BOTTOM
"""
matA = getWIM

txfEP = []

for ep in jointEP:
	matB = list(ep) # XYZ
	matB.append(1.0) # W
	matMult = []
	matMult.append( matA[ 0]*matB[0] + matA[ 4]*matB[1] + matA[ 8]*matB[2] + matA[12]*matB[3] )
	matMult.append( matA[ 1]*matB[0] + matA[ 5]*matB[1] + matA[ 9]*matB[2] + matA[13]*matB[3] )
	matMult.append( matA[ 2]*matB[0] + matA[ 6]*matB[1] + matA[10]*matB[2] + matA[14]*matB[3] )
	matMult.append( matA[ 3]         + matA[ 7]         + matA[11]         + matA[15]         )
	
	# normalise components relative to W and remove W
	for i in range(len(matMult)-1):
		matMult[i] = matMult[i] / matMult[-1]
	
	txfEP.append( tuple(matMult[:-1].copy()) )

# -----------------------------------------------------------------------------------------------

print(txfEP) # debug

# apply new curve through adjusted list of EPs
mc.curve(curveTf, r=True, ep=txfEP, d=3)

# so if the script requires reparenting the curve transform elsewhere, this operation should negate all the prior transforms
# ideally all curves in splineIK operations should be treated like skinned meshes in bind rigs,
	# i.e. not parented to any moving part, leave alone