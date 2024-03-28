from maya.api import OpenMaya
from maya import cmds

from MayaData.data.base import BaseData


def get(name):
    data = NormalData()
    data['geometry'] = name

    mesh = OpenMaya.MSelectionList().add(name).getDagPath(0)

    vertex_iter = OpenMaya.MItMeshVertex(mesh)
    while not vertex_iter.isDone():
        vertex_id = vertex_iter.index()
        normals = vertex_iter.getNormals()
        if not normals:
            vertex_iter.next()
            continue
        if vertex_id not in data['normals']:
            data['normals'][vertex_id] = list()

        [data['normals'][vertex_id].append(tuple(normal)) for normal in normals]
        data['faces'].append(list(vertex_iter.getConnectedFaces()))

        vertex_iter.next()

    return data


def load(data=None, name=None):
    if not data:
        data = NormalData()
        data.load()

    if name:
        data['geometry'] = name

    mfn_mesh = OpenMaya.MSelectionList().add(data['geometry']).getDagPath(0)
    mfn_mesh = OpenMaya.MFnMesh(mfn_mesh)

    for (vtx_id, normals), faces in zip(data['normals'].items(), data['faces']):
        mfn_mesh.setFaceVertexNormals(OpenMaya.MVectorArray(normals), OpenMaya.MIntArray(faces),
                                      OpenMaya.MIntArray([vtx_id] * len(faces)))
        # for normal, face in zip(OpenMaya.MVectorArray(normals), faces):
        #     mfn_mesh.setFaceVertexNormal(normal, face, vtx_id)
    cmds.polyNormal(data['geometry'], nm=2, unm=0, ch=0)


class NormalData(BaseData):
    def __init__(self):
        super(NormalData, self).__init__()
        self['geometry'] = str()
        self['normals'] = dict()
        self['faces'] = list()
