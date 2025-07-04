from MayaData.data.base import BaseData
from MayaData.data.tree import Tree
from MayaData.lib import hash, decorator

from maya.api import OpenMaya

import copy

DEFAULT_DATA = {'name': str(), 'matrix': None, 'orient': list(), 'rotation': list(), 'radius': float(),
                'rotateOrder': float(), 'side': float(), 'type': float()}


def _traverse_to_root(joint):
    obj = OpenMaya.MSelectionList().add(joint).getDependNode(0)
    obj_mfn = OpenMaya.MFnTransform(obj)
    while not obj_mfn.parent(0).hasFn(OpenMaya.MFn.kWorld):
        obj_mfn = OpenMaya.MFnTransform(obj_mfn.parent(0))
    return obj_mfn.object()


def _get_attributes(joint, include_namespace):
    mfn_node = OpenMaya.MFnTransform(joint)
    jnt_name = mfn_node.partialPathName()
    if not include_namespace:
        jnt_name = jnt_name.split(':')[-1]
    data = copy.deepcopy(DEFAULT_DATA)
    data['name'] = jnt_name
    data['matrix'] = list(mfn_node.transformationMatrix())

    orient_plug = mfn_node.findPlug('jointOrient', False)
    for i in range(orient_plug.numChildren()):
        data['orient'].append(orient_plug.child(i).asDouble())
    for j in ['rx', 'ry', 'rz']:
        data['rotation'].append(mfn_node.findPlug(j, False).asDouble())
    for k in ['radius', 'rotateOrder', 'side', 'type']:
        data[k] = mfn_node.findPlug(k, False).asDouble()

    return data


def _set_attributes(joint, attributes):
    mfn_node = OpenMaya.MFnTransform(joint)

    matrix = OpenMaya.MMatrix(attributes['matrix'])
    matrix = OpenMaya.MTransformationMatrix(matrix)

    translation = matrix.translation(OpenMaya.MSpace.kWorld)
    for i, translate in zip(['tx', 'ty', 'tz'], [translation.x, translation.y, translation.z]):
        mfn_node.findPlug(i, False).setDouble(translate)

    for j, rotate in zip(attributes['rotation'], ['rx', 'ry', 'rz']):
        mfn_node.findPlug(rotate, False).setDouble(j)

    orient_plug = mfn_node.findPlug('jointOrient', False)
    for k, orient in zip(attributes['orient'], range(orient_plug.numChildren())):
        orient_plug.child(orient).setDouble(k)

    mfn_node.findPlug('radius', False).setDouble(attributes['radius'])

    for l in ['rotateOrder', 'side', 'type']:
        mfn_node.findPlug(l, False).setInt(int(attributes[l]))


@decorator.timer()
def get(name, from_root=True, include_namespace=True):
    obj = OpenMaya.MSelectionList().add(name).getDependNode(0)
    if from_root:
        obj = _traverse_to_root(name)

    dag_iter = OpenMaya.MItDag(OpenMaya.MItDag.kBreadthFirst, OpenMaya.MFn.kJoint)
    dag_iter.reset(obj)
    data = SkeletonData()

    first_item = None

    while not dag_iter.isDone():
        if not dag_iter.currentItem().hasFn(OpenMaya.MFn.kJoint):
            dag_iter.next()
            continue

        full_name = dag_iter.fullPathName()
        name_parts = full_name.split('|')[1:]
        attrs = _get_attributes(dag_iter.currentItem(), include_namespace)

        if first_item is None:
            first_item = name_parts
            if not from_root:
                # Then we need to get world transformations
                m_matrix = dag_iter.getPath().inclusiveMatrix()
                attrs['matrix'] = list(m_matrix)

                rotation = OpenMaya.MTransformationMatrix(m_matrix).rotation()
                attrs['rotation'] = [OpenMaya.MAngle(angle).asRadians() for angle in rotation]
                attrs['orient'] = [0, 0, 0]
            

        jnt_name = dag_iter.partialPathName()
        if not include_namespace:
            jnt_name = jnt_name.split(':')[-1]
        data['joints'].append(jnt_name)

        if not from_root:
            i = 0
            while i < len(first_item) and i < len(name_parts) and name_parts[i] == first_item[i]:
                i += 1
            full_name = '|'.join(name_parts[i - 1:] if i > 0 else name_parts)

        data.get_bone(full_name, attrs)
        dag_iter.next()

    return data


def _build_hierarchy(joint_data, parent=None):
    if not isinstance(joint_data, dict):
        return
    mod = OpenMaya.MDagModifier()
    jnt_obj = mod.createNode('joint', OpenMaya.MObject.kNullObj)
    
    if parent:
        mod.reparentNode(jnt_obj, parent)
        
    mod.renameNode(jnt_obj, joint_data['name'])
    mod.doIt()

    _set_attributes(jnt_obj, joint_data)

    for val in joint_data.values():
        _build_hierarchy(val, jnt_obj)


@decorator.timer()
def load(data=None):
    if not data:
        data = SkeletonData()
        data.load()

    for val in data.values():
        _build_hierarchy(val)
    return data


class SkeletonData(BaseData, Tree):
    def __init__(self, *args, **kwargs):
        super(SkeletonData, self).__init__(*args, **kwargs)
        self['joints'] = list()

    def get_bone(self, full_path_name, attributes):
        int_name = hash.string_to_int(full_path_name)
        print(full_path_name)
        self.custom_node = attributes
        self.add_node(*int_name)
