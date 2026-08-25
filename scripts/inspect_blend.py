import bpy

print("=" * 60)
print("INSPECTING BLEND FILE")
print("=" * 60)

print("\n--- OBJECTS ---")
for obj in bpy.data.objects:
    print(f"Object: {obj.name} (type: {obj.type})")
    if obj.type == 'MESH':
        print(f"  Materials: {[m.name for m in obj.data.materials if m]}")
    elif obj.type == 'ARMATURE':
        print(f"  Bones count: {len(obj.data.bones)}")
        print(f"  Bone names: {[b.name for b in obj.data.bones]}")

print("\n--- MATERIALS ---")
for mat in bpy.data.materials:
    print(f"Material: {mat.name}, use_nodes: {mat.use_nodes}")
    if mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                print(f"  Image node: {node.name} -> {node.image.name} (filepath: {node.image.filepath})")

print("\n--- ACTIONS / ANIMATIONS ---")
for act in bpy.data.actions:
    print(f"Action: {act.name}, duration: {act.frame_range}")

print("\n--- IMAGES ---")
for img in bpy.data.images:
    print(f"Image: {img.name}, filepath: {img.filepath}, size: {img.size[:]}")

print("=" * 60)
