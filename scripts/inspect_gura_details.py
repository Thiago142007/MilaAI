import bpy

gura_fbx = r"c:\Users\brawl\Desktop\Mila\src\client\models\gura\source\Gawr Gura.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=gura_fbx)

print("=== GAWR GURA MATERIALS & BONES DETAILED ===")
for mat in bpy.data.materials:
    print(f"Material: '{mat.name}'")

arm = bpy.data.objects.get('GawrGura_arm')
if arm:
    print("\n--- ALL BONES ---")
    for b in arm.data.bones:
        print(f"Bone: {b.name}")
