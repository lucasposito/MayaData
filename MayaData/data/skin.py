from MayaData.data.base import BaseData
from MayaData.lib import get_node, undo, decorator

from maya.api import OpenMaya, OpenMayaAnim
from maya import cmds

import numpy as np


@decorator.timer()
def get(name):

    data = SkinData()
    mfn_skin = get_node.skin_cluster(name)
    mfn_skin = OpenMayaAnim.MFnSkinCluster(mfn_skin)

    mesh_path = mfn_skin.getPathAtIndex(0)
    mesh_node = mesh_path.node()

    vertex_mfn = OpenMaya.MItMeshVertex(mesh_node)
    indices = range(vertex_mfn.count())

    id_component = OpenMaya.MFnSingleIndexedComponent()
    vtx_component = id_component.create(OpenMaya.MFn.kMeshVertComponent)
    id_component.addElements(indices)

    influence_objects = mfn_skin.influenceObjects()
    influences = [x.partialPathName() for x in influence_objects]

    wts, num_inf = mfn_skin.getWeights(mesh_path, vtx_component)

    skin_data = np.array(wts).reshape(vertex_mfn.count(), num_inf)
    data.update({influence: skin_data[:, idx].tolist() for idx, influence in enumerate(influences)})

    return data


@decorator.timer()
def load(data=None, name=None):
    if not data:
        data = SkinData()
        data.load()

    if not name:
        name = OpenMaya.MGlobal.getActiveSelectionList().getDependNode(0)
        name = OpenMaya.MFnTransform(name).fullPathName()

    skin_cluster = get_node.skin_cluster(name)
    if skin_cluster:
        cmds.skinCluster(OpenMaya.MFnDependencyNode(skin_cluster).name(), edit=True, unbind=True, unbindKeepHistory=False)

    skin_cluster = cmds.skinCluster(list(data.keys()), name, bindMethod=1, mi=4, tsb=True)[0]
    skin_cluster = OpenMaya.MGlobal.getSelectionListByName(skin_cluster).getDependNode(0)

    skin_mfn = OpenMayaAnim.MFnSkinCluster(skin_cluster)

    mesh_path = skin_mfn.getPathAtIndex(0)
    mesh_node = mesh_path.node()

    vertex_mfn = OpenMaya.MItMeshVertex(mesh_node)
    indices = range(vertex_mfn.count())

    id_component = OpenMaya.MFnSingleIndexedComponent()
    vtx_component = id_component.create(OpenMaya.MFn.kMeshVertComponent)
    id_component.addElements(indices)

    influence_objects = skin_mfn.influenceObjects()
    influence_index = OpenMaya.MIntArray(len(influence_objects), 0)
    for x in range(len(influence_objects)):
        influence_index[x] = int(skin_mfn.indexForInfluenceObject(influence_objects[x]))

    weights = np.array(list(data.values())).T.flatten()
    skin_mfn.setWeights(mesh_path, vtx_component, influence_index, OpenMaya.MDoubleArray(weights))


class SkinData(BaseData):
    def __init__(self):
        super(SkinData, self).__init__()
