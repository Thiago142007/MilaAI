import bpy
import os
import shutil

project_root = r"c:\Users\brawl\Desktop\Mila"
tex_dir = os.path.join(project_root, "extracted_mila", "textures")
out_tex_dir = os.path.join(project_root, "src", "client", "models", "mila", "textures")
out_src_dir = os.path.join(project_root, "src", "client", "models", "mila", "source")

os.makedirs(out_tex_dir, exist_ok=True)
os.makedirs(out_src_dir, exist_ok=True)

# Copy all textures to target folder
for f in os.listdir(tex_dir):
    src_path = os.path.join(tex_dir, f)
    dst_path = os.path.join(out_tex_dir, f)
    shutil.copy2(src_path, dst_path)
    print(f"Copied texture: {f} -> {dst_path}")

# Fix textures and Principled BSDF in Blender materials
tex_mapping = {
    "bot": "bot_2D_View.png",
    "glasses": "skin_2D_Viewwithouthairshadow.png",
    "hair": "hair_white_2D_View.png",
    "hair shadow": "hairshadow.png",
    "top": "top_2D_View.png",
}

for mat in bpy.data.materials:
    if mat.name in tex_mapping:
        tex_name = tex_mapping[mat.name]
        tex_full_path = os.path.join(out_tex_dir, tex_name)
        
        # Load image into blender
        img = None
        for existing_img in bpy.data.images:
            if os.path.basename(existing_img.filepath).lower() == tex_name.lower() or existing_img.name.lower() == tex_name.lower():
                img = existing_img
                break
        if not img or not os.path.exists(img.filepath):
            img = bpy.data.images.load(tex_full_path, check_existing=True)
        img.filepath = tex_full_path
        
        # Configure node tree to ensure standard Principled BSDF -> Material Output
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Find or create Principled BSDF
        bsdf = None
        for n in nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
                break
        if not bsdf:
            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            bsdf.location = (0, 0)
        
        # Find or create Texture node
        tex_node = None
        for n in nodes:
            if n.type == 'TEX_IMAGE':
                tex_node = n
                break
        if not tex_node:
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.location = (-300, 0)
        
        tex_node.image = img
        
        # Find or create Material Output
        output_node = None
        for n in nodes:
            if n.type == 'OUTPUT_MATERIAL':
                output_node = n
                break
        if not output_node:
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            output_node.location = (300, 0)
            
        # Clean extra outputs
        for n in list(nodes):
            if n.type == 'OUTPUT_MATERIAL' and n != output_node:
                nodes.remove(n)
                
        # Link Tex -> BSDF -> Output
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
        if 'Alpha' in tex_node.outputs and 'Alpha' in bsdf.inputs:
            links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
        links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])
        
        # Setup alpha blend mode if hair or hair shadow
        if mat.name in ["hair shadow", "hair"]:
            mat.blend_method = 'HASHED'
        else:
            mat.blend_method = 'OPAQUE'
            
        print(f"Configured material: {mat.name} -> {tex_name}")

# Select all objects
bpy.ops.object.select_all(action='SELECT')

# Export GLB (standard 3D web format with embedded textures & animation compatibility)
glb_path = os.path.join(out_src_dir, "mila.glb")
bpy.ops.export_scene.gltf(
    filepath=glb_path,
    export_format='GLB',
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_yup=True,
    export_skins=True,
    export_apply=False
)
print(f"Exported GLB to: {glb_path} (size: {os.path.getsize(glb_path)} bytes)")

# Export FBX as well
fbx_path = os.path.join(out_src_dir, "mila.fbx")
bpy.ops.export_scene.fbx(
    filepath=fbx_path,
    use_selection=False,
    global_scale=1.0,
    axis_forward='-Z',
    axis_up='Y',
    apply_unit_scale=True,
    bake_space_transform=False,
    object_types={'ARMATURE', 'MESH'},
    mesh_smooth_type='FACE',
    add_leaf_bones=False,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    armature_nodetype='NULL'
)
print(f"Exported FBX to: {fbx_path} (size: {os.path.getsize(fbx_path)} bytes)")
print("EXPORT COMPLETE!")
