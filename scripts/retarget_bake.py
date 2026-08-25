import bpy
import os
import math

project_root = r"c:\Users\brawl\Desktop\Mila"
blend_path = os.path.join(project_root, "extracted_mila", "source", "cute anime girl222.blend")
idle_fbx = os.path.join(project_root, "src", "client", "models", "animations", "Idle.fbx")
talk_fbx = os.path.join(project_root, "src", "client", "models", "animations", "Talking.fbx")
out_src_dir = os.path.join(project_root, "src", "client", "models", "mila", "source")
out_anim_dir = os.path.join(project_root, "src", "client", "models", "animations")

# Mapping from Target Character Bones to Source Mixamo Bones
bone_mapping = {
    # Spine & Head
    'Hips': 'mixamorig:Hips',
    'Spine': 'mixamorig:Spine',
    'Chest': 'mixamorig:Spine2',
    'Neck': 'mixamorig:Neck',
    'Head': 'mixamorig:Head',

    # Left Arm
    'Left shoulder': 'mixamorig:LeftShoulder',
    'Left arm': 'mixamorig:LeftArm',
    'Left elbow': 'mixamorig:LeftForeArm',
    'Left wrist': 'mixamorig:LeftHand',

    # Right Arm
    'Right shoulder': 'mixamorig:RightShoulder',
    'Right arm': 'mixamorig:RightArm',
    'Right elbow': 'mixamorig:RightForeArm',
    'Right wrist': 'mixamorig:RightHand',

    # Left Leg
    'Left leg': 'mixamorig:LeftUpLeg',
    'Left knee': 'mixamorig:LeftLeg',
    'Left ankle': 'mixamorig:LeftFoot',
    'Left toe': 'mixamorig:LeftToeBase',

    # Right Leg
    'Right leg': 'mixamorig:RightUpLeg',
    'Right knee': 'mixamorig:RightLeg',
    'Right ankle': 'mixamorig:RightFoot',
    'Right toe': 'mixamorig:RightToeBase',

    # Left Hand Fingers
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

    # Right Hand Fingers
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

def retarget_and_bake(anim_fbx_path, action_name):
    # Load base blend file
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    target_arm_obj = bpy.data.objects.get('Armature')
    
    # Import source FBX
    bpy.ops.import_scene.fbx(filepath=anim_fbx_path)
    
    # Find imported source armature
    source_arm_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj != target_arm_obj:
            source_arm_obj = obj
            break
            
    if not source_arm_obj:
        print(f"Could not find imported source armature for {anim_fbx_path}")
        return None
        
    print(f"Retargeting {anim_fbx_path} from {source_arm_obj.name} to {target_arm_obj.name}")
    
    # Get frame range from source action
    src_action = source_arm_obj.animation_data.action if source_arm_obj.animation_data else None
    if not src_action:
        print("No source action found!")
        return None
        
    start_frame = int(src_action.frame_range[0])
    end_frame = int(src_action.frame_range[1])
    print(f"Action '{action_name}' frame range: {start_frame} to {end_frame}")
    
    # Switch to Pose mode on target armature and add Copy Rotation constraints
    bpy.context.view_layer.objects.active = target_arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    # Clear existing constraints
    for pb in target_arm_obj.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
            
    # Add constraints
    for tgt_bone, src_bone in bone_mapping.items():
        if tgt_bone in target_arm_obj.pose.bones and src_bone in source_arm_obj.pose.bones:
            pb = target_arm_obj.pose.bones[tgt_bone]
            crc = pb.constraints.new(type='COPY_ROTATION')
            crc.target = source_arm_obj
            crc.subtarget = src_bone
            crc.target_space = 'WORLD'
            crc.owner_space = 'WORLD'
            
    # Also copy Hips location (Z/Y translation) if desired, but keep grounded
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

    # Select all pose bones on target
    bpy.ops.pose.select_all(action='SELECT')
    
    # Bake action
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
    print(f"Successfully baked action '{action_name}' on target armature!")
    
    # Delete source armature object
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(source_arm_obj, do_unlink=True)
    
    return baked_action

# Test baking Idle
idle_action = retarget_and_bake(idle_fbx, "Idle")

# Test baking Talking
talk_action = retarget_and_bake(talk_fbx, "Talking")

print("RETARGET AND BAKE TEST COMPLETE!")
