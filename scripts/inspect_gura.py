import bpy

gura_fbx = r"c:\Users\brawl\Desktop\Mila\src\client\models\gura\source\Gawr Gura.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=gura_fbx)

print("=== GAWR GURA FBX INSPECTION ===")
print("Objects:", [o.name for o in bpy.data.objects])
for o in bpy.data.objects:
    if o.type == 'MESH':
        print(f"Mesh: {o.name}, Materials: {[m.name for m in o.data.materials if m]}")
    elif o.type == 'ARMATURE':
        print(f"Armature: {o.name}, Bones count: {len(o.data.bones)}")
        print(f"Bones sample: {[b.name for b in o.data.bones][:25]}")
