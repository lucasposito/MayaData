from maya.api import OpenMaya, OpenMayaAnim
from maya import cmds

from ..core import get_node, undo
from .base import BaseData

from future.utils import iteritems


def get(name):
    data = SkinData()
    data['geometry'] = name

    mfn_skin = get_node.skin_cluster(name)
    mfn_skin = OpenMayaAnim.MFnSkinCluster(mfn_skin)
    data['name'] = mfn_skin.name()
    
    for obj in mfn_skin.influenceObjects():
        data['influences'][int(mfn_skin.indexForInfluenceObject(obj))] = obj.partialPathName()
        
    weight_list_plug = mfn_skin.findPlug("weightList", 0)
    weight_plug = mfn_skin.findPlug("weights", 0)
    weight_list_attr = weight_list_plug.attribute()
    for vId in range(weight_list_plug.numElements()):
        vWeights = {}
        weight_plug.selectAncestorLogicalIndex(vId, weight_list_attr)
        influence_ids = weight_plug.getExistingArrayAttributeIndices()
        inf_plug = OpenMaya.MPlug(weight_plug)
        for inf_id in influence_ids:
            inf_plug.selectAncestorLogicalIndex(inf_id)
            try:
                vWeights[inf_id] = inf_plug.asDouble()
            except KeyError:
                pass
        data['weights'][vId] = vWeights
    return data


def _reset_skin_weights(data):
    shape = cmds.listConnections("{}.outputGeometry".format(data['name']))[0]
    for inf in data['influences'].values():
        cmds.setAttr("{0}.lockInfluenceWeights".format(inf))
    skin_norm = cmds.getAttr("{0}.normalizeWeights".format(data['name']))
    if skin_norm != 0:
        cmds.setAttr("{0}.normalizeWeights".format(data['name']), 0)
    cmds.skinPercent(data['name'], shape, normalize=False, pruneWeights=100)
    cmds.setAttr("{0}.normalizeWeights".format(data['name']), skin_norm)


def load(data=None, name=None):
    if not data:
        data = SkinData()
        data.load()

    if name:
        data['geometry'] = name

    skin_cluster = get_node.skin_cluster(data['geometry'])
    if skin_cluster:
        cmds.skinCluster(OpenMaya.MFnDependencyNode(skin_cluster).name(), edit=True, unbind=True, unbindKeepHistory=False)

    data['name'] = cmds.skinCluster(list(data['influences'].values()), data['geometry'],
                                    bindMethod=1, skinMethod=2, tsb=True)[0]

    with undo.UndoContext():
        _reset_skin_weights(data)
        for vId, weight in iteritems(data['weights']):
            weight_attr = '{}.weightList[{}]'.format(data['name'], vId)
            for inf_id, inf_value in iteritems(weight):
                attr = '.weights[{}]'.format(inf_id)
                full_attr = weight_attr + attr
                cmds.setAttr(full_attr, cmds.getAttr(full_attr) + inf_value)
    return data


class SkinData(BaseData):
    def __init__(self):
        super(SkinData, self).__init__()
        self['name'] = str()
        self['geometry'] = str()
        self['weights'] = dict()
        self['influences'] = dict()

    # def reset_skin_weights(self):
    #     for inf in self['influences'].values():
    #         influence = OpenMaya.MSelectionList().add(inf).getDependNode(0)
    #         OpenMaya.MFnTransform(influence).findPlug('lockInfluenceWeights', False).setBool(True)
    #
    #     skin_cluster = OpenMaya.MSelectionList().add(self['name']).getDependNode(0)
    #     skin_cluster = OpenMaya.MFnDependencyNode(skin_cluster)
    #
    #     shape = OpenMaya.MSelectionList().add(self['geometry']).getDagPath(0)
    #     shape = shape.extendToShape().node()
    #
    #     plug = skin_cluster.findPlug('normalizeWeights', False)
    #     value = plug.asDouble()
    #     if value != 0.0:
    #         plug.setDouble(0.0)
    #
    #     cmds.skinPercent(skin_cluster.name(), OpenMaya.MFnDependencyNode(shape).name(), normalize=False, pruneWeights=100)
    #     plug.setDouble(value)
