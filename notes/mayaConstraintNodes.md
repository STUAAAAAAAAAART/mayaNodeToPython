# constraint nodes in maya and differences

## the commands

common flags in commands:

- `offset`
	- add a numeric offset relative to the result constraint
	- does not exist on `parentConstraint`
	- attributes affected (this node):
		- `offset`; .x .y .z
- `maintainOffset`
	- adds a numeric offset to maintain its original transfrom prior to constaining
	- does not exist on `parentConstraint`
	- attributes affected (this node):
		- `offset`; .x .y .z
- `skip`
	- or `skipTranslate` and `skipRotate` for `mc.parentConstraint()`
	- skips making connection to specific axes on driven/child transform object
	- attributes affected (this node), where applicable:
		- `.constraintTranslate` ; .x .y .z
		- `.constraintRotate` ; .x .y .z
		- `.constraintScale` ; .x .y .z
- `remove` and/or repeated use of command with same child/driven
	- removes parent/driver from `.target[]` in constraint node
	- repeated use of creation command adds parent/driver to next index of `.target[]`
	- attributes affected (this node):
		- `.target[n]` and all its subattributes
		- to check: user-defined attribute tied to `.target[n].targetWeight`

queries:
- `targetList`
	- returns names of targets/drivers/parents
- `weightAliasList`
	- returns connection to attribute that's connected to the target's `weight` attribute
	- WARNING: this will also return the attribute connected to it coming from another node, but without the name of the node.
		- **DO NOT USE THIS TO QUERY TRUE CONNECTIONS.**
	- to properly check what's connected to `targetWeight`: `mc.listConnections()` on the attribute, and see if it originates from another node

## the nodes
> Although the all the constraint nodes inherit from transform, they do not actively use any of the attributes from transform. 

common attributes connected by command:
- `target[n]` and its subattributes
	- to find upstream target(s):
		- query `target[n].targetParentMatrix`
		- or use `targetList` in command query mode
	- driver/parent's attributes will be connected to this attribute
	- if multiple parents or another parent is added by same command, new additions are connected on the next empty slots
- `constraint` attributes
	- to find downstream driven transform:
		- query `.constraintParentInverseMatrix`
	- driven/child's transforms will be driven by these according to type of constraint

attributes of note:
- `offset`
	- adjusted by constraint creation command with `maintain offset` flag
	- `parentConstaint` does not have this
- `target[n].targetWeight`
	- connected and controlled by driver, but by default it's connected to a user-defined attribute on self, automatically created by the constraint command
- `restTranslate`, `restRotate`, `restScale`
	- activated by `enableRestPosition`
		- https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/constraint.html
	- value assigned to driven transforms when all other weights are zero
- `aimVector`, `upVector`, `worldUpType`, `worldUpMatrix`, `worldUpVector`
	- just for `aimConstraint`
	- defines the normal vector guide of a foward vector aim
	- see: https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/aimConstraint.html

## poleVectorConstraint

> poleVectorConstraint is a variation on a pointConstraint that is designed explicitly to constrain the pole vector of an ikRPsolver ikHandle to follow one or more target objects

# scope reduction

- manually recording all changed values would be overkill, considering most of these values are enumerated according to the transforms involved
- evaluating actually "user-defined" `dynamic attributes` would be messy as the creation command makes their own "user-defined" attributes.
	- the only thing to monitor is where the target weight is connected to. if connected to self.name_W0, leave it as it is. otherwise make the command to connect to it 
	- (during the rigging process) it'd make more sense to put `dynamic attributes` elsewhere, either on controls or a `network` node
- where applicable: enable rest will be always on, as a means to define a zero state.
	- if this is disabled, the driven/constrained object will stop at wherever it was last at when weights are set to zero
	- this is unpredictable, and controlling through this attribute does not account for other transforms not covered by the constraints
	- (during the rigging process) the ideal case is to use constraints on a downstream driver, and then blend between this result and the other controllers
- while every `constraint` node contains a transform (due to constraints being a subclass of the transform node), the transform and its connections will be ignored
	- (during the rigging process) use a `transform` node or directly make a transform matrix `composeMatrix`, to make things more explicit on the scene hierachy and the node editor. also as a means to survive a deletion request/action of the constraint

the `aimConstraint` node will be covered for the sake of completion, although consider using `aimMatrix` first, especially if most of the rig is already maths and matrix driven in the first place

## creation command flags

query flags require `q=True`

**common flags**

|flag|sN|query|flag type|parent|aim|orient|point|scale|poleVector|
|:-|:-|:-:|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|name |`n`|query| create, edit					|O|O|O|O|O|O|
|offset|`o`|query| create, edit					| |O|O|O|O| |
|layer |`l`| |create, edit						|O|O|O|O|O|O|
|maintainOffset |`mo`| |create					|O|O|O|O|O| |
|remove |`rm`| |edit							|O|O|O|O|O|O|
|targetList |`tl`|query| 						|O|O|O|O|O|O|
|weight = 1.0 |`w`|query| create, edit			|O|O|O|O|O|O|
|weightAliasList |`wal`|query| 					|O|O|O|O|O|O|
|skipRotate |`sr`| |create, multiuse			|O| | | | | |
|skipTranslate |`st`| |create, multiuse			|O| | | | | |
|skip|`sk`| | create, edit, multiuse			| |O|O|O|O| |

**specific flags**


|flag|sN|query|flag type|parent|aim|orient|point|scale|poleVector|
|:-|:-|:-:|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|scaleCompensate|`sc`| |create, edit			| | | | |O| |
|createCache |`cc`| |edit						|O| |O| | | |
|deleteCache |`dc`| |edit						|O| |O| | | |
|decompRotationToChild |`dr`| |create			|O| | | | | |
|aimVector|`aim`|query| create, edit			| |O| | | | |
|upVector|`u`|query| create, edit				| |O| | | | |
|worldUpObject|`wuo`|query| create, edit		| |O| | | | |
|worldUpType|`wut`|query| create, edit			| |O| | | | |
|worldUpVector|`wu`|query| create, edit			| |O| | | | |

### attributes

**attributes pre-evaluated by command**

- `.offset` <- from maintain offset flag
	- set `maintainOffset` boolean if this value is not zero/default
- rest positions `restTranslate`, `restRotate`, `restScale`
	- set `enableRestPosition` boolean if this value is not zero/default

**dynamic attributes and weightALiasList**

when a constraint is made, the command automatically makes a dynamic attribute connected to the target's weight attribute

this is done because in the attribute editor, the targets are not exposed and the only way to control a target is though this dynamic attribute

the node editor will still expose everything on the target's side, but it appears that maya would like to manage this for the user as much as it can (e.g. to add a second target or more, the command is run on the selection including the new target(s) and the existing driven object)


**constraints**

|attribute|parent|aim|orient|point|scale|poleVector|
|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|.aimVector [x,y,z]					| |O| | | | |
|.upVector [x,y,z]					| |O| | | | |
|.worldUpMatrix						| |O| | | | |
|.worldUpType						| |O| | | | |
|.worldUpVector [x,y,z]				| |O| | | | |
|.lastTargetRotate [x,y,z]			|O| |O| | | |
|.inverseScale [x,y,z]				| |O|O| | | |
| ------- |parent|aim|orient|point|scale|poleVector|
|.offset [x,y,z]					| |O|O|O|O|O|
|.lockOutput						|O|O|O|O|O|O|
|.enableRestPosition				|O|O|O|O|O|O|
|.restTranslate [x,y,z]				|O| | |O| |O|
|.restRotate [x,y,z]				|O|O|O| | | |
|.restScale [x,y,z]					| | | | |O| |
|.constraintParentInverseMatrix		|O|O|O|O|O|O|
|.constraintTranslate [x,y,z]		|O|O| | | | |
|.constraintOffsetPolarity			| | | |O| |O|
|.constraintRotate [x,y,z]			|O| |O| | | |
|.constraintRotateOrder				|O|O|O| | | |
|.constraintRotatePivot [x,y,z]		|O|O| |O| |O|
|.constraintJointOrient [x,y,z]		|O|O|O| | | |
|.constraintRotateTranslate [x,y,z]	|O|O| |O| |O|
|.constraintScale [x,y,z]			| | | | |O| |
|.constraintScaleCompensate			| | | | |O| |

**targets**

|attribute|parent|aim|orient|point|scale|poleVector|
|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|.target[n]									|O|O|O|O|O|O|
|.target[].targetWeight						|O|O|O|O|O|O|
|.target[].targetParentMatrix				|O|O|O|O|O|O|
|.target[].targetTranslate [x,y,z]			|O|O| |O| |O|
|.target[].targetRotate [x,y,z]				|O| |O| | | |
|.target[].targetScale [x,y,z]				|O| | | |O| |
|.target[].targetOffsetTranslate [x,y,z]	|O| | | | | |
|.target[].targetOffsetRotate [x,y,z]		|O| | | | | |
|.target[].targetScaleCompensate			|O| | | | | |
|.target[].targetInverseScale [x,y,z]		|O| | | | | |
|.target[].targetRotatePivot [x,y,z]		|O|O| |O| |O|
|.target[].targetRotateTranslate [x,y,z]	|O|O| |O| |O|
|.target[].targetJointOrient [x,y,z]		|O| |O| | | |
|.target[].targetRotateOrder				|O| |O| | | |
|.target[].targetRotateCached [x,y,z]		|O| |O| | | |

**other attributes**

attributes may be mentioned again here to disambiguate similarly named attributes

|attribute|parent|aim|orient|point|scale|poleVector|
|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|.pivotSpace							| | | | | |O|
|.constraintScaleCompensate				| | | | |O| |
|.scaleCompensate						| |O|O| | | |
|.useOldOffsetCalculation				| |O|O| | | |
|.interpCache							|O| |O| | | |
|.interpType							|O| | | | | |
|.rotationDecompositionTarget [x,y,z]	|O| | | | | |
|.useDecompositionTarget				|O| | | | | |

----

### parentConstraint
- .constraintJointOrient [x,y,z]
- .constraintParentInverseMatrix
- .constraintRotate [x,y,z]
- .constraintRotateOrder
- .constraintRotatePivot [x,y,z]
- .constraintRotateTranslate [x,y,z]
- .constraintTranslate [x,y,z]
- .interpCache
- .interpType
- .lastTargetRotate [x,y,z]
- .restRotate [x,y,z]
- .restTranslate [x,y,z]
- .rotationDecompositionTarget [x,y,z]
- .target
	- .targetParentMatrix
	- .targetWeight
	- .targetRotateCached [x,y,z]
	- .targetTranslate [x,y,z]
	- .targetRotatePivot [x,y,z]
	- .targetRotateTranslate [x,y,z]
	- .targetOffsetTranslate [x,y,z]
	- .targetRotate [x,y,z]
	- .targetRotateOrder
	- .targetJointOrient [x,y,z]
	- .targetOffsetRotate [x,y,z]
	- .targetScaleCompensate
	- .targetInverseScale [x,y,z]
	- .targetScale [x,y,z]
- .useDecompositionTarget

### aimConstraint
- .aimVector [x,y,z]
- .scaleCompensate
- .offset [x,y,z]
- .constraintJointOrient [x,y,z]
- .constraintParentInverseMatrix
- .constraintRotateOrder
- .constraintRotatePivot [x,y,z]
- .constraintRotateTranslate [x,y,z]
- .constraintTranslate [x,y,z]
- .inverseScale [x,y,z]
- .restRotate [x,y,z]
- .target
	- .targetTranslate [x,y,z]
	- .targetRotatePivot [x,y,z]
	- .targetRotateTranslate [x,y,z]
	- .targetParentMatrix
	- .targetWeight
- .upVector [x,y,z]
- .useOldOffsetCalculation
- .worldUpMatrix
- .worldUpType
- .worldUpVector [x,y,z]

### orientConstraint
- .scaleCompensate
- .offset [x,y,z]
- .constraintJointOrient [x,y,z]
- .constraintParentInverseMatrix
- .constraintRotate [x,y,z]
- .constraintRotateOrder
- .interpCache
- .lastTargetRotate [x,y,z]
- .inverseScale [x,y,z]
- .restRotate [x,y,z]
- .target
	- .targetRotate [x,y,z]
	- .targetRotateOrder
	- .targetJointOrient [x,y,z]
	- .targetParentMatrix
	- .targetWeight
	- .targetRotateCached [x,y,z]
- .useOldOffsetCalculation

### pointConstraint
- .offset [x,y,z]
- .constraintOffsetPolarity
- .constraintParentInverseMatrix
- .constraintRotatePivot [x,y,z]
- .constraintRotateTranslate [x,y,z]
- .constraintTranslate [x,y,z]
- .restTranslate [x,y,z]
- .target
	- .targetTranslate [x,y,z]
	- .targetRotatePivot [x,y,z]
	- .targetRotateTranslate [x,y,z]
	- .targetParentMatrix
	- .targetWeight

### scaleConstraint
- .offset [x,y,z]
- .constraintParentInverseMatrix
- .constraintScale [x,y,z]
- .constraintScaleCompensate
- .restScale [x,y,z]
- .target
	- .targetScale [x,y,z]
	- .targetParentMatrix
	- .targetWeight

