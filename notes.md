# notes and questions and clarifications etc
when i can think of a subtitle i'll put it in here

## why code-write the script to enumerate a range rather than appending a list?
```py
# (...)
nodeList = list(range(35))

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