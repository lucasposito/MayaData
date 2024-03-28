from MayaData.data.base import BaseData
from MayaData.lib import get_node, undo, decorator

from maya.api import OpenMaya, OpenMayaAnim
from maya import cmds


def remove_unused_influences(data):

    new_weights = dict()
    used_inf = dict()

    for vtx, values in data['weights'].items():
        new = {inf: value for inf, value in values.items() if value != 0}
        for inf in new:
            if inf not in used_inf:
                used_inf[inf] = data['influences'][inf]
        new_weights[vtx] = new

    remapped_data = {'influences': dict(), 'weights': dict()}

    remap = dict()
    for new_index, (old_index, name) in enumerate(used_inf.items()):
        remap[old_index] = new_index
        remapped_data['influences'][new_index] = name

    for vtx, values in new_weights.items():
        new = {remap[key]: value for key, value in values.items()}
        remapped_data['weights'][vtx] = new

    for key, value in data.items():
        if key in ['influences', 'weights']:
            continue
        remapped_data[key] = value

    return remapped_data


@decorator.timer()
def get(name):
    # TODO: Find a way to avoid writing unused influences at all instead of running a cleaning function later
    data = SkinData()
    data['geometry'] = name

    mfn_skin = get_node.skin_cluster(name)
    mfn_skin = OpenMayaAnim.MFnSkinCluster(mfn_skin)
    data['max_influence'] = mfn_skin.findPlug('maxInfluences', False).asInt()

    for obj in mfn_skin.influenceObjects():
        data['influences'][int(mfn_skin.indexForInfluenceObject(obj))] = obj.partialPathName()

    weight_list_plug = mfn_skin.findPlug("weightList", 0)
    weight_plug = mfn_skin.findPlug("weights", 0)
    weight_list_attr = weight_list_plug.attribute()

    for vId in range(weight_list_plug.numElements()):
        weights = {}
        weight_plug.selectAncestorLogicalIndex(vId, weight_list_attr)
        influence_ids = weight_plug.getExistingArrayAttributeIndices()
        inf_plug = OpenMaya.MPlug(weight_plug)
        for inf_id in influence_ids:
            inf_plug.selectAncestorLogicalIndex(inf_id)
            try:
                weights[inf_id] = inf_plug.asDouble()
            except KeyError:
                pass

        total_sum = sum(weights.values())
        normalized_weights = {inf_id: round(weight / total_sum, 4) for inf_id, weight in weights.items()}

        data['weights'][vId] = normalized_weights

    return remove_unused_influences(data)


def _reset_skin_weights(cluster_name, influences):
    shape = cmds.listConnections("{}.outputGeometry".format(cluster_name))[0]
    for inf in influences:
        cmds.setAttr("{0}.lockInfluenceWeights".format(inf))
    skin_norm = cmds.getAttr("{0}.normalizeWeights".format(cluster_name))
    if skin_norm != 0:
        cmds.setAttr("{0}.normalizeWeights".format(cluster_name), 0)
    cmds.skinPercent(cluster_name, shape, normalize=False, pruneWeights=100)
    cmds.setAttr("{0}.normalizeWeights".format(cluster_name), skin_norm)


@decorator.timer()
def load(data=None, name=None):
    if not data:
        data = SkinData()
        data.load()

    if name:
        data['geometry'] = name

    skin_cluster = get_node.skin_cluster(data['geometry'])
    if skin_cluster:
        cmds.skinCluster(OpenMaya.MFnDependencyNode(skin_cluster).name(), edit=True, unbind=True, unbindKeepHistory=False)

    cluster_name = cmds.skinCluster(list(data['influences'].values()), data['geometry'],
                                    bindMethod=1, mi=data['max_influence'], tsb=True)[0]

    with undo.UndoContext():
        _reset_skin_weights(cluster_name, data['influences'].values())
        for vId, weight in data['weights'].items():
            weight_attr = '{}.weightList[{}]'.format(cluster_name, vId)
            for inf_id, inf_value in weight.items():
                attr = '.weights[{}]'.format(inf_id)
                full_attr = weight_attr + attr
                cmds.setAttr(full_attr, cmds.getAttr(full_attr) + inf_value)
    

class SkinData(BaseData):
    def __init__(self):
        super(SkinData, self).__init__()
        self['geometry'] = str()
        self['weights'] = dict()
        self['influences'] = dict()
        self['max_influence'] = int()
