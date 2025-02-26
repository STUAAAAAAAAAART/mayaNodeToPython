import maya.cmds as mc
import maya.api.OpenMaya as om2

"""
required reference
https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=__Nodes_index_html
https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=MAYA_API_REF_py_ref_class_open_maya_1_1_m_fn_nurbs_curve_html
https://help.autodesk.com/view/MAYAUL/2023/ENU/?guid=MAYA_API_REF_py_ref_class_open_maya_1_1_m_point_html
https://help.autodesk.com/cloudhelp/ENU/MayaCRE-Tech-Docs/CommandsPython/curve.html

https://groups.google.com/g/python_inside_maya/c/83qbnDIQKuw

maya.cmds command:

mc.curve() # returns the transform node, do subsequent commands to grab curve shape node

DG: nurbsCurve.cc
Cached curve Defines geometry of the curve. The properties are defined in this order:
First line: degree, number of spans, form (0=open, 1=closed, 2=periodic), rational (yes/no), dimension
Second line: number of knots, list of knot values
Third line: number of CVs
Fourth and later lines: CV positions in x,y,z (and w if rational) 

"""

activeSelection: om2.MSelectionList = om2.MGlobal.getActiveSelectionList()
checkList = activeSelection.getSelectionStrings()

mc.listAttr()


# so basically reconstruct the list of edit points by querying the whole number params of the point on curve function....


checkList: om2.MSelectionList = om2.MSelectionList().add("curveShape1")
getCurve = om2.MFnNurbsCurve(checkList.getDependNode(0))

testSpanCount = getCurve.numSpans # number of spans of curve
# number of EPs = number of spans, +1 IF curve is closed (i.e. last point connects to first point)
# spans are the curve segments between two points, EPs are points

testPoint = getCurve.getPointAtParam(1) # curve param query, returns om2.MPoint
# this returns position relative to object transform, not world transform
# [x,y,z,w]

print(list(testPoint)) # MPoint has a type-casting binding to convert to list or tuples
# TODO: is this possible with maths, to convert CVs to EPs?


# get [transform, shape] node
    # from one, also get the other, either way
# om2.MSelectionList point to the shape node
# cast MFnNurbsCurve to the nurbsCurve DG node
# get the number of param points (either in om2 or mc)
# for-loop all the param points out
# these are your edit points

# get core curve definitions (degree/bezier, closed/open/periodic, componentVisibility, curveDisplayColour...)
# get transforms
# get all user-defined attributes


newCurve = [
    mc.createNode("transform", n="curveStu0"),
    mc.createNode("nurbsCurve", p="curveStu0", n="nurbsCurve_curveStu0")
]
