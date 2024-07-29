from MayaData.data.base import BaseData
from MayaData.lib import undo, decorator

from maya.api import OpenMaya, OpenMayaAnim
from maya import cmds

import numpy as np
import pandas as pd


def get_skin_cluster(mesh):
    """
    :param str mesh:
    :return: Skin cluster attached to the mesh
    :rtype: str/None
    """
    dag = OpenMaya.MSelectionList().add(mesh).getDagPath(0)
    dag = dag.extendToShape()
    obj = dag.node()

    skin = None
    dag_iter = OpenMaya.MItDependencyGraph(obj,
                                           OpenMaya.MItDependencyGraph.kDownstream,
                                           OpenMaya.MItDependencyGraph.kPlugLevel)
    while not dag_iter.isDone():
        current_item = dag_iter.currentNode()
        if current_item.hasFn(OpenMaya.MFn.kSkinClusterFilter):
            skin = current_item
            break
        dag_iter.next()
    return skin


def keep_influences(skin_data, influences_to_keep, base_joint):
    skin_data = pd.DataFrame(skin_data)

    remove = [i for i in skin_data.columns if i not in influences_to_keep + [base_joint]]

    skin_data.drop(remove, axis=1, inplace=True)

    for index, row in skin_data.iterrows():
        difference = 1.0 - row.sum()
        skin_data.at[index, base_joint] += difference

    return skin_data.to_dict(orient='list')


@decorator.timer()
def get(name):

    data = SkinData()
    mfn_skin = get_skin_cluster(name)
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

    skin_cluster = get_skin_cluster(name)
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
