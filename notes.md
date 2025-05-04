# notes and questions and clarifications etc
when i can think of a subtitle i'll put it in here

## why code-write the script to enumerate a range rather than appending a list?
```py
# (...)
jointList = [None] * 3

nodeList[0] = mc.createNode("composeMatrix", n="cmx_noFlipOffset", skipSelect = True)
nodeList[1] = mc.createNode("composeMatrix", n="cmx_testRotate", skipSelect = True)
nodeList[2] = mc.createNode("multMatrix", n="multMatrix4", skipSelect = True)
# (...)
```
> because i want to be able to point to each node directly after the script is printed, without having to remember or figure out the would-be index of a node from reading the list. also if items in the list were to be deleted in-text after the fact, gaps would not affect indexing of the list
>
> this is very especially difficult to juggle in mind, if all the commands were, say, like the following and you'd want something in the middle (or will be removing a few nodes and getting other nodes):
```py
# (...)
nodeList = []

nodeList.append( mc.createNode("composeMatrix", n="cmx_noFlipOffset", skipSelect = True) )
nodeList.append( mc.createNode("composeMatrix", n="cmx_testRotate", skipSelect = True) )
nodeList.append( mc.createNode("multMatrix", n="multMatrix4", skipSelect = True) )
# (...)
```
> the aim of the output is to be human-editable, so having each item in the nodeList be directly assigned an index means that i could edit, reorder, or delete values in an index, and the rest of the list are still maintained. this is important for further commands below using items in the `nodeList` for inputs

## why not make it write a script to use a loop to handle all the mc.createNode() commands?

> again, i'm wanting the flexibiity to reorder the operations while editing the output to containerise a rigging operation. it's a lot easier this way to ensure something gets made and set up absolutely before the rest or a particular node, and also a tangible way to merge two node operations into one (e.g. merging the creation of two network nodes holding two separate attributes into one after the output)

## why the use of openMaya for selection instead of mc.ls(sl=True)?

> openMaya's `MSelectionList` returns a pointer to the DG/DAG object, which allows me to rename a node without having to worry about reflecting the name change elsewhere in the other variables or lists
>
> it's less relevant here in the main script stage, because of the runtime-only nature of the script (i.e. states aren't important or remembered between runs), but it's more of a force of habit i'd like to keep as much as i can

## why not use openMaya to create nodes?

> this is an area i'm still very unfamiliar with, but as far as i understand:
>
> changes to the DAG/DG (the scene) through openMaya is direct and does not write to the undo queue. there are specific functions to make the commands to be registered in maya's history queue, but that is an undertaking i would like to undertake in a proper plugin project rather than do it here
>
> so the use of openMaya has mostly been about handling objects in lists and querying attributes or data (i'm reading there are even functions like querying the closest point on a curve without resorting to making a node in the scene for that, so that opens the possibility for openMaya-based parametric models)

## why did you createNode a curve, assign it two points, then rebuild the curve with the actual points later?

```py
curveTransformShape = [None,None]
curveTransformShape[0] = mc.createNode('transform', n=curveTransform)
curveTransformShape[1] = mc.createNode('nurbsCurve', n=curveShape, p=curveTransformShape[0])
mc.setAttr(curveTransformShape[1]+'.cc', 3,1,0,False,3,(0,0,0,1,1,1),6,4,(0,0,0),(0,0,0),(0,0,0),(0,0,0), type="nurbsCurve")
	# this is a cubic curve with two edit points at (0,0,0), applied temporarily to make it a valid cubic curve
mc.curve(curveTransformShape[0], replace=True, ep=jointAsEPs, d=3)
```

> if i were to createNode a nurbsCurve without giving it any points, then use curve(replace=True) with a desired curve, maya crashes because there is no valid curve data being held in that shape node
>
> also methodologically speaking: yes it would make sense for the curve data to be copied and applied directly (i'm doing this for curve controller shapes), but in specifc cases like drawing a curve that passes through a joint chain (especially for splineIK), using the curve() command would be much easier because the command has a flag that accepts edit points (points on a curve) instead of control vertices (points defining a curve that may not be on the curve itself)
>
> directly applying curve data can only work with control vertices, so that is a solution that does not fit all tasks that would require passing a curve through specific points in space
>
> admittedly mathematical curve definitions is one of the many major gaps in my knowledge, and i am really leaning hard on maya's implementations to solve going between control vertices and edit points. i do wish to be able to get a handle on this one day, so that i could do a platform/engine-agnostic implementation across more programs and environments

## is there a difference between the attributes nurbsCurveShape.worldspace and nurbsCurveShape.local for nurbsCurves?

> there is!!! (this is relating to using `MPlug.getSetAttrCmds()` on the curve shape's `.worldspace` and `.local` attributes, to reverse and inject into a new curve object's shape)
>
> the curve data being returned from both attributes are different: the worldSpace data is relative to the scene, and the local data is relative to the object itself
>
> for purposes of control re-creation or duplication or applying a shape from pre-saved data, you'd want to query `.local`, as the curve data stored on nurbsCurve shapes are always in local space.
>
> `.worldSpace` would help if the curve so happens to be around `[0,0,0]` but has transforms applied to it, possibly in cases where a controller shape is being designed


## why is the script not fully characterising constraint nodes? where are the connection commands for it?

> i'm using the respective creation commands to create constraint nodes and connections, as this is too many to keep track of.
>
> in addition, the scope of the constraint handler is greatly reduced in order to manage scope, as in most cases the constraints are created then forgotten (i.e. it only deals with one driver/target object and one driven/constraint object). so this script doesn't do much more than enumerating the single creation command, although this isn't set in stone and may be added on in the future

## why is everything in a singleton script?!

> i'm looking to run this either in the script editor or as a shelf command, and i want to minimise having to deal with relative script imports (either in maya's project environment or the default environment)
>
> it's an extremely long read, but it's the only simplest way i can think of that would be a copy-paste-and-run solution
>
> also it's easier to troubleshoot with the variables not declared in a function, as i can just recall a variable to show what's being held at point of the script halting in an error.

## you know pass does nothing, right?

> yes i know, it's there to mark the end of very long conditionals or loops for my eyes