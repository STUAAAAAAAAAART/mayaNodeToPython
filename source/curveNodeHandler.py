import maya.cmds as mc
import maya.api.OpenMaya as om2

activeSelection: om2.MSelectionList = om2.MGlobal.getActiveSelectionList()
checkList = activeSelection.getSelectionStrings()

mc.listAttr()


# so basically reconstruct the list of edit points by querying the whole number params of the point on curve function....


checkList: om2.MSelectionList = om2.MSelectionList().add("curveShape1")
getCurve = om2.MFnNurbsCurve(checkList.getDependNode(0))
testPoint = getCurve.getPointAtParam(1) # curve param query, returns om2.MPoint
print(list(testPoint)) # MPoint has a type-casting binding to convert to list or tuples
# TODO: is this possible with maths, to convert CVs to EPs?


newCurve = [
    mc.createNode("transform", n="curveStu0"),
    mc.createNode("nurbsCurve", p="curveStu0", n="nurbsCurve_curveStu0")
]
