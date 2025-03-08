attributes in **bold** are attributes to read/record in rigging script<br/>
(the scope is managing transforms, and visibility in maya's viewport)

recording node connections should override attribute recording if a connection is detected

https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/dagNode.html <br/>
https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/transform.html <br/>
https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/composeMatrix.html <br/>

## dagNode

physical attributes

- boundingBox (12)
	- boundingBoxMin (float3)
		- xyz
	- boundingBoxMax (float3)
		- xyz
	- boundingBoxSize (float3)
		- xyz
- center (float3)

draw overrides<br/>
seems like it's messing with display layers in the backend

- drawOverride (14)
	- overrideDisplayType (enum)
	- overrideLevelOfDetail (enum)
	- overrideShading (bool)
	- overrideTexturing (bool)
	- overridePlayback (bool)
	- overrideEnabled (bool)
	- overrideVisibility (bool)
	- hideOnPlayback (bool)
	- overrideRGBColors (bool)
	- overrideColor (unsigned char 0-7)
	- overrideColorRGB (float3)
		- overrideColorR (float)
		- overrideColorG (float)
		- overrideColorB (float)

ghosting attributes

- ghostColorPost (3)
- ghostColorPre (3)
- ghostCustomSteps (3)
- ghostDriver
- ghostFrames
- ghostOpacityRange (2)
- ghostUseDriver
- ghosting
- ghostingMode

node display

- instObjGroups (4)
- intermediateObject
- lodVisibility
- renderInfo (3)
- renderLayerInfo (3)
- selectionChildHighlighting
- template
- visibility

precomputed matrices

- inverseMatrix
- matrix
- parentInverseMatrix
- parentMatrix
- worldInverseMatrix
- worldMatrix

node wireframes<br/>
wireframe colour is managed by maya, use the wireframe command `color(node, [r,g,b]` instead of `setAttr(node.wfcc, r,g,b)`

- **useObjectColor** (enum 0-2)
- **objectColor** (short, 0-7)
- **objectColorRGB** (float3)
- **wireColorRGB** (float3)

not documented:
- **useOutlinerColor** (bool)
- **outlinerColor** (float3)

## transform

scene object attributes
- dynamics
- geometry

viewport manipulation attributes

- displayHandle
- displayLocalAxis
- displayRotatePivot
- displayScalePivot
- specifiedManipLocation (enum, 0-7)
- selectHandle (3)
- showManipDefault

hierachy attribute<br/>
avoid using in active transforms if possible, try representing with nodes to *.offsetParentMatrix*

- inheritsTransform

transform limits

- **maxRotLimit** (float3, angle)
- **maxRotLimitEnable** (bool3)
- **maxScaleLimit** (float3)
- **maxScaleLimitEnable** (bool3)
- **maxTransLimit** (float3)
- **maxTransLimitEnable** (bool3)

<nbsp/>

- **minRotLimit** (float3, angle)
- **minRotLimitEnable** (bool3)
- **minScaleLimit** (float3)
- **minScaleLimitEnable** (bool3)
- **minTransLimit** (float3)
- **minTransLimitEnable** (bool3)

precomputed transforms
- xformMatrix

pivots
- rotateAxis (3)
- rotateOrder
- rotatePivot (3)
- rotatePivotTranslate (3)
- scalePivot (3)
- scalePivotTranslate (3)
- transMinusRotatePivot (3)

transforms

- **offsetParentMatrix** (mat4)
- **rotate** (float3, angle)
- rotateQuaternion (float4)
- rotationInterpolation (enum, depreciated)
- **scale** (float3)
- shear (float3)
- **translate** (float3)


## composeMatrix

- **inputQuat** (float4)
- **inputRotate** (float3, angle)
- **inputRotateOrder** (enum 0-5)
- **inputScale** (float3)
- **inputShear** (float3)
- **inputTranslate** (float3)
- **useEulerRotation** (bool)