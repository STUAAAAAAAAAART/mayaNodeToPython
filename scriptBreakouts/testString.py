import maya.cmds as mc
import maya.api.OpenMaya as om2

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
	'\tsetAttr ".ws[0]" -type "nurbsCurve" ', # toss
	'\t\t3 6 0 no 3', # index 0
	'\t\t11 0 0 0 1 2 3 4 5 6 6 6', # pop 0th and hold, append rest as list element 
	'\t\t9', #append normally
	'\t\t-2.0000000000001679 5 13.00000000000019', # append each as triples
	'\t\t-3.5393162393164861 5 9.4111111111112198',
	'\t\t-6.6179487179490444 5 2.2333333333332837',
	'\t\t4.4717948717950335 5 -3.9333333333333247',
	'\t\t12.730769230769258 5 -4.5000000000000782',
	'\t\t-1.3948717948718699 5 9.93333333333333',
	'\t\t10.848717948718051 5 18.76666666666673',
	'\t\t11.616239316239362 5 9.5888888888889348',
	'\t\t11.999999999999996 5 5',
	'\t\t;' # toss
	]

melString.pop() # don't need the last bit
melString.pop(0) # don't need the MEL command
for i in range(len(melString)):
	melString[i] = melString[i].replace("\t",'')


melString[0] = melString[0].split(' ')

for i in range(len(melString[0])):
	try:
		melString[0][i] = int(melString[0][i])
	except:
		if melString[0][i] == "yes":
			melString[0][i] = True
		elif melString[0][i] == "no":
			melString[0][i] = False
		else:
			raise ValueError("problems parsing info string into int and bool")
melString[1] = melString[1].split(' ')
melStringKnotCount = int(melString[1].pop(0)) # remove knot count
for i in range(len(melString[1])):
	melString[1][i] = int(melString[1][i])
	# raise default error if this can't be parsed

buildList = []

buildList += melString[0] # basic info
buildList.append(melString[1]) # knot data [0,0,0,1,1,1,2,2,2...]
buildList += [int(melString[2]), melStringKnotCount] # number of knots, number of CVs

melStringCvs = melString[3:]

for cv in range(len(melStringCvs)):
	# triples now
	melStringCvs[cv] = melStringCvs[cv].split(' ')
	for i in range(len(melStringCvs[cv])):
		melStringCvs[cv][i] = float(melStringCvs[cv][i])
		# raise default error if this can't be parsed
buildList += melStringCvs

# ==============
"""
MEL to python command parser, but in string form
"""
melString = [
	'\tsetAttr ".ws[0]" -type "nurbsCurve" ', # toss
	'\t\t3 6 0 no 3', # index 0
	'\t\t11 0 0 0 1 2 3 4 5 6 6 6', # pop 0th and hold, append rest as list element 
	'\t\t9', #append normally
	'\t\t-2.0000000000001679 5 13.00000000000019', # append each as triples
	'\t\t-3.5393162393164861 5 9.4111111111112198',
	'\t\t-6.6179487179490444 5 2.2333333333332837',
	'\t\t4.4717948717950335 5 -3.9333333333333247',
	'\t\t12.730769230769258 5 -4.5000000000000782',
	'\t\t-1.3948717948718699 5 9.93333333333333',
	'\t\t10.848717948718051 5 18.76666666666673',
	'\t\t11.616239316239362 5 9.5888888888889348',
	'\t\t11.999999999999996 5 5',
	'\t\t;' # toss
	]


melString.pop() # don't need the last bit
melString.pop(0) # don't need the MEL command

# REMINDER: STRINGS ARE IMMUTABLE

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

for i in range(len(melString) -3):
	# "-2.0000000000001679 5 13.00000000000019"
	melString[i+3] = melString[i+3].replace(' ', ", ")
	# "-2.0000000000001679, 5, 13.00000000000019"
	melString[i+3] = f"[{melString[i+3]}], "
	# "[-2.0000000000001679, 5, 13.00000000000019], "
melString[-1] = melString[-1].replace("], " , "]") # remove comma from end of last item

buildString = ""
for line in melString:
	buildString += line

print(buildString)

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


checkList: om2.MSelectionList = om2.MSelectionList()
checkList.add("multMatrix1")
checkList.add("curve1")
checkList.add("bezier1")
checkList.add("curveShape1")
checkList.add("bezierShape1")
checkList.add("bezierShape1.worldSpace")

for i in range(6):
	print(checkList.getDependNode(i).apiTypeStr) # returns k[NodeType], MPlugs only return owner's DG node (i.e. for node.attr, returns node)
	# https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=MAYA_API_REF_py_ref_class_open_maya_1_1_m_fn_html

# to check node type:
om2.MSelectionList.getDependNode().apiTypeStr
# to check if plug is of datatype