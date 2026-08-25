import bpy

idle_path = r"c:\Users\brawl\Desktop\Mila\src\client\models\animations\Idle.fbx"
talk_path = r"c:\Users\brawl\Desktop\Mila\src\client\models\animations\Talking.fbx"

# Clear existing objects
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import Idle
bpy.ops.import_scene.fbx(filepath=idle_path)
print("=== IDLE.FBX ===")
for act in bpy.data.actions:
    print(f"Action: {act.name}, Fcurves: {len(act.fcurves)}")
    tracks = set([fc.data_path.split('"')[1] for fc in act.fcurves if '"' in fc.data_path])
    print(f"Bones animated in Idle: {sorted(list(tracks))}")

# Clear and import Talking
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=talk_path)
print("\n=== TALKING.FBX ===")
for act in bpy.data.actions:
    print(f"Action: {act.name}, Fcurves: {len(act.fcurves)}")
    tracks = set([fc.data_path.split('"')[1] for fc in act.fcurves if '"' in fc.data_path])
    print(f"Bones animated in Talking: {sorted(list(tracks))}")
