from maya.api import OpenMaya
from maya import cmds

import math


def hik(global_ctr='global_C0_ctl', switch_attr='mocapAttach'):
    """
    "global_C0_ctl.mocapAttach" follows MGear name convention
    """

    ctr_obj = OpenMaya.MSelectionList().add(global_ctr).getDependNode(0)
    ctr_mfn = OpenMaya.MFnDagNode(ctr_obj)

    selected = OpenMaya.MGlobal.getActiveSelectionList()
    obj1_mfn = OpenMaya.MFnDagNode(selected.getDependNode(0))
    obj2_mfn = OpenMaya.MFnDagNode(selected.getDependNode(1))

    const = cmds.parentConstraint(obj1_mfn.name(), obj2_mfn.name())[0]
    const = selected.add(const).getDependNode(2)
    const_mfn = OpenMaya.MFnDagNode(const)

    mod = OpenMaya.MDGModifier()
    blend = mod.createNode('pairBlend')
    mod.doIt()

    blend_mfn = OpenMaya.MFnDependencyNode(blend)

    mocap_plug = ctr_mfn.findPlug(switch_attr, False)
    weight_plug = blend_mfn.findPlug('weight', False)
    OpenMaya.MDagModifier().connect(mocap_plug, weight_plug).doIt()

    for vec in ['x', 'y', 'z']:
        mod = OpenMaya.MDGModifier()
        crv_t = mod.createNode('animCurveTL')
        crv_r = mod.createNode('animCurveTA')
        mod.doIt()

        out_t = OpenMaya.MFnDependencyNode(crv_t).findPlug('output', False)
        t1 = blend_mfn.findPlug(f'inTranslate{vec.upper()}1', False)
        OpenMaya.MDGModifier().connect(out_t, t1).doIt()

        cont_t = const_mfn.findPlug(f'constraintTranslate{vec.upper()}', False)
        t2 = blend_mfn.findPlug(f'inTranslate{vec.upper()}2', False)

        blend_t = blend_mfn.findPlug(f'outTranslate{vec.upper()}', False)
        obj2_t = obj2_mfn.findPlug(f't{vec}', False)

        out_r = OpenMaya.MFnDependencyNode(crv_r).findPlug('output', False)
        r1 = blend_mfn.findPlug(f'inRotate{vec.upper()}1', False)
        OpenMaya.MDGModifier().connect(out_r, r1).doIt()

        cont_r = const_mfn.findPlug(f'constraintRotate{vec.upper()}', False)
        r2 = blend_mfn.findPlug(f'inRotate{vec.upper()}2', False)

        blend_r = blend_mfn.findPlug(f'outRotate{vec.upper()}', False)
        obj2_r = obj2_mfn.findPlug(f'r{vec}', False)

        mod = OpenMaya.MDGModifier()
        mod.disconnect(cont_t, obj2_t)
        mod.disconnect(cont_r, obj2_r)

        mod.connect(cont_t, t2)
        mod.connect(blend_t, obj2_t)

        mod.connect(cont_r, r2)
        mod.connect(blend_r, obj2_r)

        mod.doIt()


def matrix(driver, driven, mirrored=False, offset=None):
    temp_list = OpenMaya.MSelectionList()
    driver_matrix = OpenMaya.MTransformationMatrix(temp_list.add(driver).getDagPath(0).inclusiveMatrix())

    driven = temp_list.add(driven)
    driven_mfn = OpenMaya.MFnTransform(driven.getDependNode(1))

    if offset:
        if not isinstance(offset, OpenMaya.MMatrix):
            offset = OpenMaya.MSelectionList().add(offset).getDagPath(0).inclusiveMatrix()
        driven_matrix = temp_list.getDagPath(1).inclusiveMatrix()

        offset_matrix = driven_matrix * offset.inverse()
        driver_matrix = OpenMaya.MTransformationMatrix(offset_matrix * driver_matrix.asMatrix())

    if not driven_mfn.parent(0).hasFn(OpenMaya.MFn.kWorld):
        parent_matrix = OpenMaya.MFnDagNode(driven_mfn.parent(0)).getPath().inclusiveMatrix()
        parent_matrix = OpenMaya.MTransformationMatrix(parent_matrix)

        driver_matrix = OpenMaya.MTransformationMatrix(driver_matrix.asMatrix() * parent_matrix.asMatrixInverse())

    if mirrored:
        Y_rotation = OpenMaya.MQuaternion().setToYAxis(math.radians(180))
        X_rotation = OpenMaya.MQuaternion().setToXAxis(math.radians(180))
        driver_matrix.setRotation(Y_rotation * driver_matrix.rotation(asQuaternion=True))
        driver_matrix.setRotation(X_rotation * driver_matrix.rotation(asQuaternion=True))

    driven_mfn.setTransformation(driver_matrix)
