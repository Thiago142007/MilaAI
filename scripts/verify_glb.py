import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"c:\Users\brawl\Desktop\Mila\src\client\models\mila\source\mila.glb")

print("\n=== IMPORTED GLB INSPECTION ===")
print(f"Objects in GLB: {[o.name for o in bpy.data.objects]}")
print(f"Actions in GLB: {[a.name for a in bpy.data.actions]}")
for a in bpy.data.actions:
    print(f"  Action '{a.name}': range={a.frame_range[:]}, fcurves={len(a.fcurves)}")
