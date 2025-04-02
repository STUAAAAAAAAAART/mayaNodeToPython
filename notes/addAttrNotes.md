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

# compound attributes

`mc.listAttr(ud=True)` outputs a list where all the subattributes follows the main attribute, so there shouldn't be any case where a parenting flag would target an attribute that hasn't been created yet.

combine the use of `mc.listAttr(ud=True)` and `mc.attributeQuery(lp=True)`, and the command list should practically build itself without much pain

# code snip

if only maya had a native `getAddAttrCmds()` function for enitre DG nodes...

(no not the `om2.MFnAttribute().getAddAttrCmds()` one)

```py
nodeName = "network2"

newNode = "network3"

for attr in udList:
	udFlags = ""
	getAttrType = mc.attributeQuery(attr, n=nodeName, at=True)

	# has custom shortName
	getShortName = mc.attributeQuery(attr, n=nodeName, sn=True)
	if attr != getShortName: # shortName defaults to longName if not set
		udFlags += f", sn='{getShortName}'"
	# has custom Nice name
		# skipping this for now. checking this will involve replicating maya's Nice Name syntax

	# parent of main Attr
	getParent = mc.attributeQuery(attr, n=nodeName, lp=True)
	if getParent:
		udFlags += f", p='{getParent[0]}'"

	# float3: is this attribute a colour representation?
	if mc.attributeQuery(attr, n=nodeName, usedAsColor=True):
		udFlags += ", uac=True"
	elif getAttrType == "float3":
		udFlags += ", uac=False" # leave the flag in there just as a reminder
	# main compound attribute flag
	if getAttrType == "compound":
		udFlags += f", nc='{mc.attributeQuery(attr, n=nodeName, nc=True)[0]}'"
	# enum attribute: enum value string flag
	if getAttrType == "enum":
		udFlags += f", en='{mc.attributeQuery(attr, n=nodeName, listEnum=True)[0]}'"	

	# insert space as attempt fot neat formatting
	if getParent == None:
		udFlags += f"{' '*(len(attr)+6)}"
	udFlags += "  \t" # spacer for ranges and attribute limiters

	# range flags
	# the following compound or attribute types do not store limits firsthand:
	if getAttrType not in ["compound","typed","bool","enum", "matrix", "fltMatrix", "char", "time", "message", "reflectance", "spectrum"]:
		# soft range (slider limits)
		if mc.attributeQuery(attr, n=nodeName, softMinExists = True):
			udFlags +=  ", hasSoftMinValue = True"
			udFlags += f", softMinValue = {mc.attributeQuery(attr, n=nodeName, softMin = True)}"
		if mc.attributeQuery(attr, n=nodeName, softMaxExists = True):
			udFlags +=  ", hasSoftMaxValue = True"
			udFlags += f", softMaxValue = {mc.attributeQuery(attr, n=nodeName, softMax = True)}"
		# hard range (hard limits)
		if mc.attributeQuery(attr, n=nodeName, minExists = True):
			udFlags +=  ", hasMinValue = True"
			udFlags += f", minValue = {mc.attributeQuery(attr, n=nodeName, softMin = True)}"
		if mc.attributeQuery(attr, n=nodeName, minExists = True):
			udFlags +=  ", hasMaxValue = True"
			udFlags += f", maxValue = {mc.attributeQuery(attr, n=nodeName, softMin = True)}"

	# hidden?
	holdBool = mc.attributeQuery(attr, n=nodeName, hidden = True)
	udFlags += f", hidden = {'True'*holdBool}{'False'*(not holdBool)}"
	# connection settings
	holdBool = mc.attributeQuery(attr, n=nodeName, readable = True)
	udFlags += f", readable = {'True'*holdBool}{'False'*(not holdBool)}"
	holdBool = mc.attributeQuery(attr, n=nodeName, writable = True)
	udFlags += f", writable = {'True'*holdBool}{'False'*(not holdBool)}"
	# animatable?
	holdBool = mc.attributeQuery(attr, n=nodeName, keyable = True)
	udFlags += f", keyable = {'True'*holdBool}{'False'*(not holdBool)}"

	# attributeType or dataType?
	if getAttrType == "typed":
		objAttr = f"{nodeName}.{attr}"
		getAttrType = f", dt='{mc.getAttr(objAttr, type=True)}'"
	else:
		getAttrType=f", at='{getAttrType}'"
	print(f"mc.addAttr({newNode}, ln='{attr}'{getAttrType}{udFlags})")

# just a quick demonstration of linking compound attributes
"""
mc.addAttr('network3', ln='nuTranslate', at='double3'                    	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuTranslateX', at='double', p='nuTranslate'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuTranslateY', at='double', p='nuTranslate'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuTranslateZ', at='double', p='nuTranslate'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='makeDouble3', at='double3'                    	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='makeDouble3X', at='double', p='makeDouble3'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='makeDouble3Y', at='double', p='makeDouble3'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='makeDouble3Z', at='double', p='makeDouble3'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuDouble3', at='double3'                  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuDouble3X', at='double', p='nuDouble3'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuDouble3Y', at='double', p='nuDouble3'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuDouble3Z', at='double', p='nuDouble3'  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuScalarA', at='double'                  	, hidden = False, readable = True, writable = True, keyable = True)
mc.addAttr('network3', ln='nuCompound', at='compound', nc='4'                   	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='nuCompoundInt', at='long', p='nuCompound'  	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='nuCompoundFloat', at='double', p='nuCompound'  	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='nuCompoundTiny', at='compound', p='nuCompound', nc='2'  	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='nuCompoundTinyU', at='double', p='nuCompoundTiny'  	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='nuCompoundTinyV', at='double', p='nuCompoundTiny'  	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='nuCompoundFour', at='bool', p='nuCompound'  	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='nuNurbsCurve', dt='nurbsCurve'                     	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='letterEnum', at='enum', en='A:B:C:D:E'                   	, hidden = False, readable = True, writable = True, keyable = False)
mc.addAttr('network3', ln='weirdEnum', at='enum', en='G:Y:A=50:K=400:F:B=1000'                  	, hidden = False, readable = True, writable = True, keyable = True)
"""
```


# scope reduction

ehh i think it's surmountable enough to contain all its use cases?