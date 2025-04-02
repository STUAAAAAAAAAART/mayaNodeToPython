# demonstrations: list in for-loops are immediately iterative

x = [1] # one element

for i in x: # for each object in list x, currently there's only one...
	if len(x)<20: # if x has less than 20 objects
		x.append(1) # add an object
		print("ding!") # signal to commandline that this happened

print(x) # print out the now-longer list x


y = list(range(20)) # list of 0-19

listCounter = 0 # suspicious counter
for i in y: # for each object in y, there are 20 of them...
	try:
		del y[listCounter+1] # remove neighbouring object
	except:
		pass # index probably went out of range, ignore command
	listCounter+=1 # count one up
	# go to next object

print(y) # print out magically halved list??





# demonstration: openMaya's MItSelectionList (and possibly other similar iterables in openMaya) work with python for loops

import maya.cmds as mc
import maya.api.OpenMaya as om2

newSel : om2.MSelectionList = om2.MSelectionList() # new selection list

for i in range(10):
	mc.createNode('transform', n=f"transform{i}")

newSel.clear() # in case parts of this script is re-run
for obj in ['transform0','transform1','transform2','transform3','transform4','transform5','transform6','transform7','transform8','transform9']:
	newSel.add(obj) # select objects
print(newSel.getSelectionStrings()) # print list 

newList = om2.MItSelectionList(newSel) # new iterator function

for i in newList: # this is where the magic starts
	print(i.getStrings())
newList.reset() # necessary for redoing the iterator

# test for immediate iteration

listCounter = 0 # sus counter
for i in newList:
	try:
		newSel.remove(listCounter+1) # the MSL, not the MIterator!! 
	except:
		pass
	listCounter += 1
newList.reset()

print(newSel.getSelectionStrings()) # whaaaaa