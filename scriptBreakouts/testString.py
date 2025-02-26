"""
THANK YOU John Creson
https://groups.google.com/g/python_inside_maya/c/83qbnDIQKuw

cmds.setAttr('myNurbsCurveShape.cc',
	3,1,0, False,3,
	(0,0,0,1,1,1),6,
	4,
	(-2,3,0),
	(2,1,0),
	(2,-3,0),
	(-2,-1,0),
	type='nurbsCurve'
    )
"""

"""
maya MEL setattr command

['\tsetAttr ".ws[0]" -type "nurbsCurve" ', '\t\t3 6 0 no 3', '\t\t11 0 0 0 1 2 3 4 5 6 6 6', '\t\t9', '\t\t-2.0000000000001679 5 13.00000000000019', '\t\t-3.5393162393164861 5 9.4111111111112198', '\t\t-6.6179487179490444 5 2.2333333333332837', '\t\t4.4717948717950335 5 -3.9333333333333247', '\t\t12.730769230769258 5 -4.5000000000000782', '\t\t-1.3948717948718699 5 9.93333333333333', '\t\t10.848717948718051 5 18.76666666666673', '\t\t11.616239316239362 5 9.5888888888889348', '\t\t11.999999999999996 5 5', '\t\t;']

"""

cacheString = [
	3, 10, 0, False, 3,
	[0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4], 15,
	13,
	(-8, 0, 9),
	(-13, 0, 7),
	(-14, 0, -4),
	(-9, 0, -7),
	(-4, 0, -10),
	(0, 0, -5),
	(0, 0, 0),
	(0, 0, 5),
	(3, 0, 10),
	(7, 0, 8),
	(11, 0, 6),
	(14, 0, -5),
	(9, 0, -9)
]

# ==============
"""
MEL to python command parser
output from om2.MObject.getPlug(x).getSetAttrCmds()

melString = ['\tsetAttr ".ws[0]" -type "nurbsCurve" ', '\t\t3 6 0 no 3', '\t\t11 0 0 0 1 2 3 4 5 6 6 6', '\t\t9', '\t\t-2.0000000000001679 5 13.00000000000019', '\t\t-3.5393162393164861 5 9.4111111111112198', '\t\t-6.6179487179490444 5 2.2333333333332837', '\t\t4.4717948717950335 5 -3.9333333333333247', '\t\t12.730769230769258 5 -4.5000000000000782', '\t\t-1.3948717948718699 5 9.93333333333333', '\t\t10.848717948718051 5 18.76666666666673', '\t\t11.616239316239362 5 9.5888888888889348', '\t\t11.999999999999996 5 5', '\t\t;']

"""

melString = [
    '\tsetAttr ".ws[0]" -type "nurbsCurve" ',
    '\t\t3 6 0 no 3',
    '\t\t11 0 0 0 1 2 3 4 5 6 6 6',
    '\t\t9',
    '\t\t-2.0000000000001679 5 13.00000000000019',
    '\t\t-3.5393162393164861 5 9.4111111111112198',
    '\t\t-6.6179487179490444 5 2.2333333333332837',
    '\t\t4.4717948717950335 5 -3.9333333333333247',
    '\t\t12.730769230769258 5 -4.5000000000000782',
    '\t\t-1.3948717948718699 5 9.93333333333333',
    '\t\t10.848717948718051 5 18.76666666666673',
    '\t\t11.616239316239362 5 9.5888888888889348',
    '\t\t11.999999999999996 5 5',
    '\t\t;'
    ]

melString.pop() # don't need the last bit
melString.pop(0) # don't need the MEL command
for i in range(len(melString)):
    melString[i].replace("\t",'')


# ==============
"""
python nurbsCurve data constructor
"""

buildList = []
curveKnots = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]
cvList = [
    (-8, 0, 9), (-13, 0, 7), (-14, 0, -4), (-9, 0, -7), (-4, 0, -10), (0, 0, -5), (0, 0, 0),(0, 0, 5), (3, 0, 10), (7, 0, 8), (11, 0, 6), (14, 0, -5), (9, 0, -9)
]
# list of tuple triples; all are position vectors relative to object space


buildList += [
    3, # degree
    10, # number of spans
    0, # form (0=open, 1=closed, 2=periodic)
	False, # rational (True/False)
    3 # dimension
]
buildList.append(curveKnots) # curve knot values
buildList.append( len(curveKnots) ) # number of curve knots
buildList.append( len(cvList)) # number of CVs
buildList += cvList # CV positions


