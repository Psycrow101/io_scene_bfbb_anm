import bpy
from dataclasses import dataclass
from mathutils import Quaternion, Vector
from . anm import Anm, AnmKeyframe


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to export animation')


def missing_action(self, context):
    self.layout.label(text='No action for active armature. Nothing to export')


@dataclass
class PoseBoneTransform:
    pos: Vector
    rot: Quaternion

    def calc_kf(self, mat):
        kf_pos = self.pos + mat.to_translation()
        kf_rot = mat.inverted_safe().to_quaternion().rotation_difference(self.rot)
        return kf_pos, kf_rot


def get_bone_transform(pose_bone):
    pos = pose_bone.location.copy()
    if pose_bone.rotation_mode == 'QUATERNION':
        rot = pose_bone.rotation_quaternion.copy()
    else:
        rot = pose_bone.rotation_euler.to_quaternion()
    return PoseBoneTransform(pos, rot)


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
    bone_transforms = {}

    if frame_start is None:
        return None

    context.scene.frame_set(frame_start)
    context.view_layer.update()

    for frame in range(frame_start, frame_end + 1):
        context.scene.frame_set(frame)
        context.view_layer.update()

        for bone_id, pose_bone in enumerate(arm_obj.pose.bones):
            if frame == frame_start:
                bone_transforms[bone_id] = [get_bone_transform(pose_bone)]
            else:
                bone_transforms[bone_id].append(get_bone_transform(pose_bone))

        offsets.append([])
        times.append((frame - frame_start) / fps)

    times.append((frame_end - frame_start + 1) / fps)

    for bone_id, transforms in sorted(bone_transforms.items()):
        bone = arm_obj.data.bones[bone_id]

        loc_mat = bone.matrix_local.copy()
        if bone.parent:
            loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat

        last_trans = None
        for time_id, trans in enumerate(transforms):
            if last_trans is None or trans != last_trans:
                kf_pos, kf_rot = trans.calc_kf(loc_mat)
                keyframes.append(AnmKeyframe(time_id, kf_pos, kf_rot))
            last_trans = trans
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
