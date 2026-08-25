import bpy
import os

project_root = r"c:\Users\brawl\Desktop\Mila"
blend_path = os.path.join(project_root, "extracted_mila", "source", "cute anime girl222.blend")
idle_path = os.path.join(project_root, "src", "client", "models", "animations", "Idle.fbx")
talk_path = os.path.join(project_root, "src", "client", "models", "animations", "Talking.fbx")
out_anim_dir = os.path.join(project_root, "src", "client", "models", "animations")

# Let's inspect the rest pose of the cute anime girl armature and compare to Mixamo
bpy.ops.wm.open_mainfile(filepath=blend_path)
arm = bpy.data.objects.get('Armature')

print("=== CUTE ANIME GIRL BONES ===")
for b in arm.data.bones:
    if any(k in b.name.lower() for k in ['head', 'neck', 'spine', 'chest', 'arm', 'leg', 'shoulder', 'elbow', 'knee']):
        print(f"Bone: {b.name:20} Matrix: {b.matrix_local.to_euler()[:]}")
