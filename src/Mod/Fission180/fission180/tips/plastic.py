# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the PLASTIC tab (wave 8, builder tips-workspaces).

One entry per ribbon command id: "summary" (the small tooltip), "what", "steps", "tips" and
"picture" (a file in fission180/icons/tips/, made by tools/fission180/tip_pictures_plastic.py).
The texts describe what Fission 180's own dialogs do (plastic_rules_ui.py, plastic_boss_ui.py,
plastic_snap_ui.py, plastic_lip_ui.py, plastic_rest_ui.py, plastic_advice_ui.py).
The SOLID commands the tab repeats (Extrude, Shell, Draft...) have their entry in tips/solid.py.
"""

TIPS = {
    "Fission180_AssignPlasticRule": {
        "summary": "Give a component a plastic rule: its material, wall thickness and draft.",
        "what": (
            "A plastic rule says how a moulded part is made: the plastic, the wall Thickness, "
            "the Draft Angle, the radius of rounds and more. Assigning one to a component sets "
            "its bodies' material, and Shell, Draft, Boss, Lip and the other plastic tools "
            "start from its values."
        ),
        "steps": [
            "Click Assign Plastic Rule.",
            "Pick the component in the list, or click one of its bodies.",
            "Click a rule under In This Design or Library (open a row to see its values).",
            "Click OK.",
        ],
        "tips": [
            "A Library rule is copied into the design when you assign it.",
            "Rules belong to components, never to single bodies.",
        ],
        "picture": "pl_assign_rule.png",
    },
    "Fission180_ManagePlasticRules": {
        "summary": "Make, edit, copy and delete the plastic rules of the design and your library.",
        "what": (
            "Lists the plastic rules In This Design and in your Library, with buttons to add "
            "and change them. A rule holds the Material, Thickness, Draft Angle, Nominal "
            "Radius, Reveal Height, Clearance and the limits Design Advice checks."
        ),
        "steps": [
            "Click Manage Plastic Rules.",
            "Click a rule, then Edit (or New, or Copy).",
            "Change the values below the lists and click Save Rule.",
            "Click OK to keep the design's changes.",
        ],
        "tips": [
            "Lengths may use the thickness, for example Thickness / 2.",
            "Set As Default picks the Library rule new components start with.",
        ],
        "picture": "pl_manage_rules.png",
    },
    "Fission180_Boss": {
        "summary": "Add screw bosses: posts with holes that hold two plastic halves together.",
        "what": (
            "Makes matching bosses on both halves of a case at each sketch point: a post with a "
            "clearance hole for the screw head on one side, a post with a pilot hole for the "
            "thread on the other. Sizes come from the screw size and the plastic rule; ribs "
            "and screws can be added."
        ),
        "steps": [
            "Sketch points on the parting plane between the halves (or click a flat face).",
            "Click Boss, then click the points (or the sketch in the browser).",
            "Set the Thread Diameter; check Side 1 (head) and Side 2 (thread).",
            "Optionally switch on Ribs, or Create Component (screws) under Fastener.",
            "Click OK.",
        ],
        "tips": [
            "Flip swaps the head side and the thread side.",
            "Each half gets its own Boss step in the timeline.",
        ],
        "picture": "pl_boss.png",
    },
    "Fission180_SnapFit": {
        "summary": "Add snap-fit hooks that click two plastic parts together without screws.",
        "what": (
            "Makes a bending hook on one body at each sketch point, and the groove, slot or "
            "loop it catches in on the other body. Types: Parallel Hook and Groove, "
            "Perpendicular Hook and Groove, Hook and Loop. The dialog warns when the hook "
            "would bend too far for the plastic."
        ),
        "steps": [
            "Sketch points where the hooks go, between the two bodies.",
            "Click Snap Fit, then click the sketch (Automatic takes every point).",
            "Pick the Type, then set Beam Length, Thickness at Root and Catch Depth.",
            "Turn the hooks with the rotation handle or the Rotation Angle.",
            "Click OK.",
        ],
        "tips": [
            "Hide Other Body shows the hooks while you work.",
            "Flip puts the hook on the other body.",
        ],
        "picture": "pl_snap_fit.png",
    },
    "Fission180_Lip": {
        "summary": "Add a lip, a groove, or both, along the rim where two plastic halves meet.",
        "what": (
            "Makes a raised lip on the rim of one half and, for Lip And Groove, the matching "
            "groove in the other half, so the case lines up and is sealed. Sizes come from the "
            "plastic rule: Lip Width = Thickness / 2, Lip Height = Reveal Height."
        ),
        "steps": [
            "Click Lip, then click the inner edge of the rim (or the rim's flat face).",
            "Pick the Type: Lip, Groove or Lip And Groove.",
            "Drag the arrows or open Advanced to set Lip Height and Lip Width.",
            "Click OK.",
        ],
        "tips": [
            "Tangent Chain takes a rounded rim in one click.",
            "Lip And Groove needs the two halves to touch.",
        ],
        "picture": "pl_lip.png",
    },
    "Fission180_Rest": {
        "summary": "Make a flat rest (a pad) on a curved or uneven part, from a sketch profile.",
        "what": (
            "Turns the area inside a closed sketch profile into a flat face on the part: "
            "material that sticks out past the sketch is cut off, and walls of the rule's "
            "Thickness are built where the part lies below it. Use it for feet and flat spots "
            "for labels."
        ),
        "steps": [
            "Sketch a closed profile on a plane where the flat face should be.",
            "Click Rest, then click inside the profile.",
            "Check the Body (Auto finds the one under the profile).",
            "Set Thickness and Draft Angle (from the rule), Flip if needed; click OK.",
        ],
        "tips": [
            "Values from the rule follow the rule until you type your own.",
        ],
        "picture": "pl_rest.png",
    },
    "Fission180_RuleFillet": {
        "summary": "Round every edge of the faces or features you pick with the rule's radius.",
        "what": (
            "Opens Fillet set to Rule Fillet: instead of clicking edges one by one, pick faces "
            "or whole features and every edge of them is rounded, also edges a later change "
            "adds. The radius starts at the plastic rule's Nominal Radius."
        ),
        "steps": [
            "Click Rule Fillet.",
            "Click faces of the part, or a feature in the timeline.",
            "Pick the Rule: All Edges, or Between Faces/Features (two boxes).",
            "Check the Radius, then click OK.",
        ],
        "tips": [
            "It is the Fillet dialog: switch Type to Fillet for single edges.",
        ],
        "picture": "pl_rule_fillet.png",
    },
    "Fission180_DesignAdvice": {
        "summary": "Check a plastic part for walls too thin or thick, missing draft and undercuts.",
        "what": (
            "Colours the part to show what would be hard to mould, against its plastic rule: "
            "wall thickness out of range, uneven walls, faces without enough draft, sharp "
            "knife edges and undercuts. A list names each issue; a click zooms to it. It is "
            "kept in the browser's Analysis folder."
        ),
        "steps": [
            "Click Design Advice: the bodies with a plastic rule are checked.",
            "Set the Pull Direction (the way the mould opens; Z by default).",
            "Read the colours and the Issues list; click an issue to zoom to it.",
            "Click OK to keep it, or Cancel.",
        ],
        "tips": [
            "Display Thickness shows a colour map of the wall thickness.",
            "It checks again by itself when the part changes.",
        ],
        "picture": "pl_design_advice.png",
    },
}
