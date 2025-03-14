# constraint nodes in maya and differences

## the commands

common flags in commands:

- `offset`
	- attributes affected (this node):
- `maintainOffset`
	- attributes affected (this node):
- `skip`
	- or `skipTranslate` and `skipRotate` for `mc.parentConstraint()`
	- skips making connection to specific axes on driven/child transform object
	- attributes affected (this node), where applicable:
		- `.constraintTranslate` ; .x .y .z
		- `.constraintRotate` ; .x .y .z
		- `.constraintScale` ; .x .y .z
- `targetList`
	- returns names of targets/drivers/parents
- `remove` and/or repeated use of command with same child/driven
	- removes parent/driver from `.target[]` in constraint node
	- repeated use of creation command adds parent/driver to next index of `.target[]`
	- attributes affected (this node):
		- `.target[n]` and all its subattributes
		- to check: user-defined attribute tied to `.target[n].targetWeight`


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

attributes to keep note for recreation command:
- `offset`
	- adjusted by constraint creation command with `maintain offset` flag
	- `parentConstaint` does not have this
- `target[n].targetWeight`
	- connected and controlled by driver, but by default it's connected to a user-defined attribute on self, automatically created by the constraint command
- attributes pre-evaluated by constraint command (e.g. when maintain offset is requested):
	- needs checking...
- `restTranslate`, `restRotate`, `restScale`
	- needs checking...
- `aimVector`, `upVector`, `worldUpMatrix`, `worldUpType`, `worldUpVector`
	- just for aimConstraint
	- needs checking...

## poleVectorConstraint

> poleVectorConstraint is a variation on a pointConstraint that is designed explicitly to constrain the pole vector of an ikRPsolver ikHandle to follow one or more target objects
- .pivotSpace

### attributes

**attributes pre-evaluated by maintain offsets**

needs checking...

**constraints**

|attr/constraint|parent|aim|orient|point|scale|poleVector|
|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|.aimVector [x,y,z]					| |O| | | | |
|.upVector [x,y,z]					| |O| | | | |
|.lastTargetRotate [x,y,z]			|O| |O| | | |
|.offset [x,y,z]					| |O|O|O|O|O|
|.restTranslate [x,y,z]				|O| | |O| |O|
|.restRotate [x,y,z]				|O|O|O| | | |
|.restScale [x,y,z]					| | | | |O| |
|.inverseScale [x,y,z]				| |O|O| | | |
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

|attr/constraint|parent|aim|orient|point|scale|poleVector|
|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|.target[n]									|O|O|O|O|O|O|
|.target[].targetWeight						|O|O|O|O|O|O|
|.target[].targetParentMatrix				|O|O|O|O|O|O|
|.target[].targetRotateCached [x,y,z]		|O| |O| | | |
|.target[].targetTranslate [x,y,z]			|O|O| |O| |O|
|.target[].targetRotatePivot [x,y,z]		|O|O| |O| |O|
|.target[].targetRotateTranslate [x,y,z]	|O|O| |O| |O|
|.target[].targetOffsetTranslate [x,y,z]	|O| | | | | |
|.target[].targetRotate [x,y,z]				|O| |O| | | |
|.target[].targetRotateOrder				|O| |O| | | |
|.target[].targetJointOrient [x,y,z]		|O| |O| | | |
|.target[].targetOffsetRotate [x,y,z]		|O| | | | | |
|.target[].targetScaleCompensate			|O| | | | | |
|.target[].targetInverseScale [x,y,z]		|O| | | | | |
|.target[].targetScale [x,y,z]				|O| | | |O| |

**other attributes**

|attr/constraint|parent|aim|orient|point|scale|poleVector|
|:-|:-:|:-:|:-:|:-:|:-:|:-:|
|.interpCache							|O| |O| | | |
|.interpType							|O| | | | | |
|.rotationDecompositionTarget [x,y,z]	|O| | | | | |
|.useDecompositionTarget				|O| | | | | |
|.scaleCompensate						| |O|O| | | |
|.useOldOffsetCalculation				| |O|O| | | |
|.worldUpMatrix							| |O| | | | |
|.worldUpType							| |O| | | | |
|.worldUpVector [x,y,z]					| |O| | | | |

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

