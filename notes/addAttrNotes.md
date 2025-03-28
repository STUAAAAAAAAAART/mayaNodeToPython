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



# scope reduction

realistically speaking in context to rig controls: deal with the following:
- vectors
- scalars (ints, floats/doubles)
- bools
- enums

anything else will be printed as a comment. multi-attributes isn't covered for now