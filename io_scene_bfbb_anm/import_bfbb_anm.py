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


def translation_matrix(v):
    return Matrix.Translation(v)


def local_to_basis_matrix(local_matrix, global_matrix, parent_matrix):
    return global_matrix.inverted() @ (parent_matrix @ local_matrix)


def create_action(arm_obj, anm, fps):
    act = bpy.data.actions.new('action')
    curves_loc, curves_rot = [], []
    prev_rots = {}

    for bone in arm_obj.data.bones:
        g = act.groups.new(name=bone.name)
        cl = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone.name) + 'location', index=i) for i in range(3)]
        cr = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone.name) + 'rotation_quaternion', index=i) for i in range(4)]

        for c in cl + cr:
            c.group = g

        curves_loc.append(cl)
        curves_rot.append(cr)

        pose_bone = arm_obj.pose.bones[bone.name]
        pose_bone.rotation_mode = 'QUATERNION'
        pose_bone.location = (0, 0, 0)
        pose_bone.rotation_quaternion = (1, 0, 0, 0)

        prev_rots[bone] = None

    set_kfs = []

    arm_bones_num, anm_bones_num = len(arm_obj.pose.bones), len(anm.offsets[0])
    if arm_bones_num > anm_bones_num:
        arm_bones_num = anm_bones_num

    for off in anm.offsets:
        for bone_id, bone in enumerate(arm_obj.data.bones[:arm_bones_num]):
            kf_id = off[bone_id]

            if kf_id in set_kfs:
                continue
            set_kfs.append(kf_id)

            kf = anm.keyframes[kf_id]
            time = anm.times[kf.time_id]

            rest_mat = bone.matrix_local
            if bone.parent:
                parent_mat = bone.parent.matrix_local
                local_rot = (parent_mat.inverted_safe() @ rest_mat).to_quaternion()
            else:
                parent_mat = Matrix.Identity(4)
                local_rot = rest_mat.to_quaternion()

            mat = translation_matrix(kf.loc)
            mat_basis = local_to_basis_matrix(mat, rest_mat, parent_mat)
            loc = mat_basis.to_translation()

            rot = local_rot.rotation_difference(kf.rot)

            # Correction opposite direction of rotation
            prev_rot = prev_rots[bone]
            if prev_rot:
                alt_rot = rot.copy()
                alt_rot.negate()
                if rot.rotation_difference(prev_rot).angle > alt_rot.rotation_difference(prev_rot).angle:
                    rot = alt_rot
            prev_rots[bone] = rot

            set_keyframe(curves_loc[bone_id], time * fps, loc)
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
