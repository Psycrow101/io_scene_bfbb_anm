import bpy
from collections import defaultdict
from mathutils import Matrix
from . anm import Anm, AnmKeyframe


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to export animation')


def missing_action(self, context):
    self.layout.label(text='No action for active armature. Nothing to export')


def basis_to_local_matrix(basis_matrix, global_matrix, parent_matrix):
    return parent_matrix.inverted() @ global_matrix @ basis_matrix


def is_matrix_interpolated(prev_mat, curr_mat, next_mat):
    mat = prev_mat.lerp(next_mat, 0.5)
    loc_diff = (mat.to_translation() - curr_mat.to_translation()).length
    rot_diff = mat.to_quaternion().rotation_difference(curr_mat.to_quaternion()).angle
    return loc_diff + rot_diff < 0.000001


def get_action_range(arm_obj, act):
    frame_start, frame_end = None, None

    for curve in act.fcurves:
        if 'pose.bones' not in curve.data_path:
            continue

        bone_name = curve.data_path.split('"')[1]
        if arm_obj.data.bones.find(bone_name) is None:
            continue

        for kp in curve.keyframe_points:
            time = kp.co[0]
            if frame_start is None:
                frame_start, frame_end = time, time
            else:
                frame_start = min(frame_start, time)
                frame_end = max(frame_end, time)

    return int(frame_start), round(frame_end)


def create_anm(context, arm_obj, act, fps, flags):
    offsets, keyframes, times = [], [], []

    old_frame = context.scene.frame_current
    frame_start, frame_end = get_action_range(arm_obj, act)
    bone_basis_matrices = defaultdict(list)

    if frame_start is None:
        return None

    context.scene.frame_set(frame_start)
    context.view_layer.update()

    for frame in range(frame_start, frame_end + 1):
        context.scene.frame_set(frame)
        context.view_layer.update()

        for bone_id, pose_bone in enumerate(arm_obj.pose.bones):
            bone_basis_matrices[bone_id].append(pose_bone.matrix_basis.copy())

        offsets.append([])
        times.append((frame - frame_start) / fps)

    times.append((frame_end - frame_start + 1) / fps)

    for bone_id, basis_matrices in sorted(bone_basis_matrices.items()):
        bone = arm_obj.data.bones[bone_id]

        rest_mat = bone.matrix_local
        if bone.parent:
            parent_mat = bone.parent.matrix_local
        else:
            parent_mat = Matrix.Identity(4)

        last_basis_mat = None
        for time_id, basis_mat in enumerate(basis_matrices):
            is_uniq_kf = False
            if basis_mat != last_basis_mat:
                if time_id > 0 and time_id < len(basis_matrices) - 1:
                    prev_basis_mat = basis_matrices[time_id - 1]
                    next_basis_mat = basis_matrices[time_id + 1]
                    is_uniq_kf = not is_matrix_interpolated(prev_basis_mat, basis_mat, next_basis_mat)
                else:
                    is_uniq_kf = True

            if is_uniq_kf:
                loc_mat = basis_to_local_matrix(basis_mat, rest_mat, parent_mat)
                kf_pos, kf_rot = loc_mat.to_translation(), loc_mat.to_quaternion()
                keyframes.append(AnmKeyframe(time_id, kf_pos, kf_rot))

            last_basis_mat = basis_mat
            offsets[time_id].append(len(keyframes) - 1)

    context.scene.frame_set(old_frame)
    context.view_layer.update()

    return Anm(flags, offsets, keyframes, times)


def save(context, filepath, fps, flags, endian):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    act = None
    animation_data = arm_obj.animation_data
    if animation_data:
        act = animation_data.action

    anm = None
    if act:
        anm = create_anm(context, arm_obj, act, fps, flags)

    if not anm:
        context.window_manager.popup_menu(missing_action, title='Error', icon='ERROR')
        return {'CANCELLED'}

    anm.save(filepath, endian)

    return {'FINISHED'}
