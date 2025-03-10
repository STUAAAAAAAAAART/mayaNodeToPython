import maya.cmds as mc
import maya.api.OpenMaya as om2

# okay for some reason beziers use the MFnNurbsCurve extractor?

"""
required reference
https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=__Nodes_index_html

maya.cmds command:
mc.curve(bezier=True) # returns the transform node, do subsequent commands to grab curve shape node


MEL creation command example:
curve -bezier -d 3 -p -8 0 9 -p -13 0 7 -p -14 0 -4 -p -9 0 -7 -p -4 0 -10 -p 0 0 -5 -p 0 0 0 -p 0 0 5 -p 3 0 10 -p 7 0 8 -p 11 0 6 -p 14 0 -5 -p 9 0 -9 -k 0 -k 0 -k 0 -k 1 -k 1 -k 1 -k 2 -k 2 -k 2 -k 3 -k 3 -k 3 -k 4 -k 4 -k 4 ;

curve -bezier
	-d 3
	
	-p -8 0 9
	-p -13 0 7

	-p -14 0 -4
	-p -9 0 -7
	-p -4 0 -10
	
	-p 0 0 -5
	-p 0 0 0
	-p 0 0 5
	
	-p 3 0 10
	-p 7 0 8
	-p 11 0 6
	
	-p 14 0 -5
	-p 9 0 -9

	-k 0 -k 0 -k 0 -k 1 -k 1 -k 1 -k 2 -k 2 -k 2 -k 3 -k 3 -k 3 -k 4 -k 4 -k 4
//	knots 0 0 0 1 1 1 2 2 2 3 3 3 4 4 4	

	;

"""

# open spans are CVs -2

