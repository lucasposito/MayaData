from math import *
from maya.api import OpenMaya


def aim_matrix(aim_vector, up_vector):
    """
    Builds the orientation from two vectors.
    It behaves with the same logic as an aim constraint,
    with main vector as the aiming axis and the secondary as the up axis.

    :param aim_vector: OpenMaya.MVector
    :param up_vector: OpenMaya.MVector
    :return: OpenMaya.MMatrix
    """
    aim_axis = OpenMaya.MVector().kYaxisVector
    up_axis = OpenMaya.MVector().kXaxisVector

    obj_u = aim_vector.normal()
    obj_w = (obj_u ^ up_vector).normal()
    obj_v = obj_w ^ obj_u

    quat_u = OpenMaya.MQuaternion(aim_axis, obj_u)
    up_axis_rotated = up_axis.rotateBy(quat_u)

    angle = math.acos(up_axis_rotated * obj_v)
    quat_v = OpenMaya.MQuaternion(angle, obj_u)

    if not obj_v.isEquivalent(up_axis_rotated.rotateBy(quat_v), 1.0e-1):
        angle = (2 * math.pi) - angle
        quat_v = OpenMaya.MQuaternion(angle, obj_u)

    mod = OpenMaya.MDagModifier()
    target_obj = mod.createNode('transform', OpenMaya.MObject.kNullObj)
    mod.doIt()

    quat = quat_u * quat_v
    target_mfn = OpenMaya.MFnTransform(target_obj)
    target_mfn.setRotation(quat, OpenMaya.MSpace.kObject)
    result_matrix = target_mfn.getPath().inclusiveMatrix()

    OpenMaya.MDagModifier().deleteNode(target_obj).doIt()
    return result_matrix


def pole_vector():
    pass


def orient():
    pass
