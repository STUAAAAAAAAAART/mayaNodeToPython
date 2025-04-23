import numpy as np # trig functions are all in radians
from numpy.linalg import inv as mInv

# maya world transform matrix, position-only

p1 = np.matrix([ # world position of joint being oriented
	[1,0,0,0],
	[0,1,0,0],
	[0,0,1,0],
	[0.491209,1.995682,-0.88089,1]])

p2 = np.matrix([ # world position of forward joint
	[1,0,0,0],
	[0,1,0,0],
	[0,0,1,0],
	[2.317401,2.199864,-1.670406,1]])

p3 = np.matrix([ # third joint, existing on the smae triangle plane
	[1,0,0,0],
	[0,1,0,0],
	[0,0,1,0],
	[0,0,0,1]])




def orient3Point(position, forward, other):
	# convert world transforms to points
	pass
	# maya worldMatrix tuple

	# np.array 4x4
	p1 : np.array = position # 
	p2 : np.array = forward
	p3 : np.array = other

	# translate components
	pt1= p1.A[-1] # array([x,y,z,w])
	pt2= p2.A[-1]
	pt3= p3.A[-1]

	pvA= pt3-pt1 # triangle side vectors
	pvB= pt2-pt1

	pNml = np.cross(pvA[:-1], pvB[:-1]) # [x,y,z]
	pNml = np.resize(pNml, 4)
	pJnt = pt1-pt3
	pFwd = pt2-pt3
	pJnt[-1] = 1.0 # reset W component
	pFwd[-1] = 1.0 # same
	pNml[-1] = 1.0 # same

	orient = [0,0,0] # xyz

	# Z orient
	pEval = pFwd - pJnt # [x,y,z,w]
	orient[2] = np.arctan(pEval[1] / pEval[0] ) # z <- y/x
	matZ = np.identity(4)
	cosZ = np.cos(orient[2])
	sinZ = np.sin(orient[2])
	matZ[0,0] = matZ[1,1] = cosZ
	matZ[0,1] = sinZ
	matZ[1,0] = -sinZ
#	matZ = matZ.transpose()
	invZ = mInv(matZ)

	pJnt = pJnt@invZ
	pFwd = pFwd@invZ
	pNml = pNml@invZ

	# Y orient
	pEval = pFwd - pJnt # [x,y,z,w]
	orient[1] = np.arctan(-pEval[2] / pEval[0] ) # y <- z/x
	# also not sure why ^this has to be negative? 
	matY = np.identity(4)
	cosY = np.cos(orient[1])
	sinY = np.sin(orient[1])
	matY[0,0] = matY[2,2] = cosY
	matY[2,0] = sinY
	matY[0,2] = -sinY
#	matY = matY.transpose()
	invY = mInv(matY)

	pJnt = pJnt@invY
	pFwd = pFwd@invY
	pNml = pNml@invY

	# X orient
	pEval = pJnt # [x,y,z,w]
	orient[0] = np.arctan(pEval[2] / pEval[1] ) # x <- y/z
	matX = np.identity(4)
	cosX = np.cos(orient[0])
	sinX = np.sin(orient[0])
	matX[1,1] = matX[2,2] = cosX
	matX[1,2] = sinX
	matX[2,1] = -sinX
#	matX = matX.transpose()

	orientMatrix = matX@matY@matZ
	
	for i in range(3):
		orient[i] = float(np.rad2deg(orient[i]))
	
	print(orient)
	return orientMatrix

testMatrix = orient3Point(p1,p2,p3)

print(testMatrix)