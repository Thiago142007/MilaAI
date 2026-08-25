import bpy
import os

print("--- DETAILED BONE HIERARCHY & ROTATIONS ---")
arm = bpy.data.objects.get('Armature')
if arm:
    for b in arm.data.bones:
        parent_name = b.parent.name if b.parent else "None"
        print(f"Bone: {b.name:25} | Parent: {parent_name:25} | Length: {b.length:.3f} | Head: {b.head_local[:]}")

print("\n--- MATERIAL SHADER NODES ---")
for mat in bpy.data.materials:
    print(f"\nMaterial: {mat.name}")
    if mat.node_tree:
        for n in mat.node_tree.nodes:
            print(f"  Node: {n.name} ({n.type})")
            for inp in n.inputs:
                if inp.is_linked:
                    links = [l.from_node.name + "." + l.from_socket.name for l in inp.links]
                    print(f"    Input '{inp.name}' linked from: {links}")
