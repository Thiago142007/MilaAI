import bpy
import os
import shutil

project_root = r"c:\Users\brawl\Desktop\Mila"
blend_path = os.path.join(project_root, "extracted_mila", "source", "cute anime girl222.blend")
idle_fbx = os.path.join(project_root, "src", "client", "models", "animations", "Idle.fbx")
talk_fbx = os.path.join(project_root, "src", "client", "models", "animations", "Talking.fbx")

tex_src_dir = os.path.join(project_root, "extracted_mila", "textures")
out_tex_dir = os.path.join(project_root, "src", "client", "models", "mila", "textures")
out_src_dir = os.path.join(project_root, "src", "client", "models", "mila", "source")
out_anim_dir = os.path.join(project_root, "src", "client", "models", "animations")

os.makedirs(out_tex_dir, exist_ok=True)
os.makedirs(out_src_dir, exist_ok=True)
os.makedirs(out_anim_dir, exist_ok=True)

# 1. Copy textures
print("--- 1. COPYING TEXTURES ---")
for f in os.listdir(tex_src_dir):
    src = os.path.join(tex_src_dir, f)
    dst = os.path.join(out_tex_dir, f)
    shutil.copy2(src, dst)
    print(f"Copied: {f}")

# 2. Retarget function
bone_mapping = {
    'Hips': 'mixamorig:Hips',
    'Spine': 'mixamorig:Spine',
    'Chest': 'mixamorig:Spine2',
    'Neck': 'mixamorig:Neck',
    'Head': 'mixamorig:Head',

    'Left shoulder': 'mixamorig:LeftShoulder',
    'Left arm': 'mixamorig:LeftArm',
    'Left elbow': 'mixamorig:LeftForeArm',
    'Left wrist': 'mixamorig:LeftHand',

    'Right shoulder': 'mixamorig:RightShoulder',
    'Right arm': 'mixamorig:RightArm',
    'Right elbow': 'mixamorig:RightForeArm',
    'Right wrist': 'mixamorig:RightHand',

    'Left leg': 'mixamorig:LeftUpLeg',
    'Left knee': 'mixamorig:LeftLeg',
    'Left ankle': 'mixamorig:LeftFoot',
    'Left toe': 'mixamorig:LeftToeBase',

    'Right leg': 'mixamorig:RightUpLeg',
    'Right knee': 'mixamorig:RightLeg',
    'Right ankle': 'mixamorig:RightFoot',
    'Right toe': 'mixamorig:RightToeBase',

    'Thumb1_L': 'mixamorig:LeftHandThumb1',
    'Thumb2_L': 'mixamorig:LeftHandThumb2',
    'IndexFinger1_L': 'mixamorig:LeftHandIndex1',
    'IndexFinger2_L': 'mixamorig:LeftHandIndex2',
    'IndexFinger3_L': 'mixamorig:LeftHandIndex3',
    'MiddleFinger1_L': 'mixamorig:LeftHandMiddle1',
    'MiddleFinger2_L': 'mixamorig:LeftHandMiddle2',
    'MiddleFinger3_L': 'mixamorig:LeftHandMiddle3',
    'RingFinger1_L': 'mixamorig:LeftHandRing1',
    'RingFinger2_L': 'mixamorig:LeftHandRing2',
    'RingFinger3_L': 'mixamorig:LeftHandRing3',
    'LittleFinger1_L': 'mixamorig:LeftHandPinky1',
    'LittleFinger2_L': 'mixamorig:LeftHandPinky2',
    'LittleFinger3_L': 'mixamorig:LeftHandPinky3',

    'Thumb2_R': 'mixamorig:RightHandThumb2',
    'IndexFinger1_R': 'mixamorig:RightHandIndex1',
    'IndexFinger2_R': 'mixamorig:RightHandIndex2',
    'IndexFinger3_R': 'mixamorig:RightHandIndex3',
    'MiddleFinger1_R': 'mixamorig:RightHandMiddle1',
    'MiddleFinger2_R': 'mixamorig:RightHandMiddle2',
    'MiddleFinger3_R': 'mixamorig:RightHandMiddle3',
    'RingFinger1_R': 'mixamorig:RightHandRing1',
    'RingFinger2_R': 'mixamorig:RightHandRing2',
    'RingFinger3_R': 'mixamorig:RightHandRing3',
    'LittleFinger1_R': 'mixamorig:RightHandPinky1',
    'LittleFinger2_R': 'mixamorig:RightHandPinky2',
    'LittleFinger3_R': 'mixamorig:RightHandPinky3',
}

# Open blend file
bpy.ops.wm.open_mainfile(filepath=blend_path)
target_arm_obj = bpy.data.objects.get('Armature')

# Configure materials
print("--- 2. CONFIGURING MATERIALS & TEXTURES ---")
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
        
        img = None
        for existing_img in bpy.data.images:
            if os.path.basename(existing_img.filepath).lower() == tex_name.lower() or existing_img.name.lower() == tex_name.lower():
                img = existing_img
                break
        if not img or not os.path.exists(img.filepath):
            img = bpy.data.images.load(tex_full_path, check_existing=True)
        img.filepath = tex_full_path
        
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        bsdf = None
        for n in nodes:
            if n.type == 'BSDF_PRINCIPLED':
                bsdf = n
                break
        if not bsdf:
            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            bsdf.location = (0, 0)
        
        tex_node = None
        for n in nodes:
            if n.type == 'TEX_IMAGE':
                tex_node = n
                break
        if not tex_node:
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.location = (-300, 0)
        tex_node.image = img
        
        output_node = None
        for n in nodes:
            if n.type == 'OUTPUT_MATERIAL':
                output_node = n
                break
        if not output_node:
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            output_node.location = (300, 0)
            
        for n in list(nodes):
            if n.type == 'OUTPUT_MATERIAL' and n != output_node:
                nodes.remove(n)
                
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
        if 'Alpha' in tex_node.outputs and 'Alpha' in bsdf.inputs:
            links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
        links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])
        
        # Soft anime shading parameters
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.4
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.3
            
        if mat.name in ["hair shadow", "hair"]:
            mat.blend_method = 'HASHED'
        else:
            mat.blend_method = 'OPAQUE'
            
        print(f"Configured material '{mat.name}' with texture '{tex_name}'")

# Retarget and Bake Idle and Talking actions
def bake_animation(source_fbx_path, action_name):
    print(f"\n--- Retargeting {action_name} from {source_fbx_path} ---")
    bpy.ops.import_scene.fbx(filepath=source_fbx_path)
    
    source_arm_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj != target_arm_obj:
            source_arm_obj = obj
            break
            
    if not source_arm_obj:
        print(f"Error: source armature not found for {source_fbx_path}")
        return None
        
    src_action = source_arm_obj.animation_data.action if source_arm_obj.animation_data else None
    start_frame = int(src_action.frame_range[0])
    end_frame = int(src_action.frame_range[1])
    
    bpy.context.view_layer.objects.active = target_arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    for pb in target_arm_obj.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
            
    for tgt_bone, src_bone in bone_mapping.items():
        if tgt_bone in target_arm_obj.pose.bones and src_bone in source_arm_obj.pose.bones:
            pb = target_arm_obj.pose.bones[tgt_bone]
            crc = pb.constraints.new(type='COPY_ROTATION')
            crc.target = source_arm_obj
            crc.subtarget = src_bone
            crc.target_space = 'WORLD'
            crc.owner_space = 'WORLD'
            
    if 'Hips' in target_arm_obj.pose.bones and 'mixamorig:Hips' in source_arm_obj.pose.bones:
        pb = target_arm_obj.pose.bones['Hips']
        clc = pb.constraints.new(type='COPY_LOCATION')
        clc.target = source_arm_obj
        clc.subtarget = 'mixamorig:Hips'
        clc.use_x = False
        clc.use_y = False
        clc.use_z = True
        clc.target_space = 'LOCAL'
        clc.owner_space = 'LOCAL'

    bpy.ops.pose.select_all(action='SELECT')
    
    bpy.ops.nla.bake(
        frame_start=start_frame,
        frame_end=end_frame,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        bake_types={'POSE'}
    )
    
    baked_action = target_arm_obj.animation_data.action
    baked_action.name = action_name
    
    # Push to NLA track so glTF exporter includes all actions!
    if not target_arm_obj.animation_data.nla_tracks:
        track = target_arm_obj.animation_data.nla_tracks.new()
    else:
        track = target_arm_obj.animation_data.nla_tracks.new()
    track.name = action_name
    track.strips.new(action_name, start_frame, baked_action)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(source_arm_obj, do_unlink=True)
    print(f"Action '{action_name}' baked and pushed to NLA track!")
    return baked_action

idle_action = bake_animation(idle_fbx, "Idle")
talk_action = bake_animation(talk_fbx, "Talking")

# Export GLB
glb_path = os.path.join(out_src_dir, "mila.glb")
print(f"\n--- 3. EXPORTING GLB TO {glb_path} ---")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=glb_path,
    export_format='GLB',
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_yup=True,
    export_skins=True,
    export_animations=True,
    export_apply=False
)
print(f"GLB export complete: {os.path.getsize(glb_path)} bytes")

# Export FBX
fbx_path = os.path.join(out_src_dir, "mila.fbx")
print(f"\n--- 4. EXPORTING FBX TO {fbx_path} ---")
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
    armature_nodetype='NULL',
    bake_anim=True
)
print(f"FBX export complete: {os.path.getsize(fbx_path)} bytes")

print("\n==========================================")
print("  MILA MODEL BUILD COMPLETE SUCCESSFULLY! ")
print("==========================================")
