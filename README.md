```py
import maya.cmds as mc
import maya.api.OpenMaya as om2
```

# mayaNodeToPython
maya rigger's devscript to convert node networks to creation commands

- written for a maya 2022 environment
- openMaya 2.0 and maya.cmds in-DCC packages
- only deals with default nodes (plugins that interface with `mc.createNode()` or `mc.nodeType()` may work, but is untested)
- mostly default node editor work, am interested in other bespoke node editor plugins for maya (would prefer node editor UX from blender or unreal engine)

## the gist

- parses selected nodes in node editor and re-creates the creation/invocation commands for them
- workflow is half-automatic; only a means to quickly create a script that can be easily modified to hook up lists of existing joints
	- target use is in developing autorig scripts, either as a whole or as separate modules

## motivation

gonna show weakness for a bit: had a dino rig assignment years ago in uni and made a digitgrade reverse foot (that's 80% toe 20% palm 0% heel-is-above-ground), and it took me too much time to re-invent a driver and control scheme. was not left with much time to reflect-rig the other foot. this is one of the letters to my past self on this aspect

## misc links

- github pages for the initial prototype: [stuaaaaaaaaaart.github.io - nodesToPython (2024)](https://stuaaaaaaaaaart.github.io/posts/2024/Note_2024-005_nodesToPython.html)