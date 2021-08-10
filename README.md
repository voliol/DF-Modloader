# DF-Modloader
A loader/compiler/manager for Dwarf Fortress mods

This project is just a (working) mockup. It is also currently inactive. If you want to work on it, make your own fork.
Asking me about it is fine though.

Below is my initial forum/reddit post (http://www.bay12forums.com/smf/index.php?topic=178868.0), which will have to do in lack of another explanation:
---
I don't recall if it was in a recent interview, FotF reply, or maybe a DF talk, but somewhere Toady was asked about Steam workshop, and what it meant for mod managing. He said he'd take a look at it, and that he was surprised that some kind of utility for managing mods hadn't popped up from the community. Turns out there have been a few attempts at it, but none established themselves firmly as DFhack or Therapist did, and are by now outdated. I've also acquainted myself more closely with how the raws work lately as I developed DF Diagnosipack, So I figured, why don't I give it a try.
Below is my attempt, which I should already disclaim I will not continue working on. My hope is that it is still workable enough to inspire something better, or to build of off to make a long-standing utility. A third wishful outcome to is that the discussion this spawns, regarding how a mod loader should best be laid out, is helpful to the brothers Adams as they are to implement one into Dwarf Fortress proper.

In any case, here is the download: https://dffd.bay12games.com/file.php?id=15633
and a screenshot:
Spoiler (click to show/hide)

You need Python 3 to run it, nothing more (hopefully).

The design was inspired primarily by the Minecraft resource pack screen. The selected mods are compiled from top going down. Other than just mashing the mods together, there is some functionality in there to (mass) edit raw objects defined "higher up" in the mod loading order, as well as a few new tokens also for the modloader to parse. You can do some pretty powerful stuff, see the example mods in the download.
New "object definitions":
[OBJECT_TYPE:OBJECT_ID]:
The "vanilla" way to define a new object, e.g. [CREATURE:TIGER]. If you define an object with the same OBJECT_TYPE and OBJECT_ID as an already defined one, the old object is overwritten.

[OBJECT_TYPE:EDIT:selection criteria]:
Selects one or multiple already defined objects to be edited. Subsequent tokens are added to the end by default. Valid selection criteria are BY_ID:OBJECT_ID, selecting individual objects by id, BY_CLASS:OBJECT_CLASS, selecting all objects (of the object type) with the given object class (or creature class), BY_TOKEN:TOKEN, selecting all objects with the given token, and BY_TOKEN_PRECISE:TOKEN, selecting all objects with the given token and token values.
E.g. [CREATURE:EDIT:BY_ID:TIGER], [CREATURE:EDIT:BY_CLASS:MAMMAL], [CREATURE:EDIT:BY_TOKEN:LAIR], [CREATURE:EDIT:BY_TOKEN_SPECIFIC:LAIR:SHRINE:100]

[OBJECT_TYPE:REMOVE:selection criteria]:
Removes the selected objects. Takes the same selection criteria as EDIT. e.g. [ENTITY:REMOVE:BY_ID:FOREST]

[OBJECT_CLASS:class name] is a new token. It grants an arbitrary "object class". For creatures, it is synonymous with [CREATURE_CLASS]

The special tokens COPY_TAGS_FROM, GO_TO_END, GO_TO_START, GO_TO_TAG have also been made to work for all objects (not just creatures).

Finally, creature variations have been generalized into "object variations". These work just the same as creature variations do, which is too say they are a little tricky. See the wiki article. The only difference is that instead of "CREATURE_VARIATION" or "CV" object variation-related tokens have "OBJECT_VARIATION" or "OV" in their names. You can also nest an object variation within a creature variation. Creature variations can still be used on creatures.
The full set of object variation-related tokens is:
Spoiler (click to show/hide)

I hope you excuse me for the sloppiness of my writing, I finished up the mockup to a point where I could feel satisfied to let it go pretty late in the evening, and wanted to make this post befor going to bed so I'm done with it. It's affecting the quality for the worse, as my brain gets all tangled. At the time of writing, it is 1 at night for me.
