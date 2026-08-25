import bpy
import os
import shutil
import bmesh

project_root = r"c:\Users\brawl\Desktop\Mila"
fbx_source = os.path.join(project_root, "src", "client", "models", "gura", "source", "Gawr Gura.fbx")
tex_dir = os.path.join(project_root, "src", "client", "models", "gura", "textures")
out_src_dirs = [
    os.path.join(project_root, "src", "client", "models", "gura", "source"),
    os.path.join(project_root, "frontend", "models", "gura", "source"),
]

for d in out_src_dirs:
    os.makedirs(d, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx_source)

# 1. Clean out outline material and hull polygons
mesh_obj = bpy.data.objects.get('GawrGura_mesh')
target_arm = bpy.data.objects.get('GawrGura_arm')

if mesh_obj:
    print("\n--- 1. REMOVING INVERTED OUTLINE HULL ---")
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    outline_slot_idx = -1
    for i, slot in enumerate(mesh_obj.material_slots):
        if slot.name == 'OH_Outline_Material':
            outline_slot_idx = i
            break
            
    if outline_slot_idx >= 0:
        faces_to_remove = [f for f in bm.faces if f.material_index == outline_slot_idx]
        print(f"Deleting {len(faces_to_remove)} inverted outline hull faces from mesh...")
        bmesh.ops.delete(bm, geom=faces_to_remove, context='FACES_ONLY')
        bm.to_mesh(mesh_obj.data)
        mesh_obj.data.update()
        
        # Remove material slot
        mesh_obj.active_material_index = outline_slot_idx
        bpy.context.view_layer.objects.active = mesh_obj
        bpy.ops.object.material_slot_remove()
        print("OH_Outline_Material slot removed!")
    bm.free()

# 2. Textures Setup
print("\n--- 2. CONFIGURING HIGH-RES TEXTURES & SHADERS ---")
body_tex_path = os.path.join(tex_dir, "body.png")
face_tex_path = os.path.join(tex_dir, "face.png")
hair_tex_path = os.path.join(tex_dir, "hair.png")

body_img = bpy.data.images.load(body_tex_path, check_existing=True)
face_img = bpy.data.images.load(face_tex_path, check_existing=True)
hair_img = bpy.data.images.load(hair_tex_path, check_existing=True)

body_mats = {'体', '服', '服白', '服黒', '服灰', '服赤', '服金', '服内'}
face_mats = {'白目', '歯', '口内', '顔', '顔線無し', '瞳', 'ハイライト', '瞳拡張', 'まつげ', 'まゆ'}
hair_mats = {'帽子', '後髪', 'おさげ改', '横髪', 'ex', '前髪', 'ex2'}
mask_mats = {'まつげ', 'まゆ', 'ハイライト', '瞳拡張', 'おさげ改', '顔線無し'}

for mat in bpy.data.materials:
    name = mat.name
    if name == 'OH_Outline_Material':
        continue
        
    img = None
    if name in body_mats:
        img = body_img
    elif name in face_mats:
        img = face_img
    elif name in hair_mats:
        img = hair_img
    else:
        img = body_img
        
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.location = (-300, 0)
    tex_node.image = img
    
    out_node = nodes.new(type='ShaderNodeOutputMaterial')
    out_node.location = (300, 0)
    
    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    
    if name in mask_mats:
        if 'Alpha' in tex_node.outputs and 'Alpha' in bsdf.inputs:
            links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
        mat.blend_method = 'CLIP'
        mat.alpha_threshold = 0.2
        print(f"Configured MASK material: {name} -> {img.name}")
    else:
        mat.blend_method = 'OPAQUE'
        print(f"Configured OPAQUE material: {name} -> {img.name}")
        
    links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.45
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.15

# 3. Retarget and Bake Talking animation from Talking.fbx for Gura
talk_fbx = os.path.join(project_root, "src", "client", "models", "animations", "Talking.fbx")

bone_mapping_gura = {
    '下半身': 'mixamorig:Hips',
    '上半身': 'mixamorig:Spine',
    '上半身2': 'mixamorig:Spine1',
    '上半身3': 'mixamorig:Spine2',
    '首': 'mixamorig:Neck',
    '頭': 'mixamorig:Head',

    '肩.L': 'mixamorig:LeftShoulder',
    '腕.L': 'mixamorig:LeftArm',
    'ひじ.L': 'mixamorig:LeftForeArm',
    '手首.L': 'mixamorig:LeftHand',

    '肩.R': 'mixamorig:RightShoulder',
    '腕.R': 'mixamorig:RightArm',
    'ひじ.R': 'mixamorig:RightForeArm',
    '手首.R': 'mixamorig:RightHand',

    '足.L': 'mixamorig:LeftUpLeg',
    'ひざ.L': 'mixamorig:LeftLeg',
    '足首.L': 'mixamorig:LeftFoot',
    'つま先.L': 'mixamorig:LeftToeBase',

    '足.R': 'mixamorig:RightUpLeg',
    'ひざ.R': 'mixamorig:RightLeg',
    '足首.R': 'mixamorig:RightFoot',
    'つま先.R': 'mixamorig:RightToeBase',

    '親指０.L': 'mixamorig:LeftHandThumb1',
    '親指１.L': 'mixamorig:LeftHandThumb2',
    '親指２.L': 'mixamorig:LeftHandThumb3',
    '人指１.L': 'mixamorig:LeftHandIndex1',
    '人指２.L': 'mixamorig:LeftHandIndex2',
    '人指３.L': 'mixamorig:LeftHandIndex3',
    '中指１.L': 'mixamorig:LeftHandMiddle1',
    '中指２.L': 'mixamorig:LeftHandMiddle2',
    '中指３.L': 'mixamorig:LeftHandMiddle3',
    '薬指１.L': 'mixamorig:LeftHandRing1',
    '薬指２.L': 'mixamorig:LeftHandRing2',
    '薬指３.L': 'mixamorig:LeftHandRing3',
    '小指１.L': 'mixamorig:LeftHandPinky1',
    '小指２.L': 'mixamorig:LeftHandPinky2',
    '小指３.L': 'mixamorig:LeftHandPinky3',

    '親指０.R': 'mixamorig:RightHandThumb1',
    '親指１.R': 'mixamorig:RightHandThumb2',
    '親指２.R': 'mixamorig:RightHandThumb3',
    '人指１.R': 'mixamorig:RightHandIndex1',
    '人指２.R': 'mixamorig:RightHandIndex2',
    '人指３.R': 'mixamorig:RightHandIndex3',
    '中指１.R': 'mixamorig:RightHandMiddle1',
    '中指２.R': 'mixamorig:RightHandMiddle2',
    '中指３.R': 'mixamorig:RightHandMiddle3',
    '薬指１.R': 'mixamorig:RightHandRing1',
    '薬指２.R': 'mixamorig:RightHandRing2',
    '薬指３.R': 'mixamorig:RightHandRing3',
    '小指１.R': 'mixamorig:RightHandPinky1',
    '小指２.R': 'mixamorig:RightHandPinky2',
    '小指３.R': 'mixamorig:RightHandPinky3',
}

print("\n--- 3. BAKING TALKING ANIMATION ---")
before_objs = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=talk_fbx)
imported_objs = [o for o in bpy.data.objects if o not in before_objs]

source_arm = None
for obj in imported_objs:
    if obj.type == 'ARMATURE':
        source_arm = obj
        break

if source_arm and target_arm:
    src_action = source_arm.animation_data.action if source_arm.animation_data else None
    start_frame = int(src_action.frame_range[0])
    end_frame = int(src_action.frame_range[1])
    
    bpy.context.view_layer.objects.active = target_arm
    bpy.ops.object.mode_set(mode='POSE')
    
    for pb in target_arm.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
            
    for tgt_b, src_b in bone_mapping_gura.items():
        if tgt_b in target_arm.pose.bones and src_b in source_arm.pose.bones:
            pb = target_arm.pose.bones[tgt_b]
            crc = pb.constraints.new(type='COPY_ROTATION')
            crc.target = source_arm
            crc.subtarget = src_b
            crc.target_space = 'WORLD'
            crc.owner_space = 'WORLD'
            
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
    
    baked_action = target_arm.animation_data.action
    baked_action.name = "Talking"
    
    if target_arm.animation_data.nla_tracks:
        for t in list(target_arm.animation_data.nla_tracks):
            target_arm.animation_data.nla_tracks.remove(t)
            
    track = target_arm.animation_data.nla_tracks.new()
    track.name = "Talking"
    track.strips.new("Talking", start_frame, baked_action)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in imported_objs:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    print("Talking action baked successfully on Gura!")

# Clean out any extra non-character objects in the scene
for obj in list(bpy.data.objects):
    if obj not in {target_arm, mesh_obj}:
        bpy.data.objects.remove(obj, do_unlink=True)

# Select only Gura Armature and Mesh
bpy.ops.object.select_all(action='DESELECT')
target_arm.select_set(True)
mesh_obj.select_set(True)
bpy.context.view_layer.objects.active = target_arm

# Export GLB to all client directories
for out_dir in out_src_dirs:
    glb_path = os.path.join(out_dir, "gura.glb")
    print(f"\n--- 4. EXPORTING GURA GLB: {glb_path} ---")
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format='GLB',
        use_selection=True,
        export_materials='EXPORT',
        export_image_format='AUTO',
        export_yup=True,
        export_skins=True,
        export_animations=True,
        export_apply=False
    )
    print(f"GLB export complete: {os.path.getsize(glb_path)} bytes")

print("\n==========================================")
print("  GAWR GURA BUILD WITH TEXTURES COMPLETE! ")
print("==========================================")
