# just a quick script to enumerate that list of transform node attributes i wanted

import maya.cmds as mc
import maya.api.OpenMaya as om2

mc.createNode("transform", n="null1", ss=True)
mc.createNode("composeMatrix", n="cmx1", ss=True)

checkList0 = [["offsetParentMatrix"],["rotate"],["scale"],["translate"],["maxRotLimit"],["maxRotLimitEnable"],["maxScaleLimit"],["maxScaleLimitEnable"],["maxTransLimit"],["maxTransLimitEnable"],["minRotLimit"],["minRotLimitEnable"],["minScaleLimit"],["minScaleLimitEnable"],["minTransLimit"],["minTransLimitEnable"],["useObjectColor"],["objectColor"],["objectColorRGB"],["wireColorRGB"],["useOutlinerColor"],["outlinerColor"]]
checkList1 = [["inputQuat"], ["inputRotate"], ["inputRotateOrder"], ["inputScale"], ["inputShear"], ["inputTranslate"], ["useEulerRotation"]]

def enumSubAttributes(attrList:list = [], nodeName:str = ""):

	checkList = attrList.copy()
	gotChildren = []

	for i in checkList:
		gotChildren.append( mc.attributeQuery(i[0], node=nodeName, lc=True))

	for i in range(len(gotChildren)):
		if gotChildren[i] != None:
			checkList[i] += gotChildren[i]
			
	return checkList

print( enumSubAttributes(checkList0, "null1") )
print( enumSubAttributes(checkList1, "cmx1") )
