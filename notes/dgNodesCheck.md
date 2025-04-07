extra stuff to write `mc.setAttr()` commands for:

- `plusMinusAverage`
	- `.operation`
	- multi-attributes: incoming vectors
		- `input1D`, `input2D`, `input3D`
		- check for connections and non-default values

- `multiplyDivide`
	- `.operation`
- `aimMatrix`
	- `.primaryMode`
	- `.secondaryMode`

# plusMinusAverage multi-attribute

https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Nodes/plusMinusAverage.html

- get list lengths of multi-attrs
	- no active attrs will return `None`
	- `input1D` would return `[input1D[a], input1D[b], input1D[c], input1D[d], ... ]`
		- rigging note: attributes added by connection is not undoable and may require using openMaya commands to explicitly remove
		- maya 2023 onwards: it's a better idea to use the `add`, `average` and `subtract` maths nodes
	- `input2D` would return `[input2D[a], input2Dx[a], input2Dy[a], ... ]` as a flat list
	- `input3D` would return `[input3D[a], input3Dx[a], input3Dy[a], input3Dz[a], ... ]` as a flat list
- index of members may not be in contiguous order (e.g. `[ 0,1,4,5,6 ]`)
- to get totals of actual members:
	- `input1D` is already of length
	- `input2D` : divide by 3
	- `input3D` : divide by 4
- for each member:
	- get actual index
	- process like a normal transform member
		- easiest way is to append to `checkList`
		- `([input2D[a], input2Dx[a], input2Dy[a])`
		- PROBLEM: `attributeQuery` does not recognise subElements as attrs
			- i.e. `mc.attributeQuery('input2D[0]', n='plusMinusAverage4', at=True)` does not work
		- WORKAROUND: since attributes can not contain '[ ]' as the name, strip 
