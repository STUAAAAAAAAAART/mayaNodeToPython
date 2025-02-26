import maya.cmds as mc
import maya.api.OpenMaya as om2

# okay for some reason beziers use the MFnNurbsCurve extractor?

"""
maya.cmds command:
mc.curve(bezier=True) # returns the transform node, do subsequent commands to grab curve shape node
"""

# open spans are CVs -2
