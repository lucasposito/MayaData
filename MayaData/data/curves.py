from MayaData.data.base import BaseData
from MayaData.lib import decorator

from maya.api import OpenMaya
from maya import cmds
import json
import numpy as np
import pandas as pd


# with open(str(VAR.MAIN_PATH / 'lib' / 'templates' / 'shape.json'), 'r') as f:
#     shapes = json.loads(f.read())

# TODO: If it's a multi shapes node, transform it into single shape

@decorator.timer()
def get():
    data = CurveData()
    iter = OpenMaya.MItSelectionList(OpenMaya.MGlobal.getActiveSelectionList())

    while not iter.isDone():
        points = get_shape(iter.getDagPath())
        name = OpenMaya.MFnTransform(iter.getDependNode()).partialPathName()
        color = get_color(iter.getDagPath())

        shape_node = iter.getDagPath().extendToShape()

        data['degrees'].append(OpenMaya.MFnDagNode(shape_node).findPlug('degree', False).asInt())
        data['names'].append(name)
        data['shapes'].append(points)
        data['colors'].append(color)
        iter.next()

    return data


@decorator.timer()
def load(data=None):
    if not data:
        data = CurveData()
        data.load()
    data = pd.DataFrame(data)
    for row in data.itertuples(index=False):
        shape, color, name, degree = row.shapes, row.colors, row.names, row.degrees
        if cmds.objExists(name):
            curve = replace(shape, name, degree)
        else:
            curve = load_shape(shape, name, degree)
        load_color(color, curve)


def object_size(node):
    shape = cmds.listRelatives(node, s=True, f=True)
    min_size = cmds.getAttr('%s.boundingBoxMin' % shape[0])[0]
    max_size = cmds.getAttr('%s.boundingBoxMax' % shape[0])[0]

    width = max_size[0] - min_size[0]
    height = max_size[1] - min_size[1]
    depth = max_size[2] - min_size[2]

    return width, height, depth


def size_difference(size1, size2):
    volume1 = size1[0] * size1[1] * size1[2]
    volume2 = size2[0] * size2[1] * size2[2]

    result = (volume1 / volume2) ** (1. / 3)
    return result


def get_shape(name=None):
    curve = OpenMaya.MSelectionList()

    if not name:
        curve = OpenMaya.MGlobal.getActiveSelectionList()
        if curve.isEmpty():
            return
        curve = curve.getDagPath(0).extendToShape()
    else:
        curve = curve.add(name).getDagPath(0).extendToShape()

    curve_mfn = OpenMaya.MFnNurbsCurve(curve)

    return [list(pt) for pt in list(curve_mfn.cvPositions())]


def load_shape(points, name=None, degree=None):
    if not degree:
        degree = 3
    num_knots = len(points) + degree - 1
    knots = OpenMaya.MDoubleArray(np.arange(0, num_knots, 1.0))

    new = OpenMaya.MFnNurbsCurve()
    new.create(points, knots, degree, OpenMaya.MFnNurbsCurve.kOpen, False, False)
    new = new.parent(0)

    if not name:
        name = 'curve'

    mod = OpenMaya.MDGModifier()
    mod.renameNode(new, name)
    mod.doIt()

    OpenMaya.MGlobal.setActiveSelectionList(OpenMaya.MSelectionList().add(new))

    return OpenMaya.MFnTransform(new).partialPathName()


def set_line(point_a, point_b, name=None):
    if not name:
        name = 'curve'

    line = cmds.curve(n=name, d=1, p=[point_a, point_b])
    cmds.rename(cmds.listRelatives(line, s=True, f=True), f'{line}Shape')
    return line


def get_color(name=None):
    curve = OpenMaya.MSelectionList()

    if not name:
        curve = OpenMaya.MGlobal.getActiveSelectionList()
        if curve.isEmpty():
            return
        curve = curve.getDagPath(0).extendToShape()
    else:
        curve = curve.add(name).getDagPath(0).extendToShape()

    curve_mfn = OpenMaya.MFnDagNode(curve)
    if curve_mfn.findPlug('overrideEnabled', False).asBool():
        if curve_mfn.findPlug('overrideRGBColors', False).asBool():
            value = curve_mfn.findPlug('overrideColorRGB', False)
            value = [value.child(i).asDouble() for i in range(value.numChildren())]
            return value
        value = curve_mfn.findPlug('overrideColor', False).asDouble()
        return value
    return float()


def load_color(color, name=None):
    curve = OpenMaya.MSelectionList()

    if not name:
        curve = OpenMaya.MGlobal.getActiveSelectionList()
        if curve.isEmpty():
            return
        curve = curve.getDagPath(0).extendToShape()
    else:
        curve = curve.add(name).getDagPath(0).extendToShape()

    color_type = True if isinstance(color, list) else False
    curve_mfn = OpenMaya.MFnDagNode(curve)

    curve_mfn.findPlug('overrideEnabled', False).setBool(True)
    curve_mfn.findPlug('overrideRGBColors', False).setBool(color_type)
    if color_type:
        rgb_plug = curve_mfn.findPlug('overrideColorRGB', False)
        for a, b in zip(range(rgb_plug.numChildren()), color):
            rgb_plug.child(a).setDouble(b)
        return
    curve_mfn.findPlug('overrideColor', False).setDouble(color)


# def set_size(value=None):
#     selected = cmds.ls(sl=True)
#     if not selected:
#         return
#     if not value:
#         if not _size_cache:
#             return
#         value = _size_cache
#
#     for each in selected:
#         if isinstance(value, tuple):
#             value = size_difference(value, object_size(each))
#         shape_nodes = cmds.listRelatives(each, s=True, f=True)
#         curve_pivot = cmds.xform(each, q=True, ws=True, piv=True)[:3]
#         for crv in shape_nodes:
#             cmds.scale(value, value, value, '{}.cv[*]'.format(crv), r=True, p=curve_pivot)
#
#
# def get_size():
#     global _size_cache
#     shape = cmds.listRelatives(cmds.ls(sl=True, l=True), s=True, f=True)[0]
#     if not shape:
#         _size_cache = None
#         return
#     _size_cache = object_size(shape)
#     return _size_cache

def replace(points, name=None, degree=None):
    target_shape = OpenMaya.MSelectionList()

    if not name:
        target_shape = OpenMaya.MGlobal.getActiveSelectionList()
        if target_shape.isEmpty():
            return
        target_shape = target_shape.getDagPath(0).extendToShape()
    else:
        target_shape = target_shape.add(name).getDagPath(0).extendToShape()

    if not degree:
        degree = 3

    curve_name = load_shape(points, degree=degree)
    curve_dag = OpenMaya.MSelectionList().add(curve_name).getDagPath(0)

    sources, destinations = list(), list()
    target_mfn = OpenMaya.MFnDagNode(target_shape)

    curve_mfn = OpenMaya.MFnDagNode(curve_dag.extendToShape())

    for plug in target_mfn.getConnections():
        if plug.partialName(useLongNames=1) != 'visibility':
            continue
        sources.append(plug.source())
        destinations.append(plug.partialName(useLongNames=1))

    mod = OpenMaya.MDagModifier()
    null = mod.createNode('transform', OpenMaya.MObject.kNullObj)

    mod.reparentNode(curve_dag.extendToShape().node(), target_mfn.parent(0))
    mod.reparentNode(target_shape.node(), null)
    mod.renameNode(curve_mfn.object(), target_mfn.name())
    mod.doIt()

    cmds.delete([curve_name, OpenMaya.MFnTransform(null).fullPathName()])

    mod = OpenMaya.MDGModifier()
    for src, dst in zip(sources, destinations):
        dst_plug = curve_mfn.findPlug(dst, False)
        mod.connect(src, dst_plug)
    mod.doIt()

    return curve_mfn.partialPathName()


class CurveData(BaseData):
    def __init__(self):
        super(CurveData, self).__init__()
        self['names'] = list()
        self['shapes'] = list()
        self['colors'] = list()
        self['degrees'] = list()
