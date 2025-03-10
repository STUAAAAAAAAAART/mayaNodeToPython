# nurbsCurve and bezierCurve

https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/curve.html
https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/nurbsCurve.html
https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/bezierCurve.html

representation in a maya scene:
- transform node (DAG)
- shape node (DAG, requires a transform parent)

curves being open or closed (calls it periodicity/period, basically a line or a loop) seems to be managed by maya rather than being stored in the shape node itself (i.e. reverse-evaluated using the number of knots to the number of spans)

ways to create a curve:
- invoke `mc.curve()`
	- input for nurbsCurve can be control points `p=[]` or edit points `ep=[]`
	- points can be specified in object space `os=True, ws=False` or world space `os=False, ws=True`, defaults to object space
	- input for bezier requires `bezier = True`, with list of CVs and knots
		- uneven and broken tangents seem to be managed by maya rather than being stored in the shape node itself
- use `mc.createNode()` for `transform` and `nurbsCurve` or `bezierCurve` types
	- get curve data from `shape.worldspace`, and use `mc.setAttr("shape.cc", type="nurbsCurve")` to apply curve data

`mc.curve()` could be more useful for directly using joint positions for splineIK setup
- `mc.curve()` will create both the `transform` node and the shape node, but will only return the `transform` node
	- in the script: print `mc.listRelatives()` to look for child shape node instead of directly selecting by name
	- also: `mc.rename()` command this shape if needed
- `p=[], k=[]` ; or `ep=[]`
- `bezier = True` for beziers
- `degree = 3` or as desired (especially for linear, `d=1`)

`mc.createNode()` could be more convenient for just copying data for re-creation later, but requires setAttr after creation
- `mc.createNode("nurbsCurve")` will create a `transform` node if the node does not exist in the scene;
	- also this function call will only return the shape node in this case
	- in the script: always `mc.createnode("transform")` before making this shape, just to get the thing
- traverse to `om2.MPlug.getSetAttrCmds()` and reformat the list of strings

both can be used with identical results, just with different input arrangements

in the script: print commented-out second line with `mc.curve()` command?
```py
nodeList[9] = mc.createNode("transform", n="curve1", skipSelect = True)
nodeList[10] = mc.createNode("nurbsCurve", n="curveShape1", p=nodeList[9] , skipSelect = True)
# nodeList[10] = mc.curve("curve", p=[], k=[] , skipSelect = True)
# mc.setAttr(nodeList[10]+".cc", x, x, [...], ... , type="nurbsCurve" )
```



things to query:
	- wireframe colour (for left/right/center/front/back/etc)
	- user-defined attributes
	- if it's part of a splineIK chain (see if `worldSpace` is connected to one)
		- in the script: consider that the splineIK node can be processed before or after this shape node
	