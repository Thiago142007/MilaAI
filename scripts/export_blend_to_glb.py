import bpy
import os
import sys

# Get absolute output path
project_root = r"c:\Users\brawl\Desktop\Mila"
out_glb = os.path.join(project_root, "src", "client", "models", "mila", "source", "mila.glb")
out_fbx = os.path.join(project_root, "src", "client", "models", "mila", "source", "mila.fbx")
tex_dir = os.path.join(project_root, "src", "client", "models", "mila", "textures")

os.makedirs(os.path.dirname(out_glb), exist_ok=True)
os.makedirs(tex_dir, exist_ok=True)

# Copy extracted textures from extracted_mila to client textures folder
import shutil
src_tex_dir = os.path.join(project_root, "extracted_mila", "textures")
if os.path.exists(src_tex_dir):
    for f in os.listdir(src_tex_dir):
        src_f = os.path.join(src_tex_dir, f)
        dst_f = os.path.join(tex_dir, f)
        if os.path.isfile(src_f):
            shutil.copy2(src_f, dst_f)
            print(f"[Texture] Copied {f} to {dst_f}")

print("[Blender] Exporting scene to GLB...")
try:
    bpy.ops.export_scene.gltf(
        filepath=out_glb,
        export_format='GLB',
        export_apply=True,
        export_animations=True,
        export_skins=True,
        export_morph=True,
        export_cameras=False,
        export_lights=False,
    )
    print(f"[Blender] Successfully exported GLB to {out_glb} (Size: {os.path.getsize(out_glb)} bytes)")
except Exception as e:
    print(f"[Blender] GLB Export failed: {e}")

print("[Blender] Exporting scene to FBX...")
try:
    bpy.ops.export_scene.fbx(
        filepath=out_fbx,
        use_selection=False,
        global_scale=1.0,
        apply_unit_scale=True,
        bake_anim=True,
        path_mode='COPY',
        embed_textures=True
    )
    print(f"[Blender] Successfully exported FBX to {out_fbx} (Size: {os.path.getsize(out_fbx)} bytes)")
except Exception as e:
    print(f"[Blender] FBX Export failed: {e}")
