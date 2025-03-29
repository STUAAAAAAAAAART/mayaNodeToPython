```py
mc.listAttr(ud=True)
# return example
# ['nuTranslate', 'nuTranslateX', 'nuTranslateY', 'nuTranslateZ', 'makeDouble3', 'makeDouble3X', 'makeDouble3Y', 'makeDouble3Z', 'nuDouble3', 'nuDouble3X', 'nuDouble3Y', 'nuDouble3Z', 'nuScalarA']

mc.attributeQuery(attr, n-node, at=True)

```

`mc.listAttr(userDefined=True)` returns a list of strings in an orderly form:
- main attributes in creation order
- if it's a vector: all subattributes will follow immediately behind the main attribute in the flat list order

```py
# ['makeDouble3', 'makeDouble3X', 'makeDouble3Y', 'makeDouble3Z', 'nuDouble3', 'nuDouble3X', 'nuDouble3Y', 'nuDouble3Z', 'nuScalarA']
#   ^main:3-long   ^sub1           ^sub2           ^sub3           ^main:3-long ^sub1         ^sub2         ^sub3         ^main:1-long
```

# enums

```py
mc.addAttr(node, ln=enumAttrName, en="uno:dos:tres:quad")


mc.addAttr('network3', ln="weirdEnum", at="enum", en="G=0:Y=1:K=400:A=50:B=1000", h=False, k=True)
print(mc.attributeQuery("weirdEnum", n='network3', listEnum=True))
# return
# ['G:Y:A=50:K=400:F:B=1000']
# note that the enum definition string is automatically sorted by end value ascending order

```
https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/CommandsPython/addAttr.html
> Flag used to specify the ui names corresponding to the enum values. The specified string should contain a colon-separated list of the names, with optional values. If values are not specified, they will treated as sequential integers starting with 0.
>
> For example:
> -enumName "A:B:C" would produce options: A,B,C with values of 0,1,2;
> -enumName "zero:one:two:thousand=1000" would produce four options with values 0,1,2,1000;
> -enumName "solo=1:triplet=3:quintet=5" would produce three options with values 1,3,5.
> 
> Note that there is a current limitation of the Channel Box that will sometimes incorrectly display an enumerated attribute's pull-down menu. Extra menu items can appear that represent the numbers inbetween non-sequential option values.
> To avoid this limitation, specify sequential values for the options of any enumerated attributes that will appear in the Channel Box. For example: "solo=1:triplet=2:quintet=3".

the only addition to the UD attribute handler is the `en=""` `enumName` flag, which is fairly easy to query and insert into the command string.

for reference: this is the pathway from openMaya to grab an `addAttr` command for the attribute

```py
# add enums before running
checkPlug = om2.MSelectionList().add("network1.letterEnum")
checkAttr = om2.MFnAttribute( checkPlug.getPlug(0).attribute() )

print(checkAttr.name)
print(checkAttr.getAddAttrCmd(longFlags =True)) # MEL OUTPUT

# example output
# addAttr -cachedInternally true -shortName "letterEnum" -longName "letterEnum" -minValue 0 -maxValue 4 -enumName "A:B:C:D:E" -attributeType "enum";

```

# attributeType vs dataType

> To add a non-double attribute the following criteria can be used to determine whether the dataType or the attributeType flag is appropriate.
> Some types, such as double3 can use either. In these cases the -dt flag should be used when you only wish to access the data as an atomic entity (eg. you never want to access the three individual values that make up a double3). In general it is best to use the -at in these cases for maximum flexibility.
>
> In most cases the -dt version will not display in the attribute editor as it is an atomic type and you are not allowed to change individual parts of it.

> All attributes flagged as "(compound)" below or the compound attribute itself are not actually added to the node until all of the children are defined (using the "-p" flag to set their parent to the compound being created). See the EXAMPLES section for more details. 

scope: always defer to the `attributeType` flag for rigging


## table of types

```
python flag syntax:

( ... at="dataType", ...)

or

( ... dt="dataType", ...)

```

| dataType | scope | subAttrs<br/>required | at | dt | description |
|:-|:-:|:-:|:-:|:-:|:-|
| bool				| s | | -at |     | boolean  |
| long				| s | | -at |     | 32 bit integer  |
| short				| s | | -at |     | 16 bit integer  |
| byte				| s | | -at |     | 8 bit integer  |
| char				| s | | -at |     | char  |
| enum				| s | | -at |     | enum  |
| float				| s | | -at |     | float  |
| double			| s | | -at |     | double  |
| doubleAngle 		| s | | -at |     | angle value  |
| doubleLinear 		| s | | -at |     | linear value  |
| compound 			| | | -at |     | compound  |
| time 				| | | -at |     | time  |
| reflectanceRGB	| | |     | -dt | reflectance  |
| reflectance 		| s | y | -at |     | reflectance (compound)  |
| spectrumRGB 		| | |     | -dt | spectrum  |
| spectrum 			| s | y | -at |     | spectrum (compound)  |
| matrix 			| s | | -at\* | -dt | 4x4 double matrix  |
| fltMatrix 		| s | | -at |     | 4x4 float matrix  |
| float2 			| s | y | -at | -dt | 2 floats  |
| float3 			| s | y | -at | -dt | 3 floats  |
| double2 			| s | y | -at | -dt | 2 doubles  |
| double3 			| s | y | -at | -dt | 3 doubles  |
| long2 			| s | y | -at | -dt | 2 32-bit integers  |
| long3 			| s | y | -at | -dt | 3 32-bit integers  |
| short2 			| s | y | -at | -dt | 2 16-bit integers  |
| short3 			| s | y | -at | -dt | 3 16-bit integers  |
| message 			| | | -at |     | message (no data)  |

\* not documented in official docs, but maya accepted the command with that string with the `at` flag

note:
- use `float3` for colour attributes: the `usedAsColor=True` flag changes the attribute into a colour slider.
	- documentation says `double3` would be applicable, but maya did not accept that for the `usedAsColor` flag.
	- reflectance and spectrum attributes default to `uac=True`

| dataType | at | dt | description |
|:-|:-:|:-:|:-|
| doubleArray |  | -dt | array of doubles  |
| floatArray |  | -dt | array of floats  |
| Int32Array |  | -dt | array of 32-bit ints  |
| vectorArray |  | -dt | array of vectors  |
| nurbsCurve |  | -dt | nurbs curve  |
| nurbsSurface |  | -dt | nurbs surface  |
| mesh |  | -dt | polygonal mesh  |
| lattice |  | -dt | lattice  |
| pointArray  |  | -dt | array of double 4D points  |
| string |  | -dt | string  |
| stringArray |  | -dt | array of strings  |


# vectors

```py

testNet = 'network2'

mc.addAttr(testNet, ln="nuDouble3", attributeType="double3", h=False, k=True)
mc.addAttr(testNet, ln="nuTranslate", attributeType="double3", h=False, k=True)
mc.addAttr(testNet, ln="nuTranslateX", attributeType="double", p="nuTranslate", h=False, k=True)
mc.addAttr(testNet, ln="nuTranslateY", attributeType="double", p="nuTranslate", h=False, k=True)
mc.addAttr(testNet, ln="nuTranslateZ", attributeType="double", p="nuTranslate", h=False, k=True)
mc.addAttr(testNet, ln="makeDouble3", attributeType="double3", h=False, k=True)
mc.addAttr(testNet, ln="makeDouble3X", attributeType="double", p="makeDouble3", h=False, k=True)
mc.addAttr(testNet, ln="makeDouble3Y", attributeType="double", p="makeDouble3", h=False, k=True)
mc.addAttr(testNet, ln="makeDouble3Z", attributeType="double", p="makeDouble3", h=False, k=True)
mc.addAttr(testNet, ln="nuDouble3X", attributeType="double", p="nuDouble3", h=False, k=True)
mc.addAttr(testNet, ln="nuDouble3Y", attributeType="double", p="nuDouble3", h=False, k=True)
mc.addAttr(testNet, ln="nuDouble3Z", attributeType="double", p="nuDouble3", h=False, k=True)
mc.addAttr(testNet, ln="nuScalarA", attributeType="double", h=False, k=True)

print(mc.listAttr(testNet, userDefined=True))
# return
# ['nuTranslate', 'nuTranslateX', 'nuTranslateY', 'nuTranslateZ', 'makeDouble3', 'makeDouble3X', 'makeDouble3Y', 'makeDouble3Z', 'nuDouble3', 'nuDouble3X', 'nuDouble3Y', 'nuDouble3Z', 'nuScalarA']
# note that:
# - vector attributes REQUIRE SUBATTRIBUTES TO BE DECLARED VIA mc.addAttr(p=mainAttr) TO WORK
# - return list for mc.listAttr always order subAttrs right next to the main attribute that owns them
# - the return list is flat and will require hop-aheads when processing

```

# colour attribute

```py
mc.addAttr('network3', ln="magicFloat3", at="float3", usedAsColor=True, h=False, k=True)
mc.addAttr('network3', ln="magicFloat3R", attributeType="float", p="magicFloat3", h=False, k=True)
mc.addAttr('network3', ln="magicFloat3G", attributeType="float", p="magicFloat3", h=False, k=True)
mc.addAttr('network3', ln="magicFloat3B", attributeType="float", p="magicFloat3", h=False, k=True)

print(mc.attributeQuery("magicFloat3", n="network3", uac=True))
```

would be useful for a network node to keep sepatare attributes made of key colours for use in rigs, to quickly change wireframe colours of groups of controls

# typed

where `mc.addAttr(dt=dataType)` is used, and `mc.attributeQuery(at=True)` returns `"typed"`

```py
mc.addAttr('network3', ln="strangeAttr", dt="nurbsCurve", h=False, k=True)
print(mc.attributeQuery("strangeAttr", n="network3", attributeType = True))
# return:
# "typed"
print(mc.getAttr("network3.strangeAttr", type=True))
# return:
# "nurbsCurve"
```

script won't be covering `dt` flags for this case, but i can see a use case for holding a massive network node full of premade `nurbsCurve` data to quickly touch nurbsCurve shape nodes in the editor during the rig control design process.
> i've previously used a separate maya file with common control shapes, and i think making a script to generate the singleton `network` node MIGHT work better. we'll see
>
> also i've just realised a `network` node with a `nurbsCurve` attribute would be the most compact representation of holding `nurbsCurve` data without having to create a transform-and-shape curve DAG object... i will have to look into the rammifications of this

# scope reduction

realistically speaking in context to rig controls: deal with the following:
- vectors
- scalars (ints, floats/doubles)
- bools
- enums

while compound attributes has a chance of working, the script at initial scope DOES NOT cover for cases where its children are compound attributes themselves. assuming its child attributes are NOT compound attributes (like vectors) would not cover the back half of its use case, so this will not be covered (or to be added in the future as and when the need arises)

anything else will be printed as a comment. multi-attributes isn't covered for now