import bpy
from mathutils import Matrix
from os import path
from . anm import Anm, InvalidAnmFormat

POSEDATA_PREFIX = 'pose.bones["%s"].'


def invalid_file_format(self, context):
    self.layout.label(text='Invalid anim file!')


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to import animation')


def bones_number_mismatch(self, context):
    self.layout.label(text='Bones number mismatch')


def set_keyframe(curves, frame, values):
    for i, c in enumerate(curves):
        c.keyframe_points.add(1)
        c.keyframe_points[-1].co = frame, values[i]
        c.keyframe_points[-1].interpolation = 'LINEAR'


def create_action(arm_obj, anm, fps):
    act = bpy.data.actions.new('action')
    curves_loc, curves_rot = [], []
    loc_mats, prev_rots = {}, {}

    for pose_bone in arm_obj.pose.bones:
        g = act.groups.new(name=pose_bone.name)
        cl = [act.fcurves.new(data_path=(POSEDATA_PREFIX % pose_bone.name) + 'location', index=i) for i in range(3)]
        cr = [act.fcurves.new(data_path=(POSEDATA_PREFIX % pose_bone.name) + 'rotation_quaternion', index=i) for i in range(4)]

        for c in cl:
            c.group = g

        for c in cr:
            c.group = g

        curves_loc.append(cl)
        curves_rot.append(cr)
        pose_bone.rotation_mode = 'QUATERNION'
        pose_bone.location = (0, 0, 0)
        pose_bone.rotation_quaternion = (1, 0, 0, 0)

        bone = arm_obj.data.bones.get(pose_bone.name)
        loc_mat = bone.matrix_local.copy()
        if bone.parent:
            loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat
        loc_mats[pose_bone] = loc_mat
        prev_rots[pose_bone] = None

    set_kfs = []

    arm_bones_num, anm_bones_num = len(arm_obj.pose.bones), len(anm.offsets[0])
    if arm_bones_num > anm_bones_num:
        arm_bones_num = anm_bones_num

    for off in anm.offsets:
        for bone_id, pose_bone in enumerate(arm_obj.pose.bones[:arm_bones_num]):
            kf_id = off[bone_id]

            if kf_id in set_kfs:
                continue
            set_kfs.append(kf_id)

            kf = anm.keyframes[kf_id]
            time = anm.times[kf.time_id]

            loc_mat = loc_mats[pose_bone]
            loc_pos = loc_mat.to_translation()
            loc_rot = loc_mat.to_quaternion()

            rot = loc_rot.rotation_difference(kf.rot)

            prev_rot = prev_rots[pose_bone]
            if prev_rot:
                alt_rot = rot.copy()
                alt_rot.negate()
                if rot.rotation_difference(prev_rot).angle > alt_rot.rotation_difference(prev_rot).angle:
                    rot = alt_rot
            prev_rots[pose_bone] = rot

            set_keyframe(curves_loc[bone_id], time * fps, kf.loc - loc_pos)
            set_keyframe(curves_rot[bone_id], time * fps, rot)

    return act

def load(context, filepath, fps):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    try:
        anm = Anm.load(filepath)
    except InvalidAnmFormat:
        context.window_manager.popup_menu(invalid_file_format, title='Error', icon='ERROR')
        return {'CANCELLED'}

    arm_bones_num, anm_bones_num = len(arm_obj.pose.bones), len(anm.offsets[0])
    if arm_bones_num != anm_bones_num:
        context.window_manager.popup_menu(bones_number_mismatch, title='Error', icon='ERROR')

    animation_data = arm_obj.animation_data
    if not animation_data:
        animation_data = arm_obj.animation_data_create()

    bpy.ops.object.mode_set(mode='POSE')

    act = create_action(arm_obj, anm, fps)
    act.name = path.basename(filepath)
    animation_data.action = act

    max_frame = 0
    for fcu in act.fcurves:
        for kfp in fcu.keyframe_points:
            max_frame = max(max_frame, kfp.co[0])

    context.scene.frame_start = 0
    context.scene.frame_end = round(max_frame)

    bpy.ops.object.mode_set(mode='OBJECT')

    return {'FINISHED'}
