from MayaData.data.base import BaseData
from MayaData.lib import decorator

from maya.api import OpenMaya


@decorator.timer()
def get(name):
    dag_obj = OpenMaya.MSelectionList().add(name).getDagPath(0)
    mfn_mesh = OpenMaya.MFnMesh(dag_obj)
    data = GeometryData()
    data['name'] = name
    data['matrix'] = list(dag_obj.inclusiveMatrix())

    data['vertices'] = list()
    points = mfn_mesh.getPoints()
    for point in points:
        data['vertices'].append([point.x, point.y, point.z])

    data['indices'] = list()
    data['faces'] = list()

    for face_id in range(0, mfn_mesh.numPolygons):
        poly_connect = mfn_mesh.getPolygonVertices(face_id)
        data['faces'].append(len(poly_connect))

        data['indices'].extend([i for i in poly_connect])

    return data


@decorator.timer()
def load(data=None):
    if not data:
        data = GeometryData()
        data.load()
    face_points = [OpenMaya.MPoint(vertex) for vertex in data['vertices']]
    mfn_mesh = OpenMaya.MFnMesh()
    mfn_mesh.create(face_points, data['faces'], data['indices'])

    matrix = OpenMaya.MMatrix(data['matrix'])
    matrix = OpenMaya.MTransformationMatrix(matrix)
    OpenMaya.MFnTransform(mfn_mesh.parent(0)).setTransformation(matrix)

    mod = OpenMaya.MDagModifier()
    mod.renameNode(mfn_mesh.parent(0), data['name']).doIt()

    
class GeometryData(BaseData):
    def __init__(self):
        super(GeometryData, self).__init__()
        self['name'] = str()
        self['vertices'] = list()
        self['indices'] = list()
        self['faces'] = list()
        self['matrix'] = list()
