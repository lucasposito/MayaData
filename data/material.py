
from maya.api import OpenMaya
from maya import cmds

from . import BaseData


def get(name):
    data = MaterialData()
    data['geometry'] = name

    mfn_mesh = OpenMaya.MSelectionList().add(name).getDagPath(0)
    mfn_mesh = OpenMaya.MFnMesh(mfn_mesh.extendToShape())
    m_objects, face_ids = mfn_mesh.getConnectedShaders(0)

    data['shading_groups'] = [OpenMaya.MFnDependencyNode(obj).name() for obj in m_objects]

    for index, obj in enumerate(m_objects):
        data['face_id_map'][index] = list()
        mfn_material = OpenMaya.MFnDependencyNode(obj)
        plug = mfn_material.findPlug("surfaceShader", False)
        plug_array = plug.connectedTo(True, False)
        for p in plug_array:
            data['materials'].append(OpenMaya.MFnDependencyNode(p.node()).name())

    for face_index, material_index in enumerate(face_ids):
        data['face_id_map'][material_index].append(face_index)

    return data


def consecutive_blocks(index_list):
    """return start indices and subsequences of each run of
    consecutive or equal values
    """
    index_list = sorted(index_list)
    starts = [0]
    for i in range(len(index_list) - 1):
        if abs(index_list[i + 1] - index_list[i]) > 1:
            starts.append(i + 1)
    blocks = []
    starts.append(len(index_list))
    for i in range(len(starts) - 1):
        blocks.append(index_list[starts[i] : starts[i + 1]])
    if not blocks:
        print(starts, blocks)
    return starts, blocks


def set_face_materials(mesh_name, n_faces, sg):

    starts, blocks = consecutive_blocks(sorted(n_faces))
    for block in blocks:
        # combine to get face strings
        f_string = "f[{}:{}]".format(block[0], block[-1])
        ns = cmds.namespaceInfo(currentNamespace=1)
        mesh_ns_name = ns + ":" + mesh_name
        if not cmds.objExists(mesh_ns_name):
            print("mesh", mesh_ns_name, "not found, skipping material load")
            continue
        mesh_face_string = mesh_ns_name + "." + f_string
        cmds.sets(mesh_face_string, e=True, forceElement=sg)


def create_materials(materials):
    # Maya replaces all illegal characters with underscores
    # clean_name = re.sub(r"[^0-9a-zA-Z]", "_", material_name)

    scene_mats = list(set(cmds.ls(materials=1)))
    shader_groups = []

    for mat_name in materials:
        # checks if material is already created if not, creates it.
        if mat_name not in scene_mats:
            mat = cmds.shadingNode("lambert", name=mat_name, asShader=True)
            shading_group = cmds.sets(
                name=mat_name + "SG",
                empty=True,
                renderable=True,
                noSurfaceShader=True,
            )
            cmds.connectAttr(mat + ".outColor", shading_group + ".surfaceShader")
            shader_groups.append(shading_group)
            scene_mats.append(mat)
            continue

        # grabs the already created shading engine if it is already in scene
        shader_groups.append(mat_name + "SG")

    return shader_groups


def load(data=None, name=None):
    if not data:
        data = MaterialData()
        data.load()

    if name:
        data['geometry'] = name
    # shader_groups = create_materials(data['materials'])

    for index, material_name in enumerate(data['materials']):
        set_face_materials(data['geometry'], data['face_id_map'][index], data['shading_groups'][index])


class MaterialData(BaseData):
    def __init__(self):
        super(MaterialData, self).__init__()
        self['geometry'] = str()
        self['materials'] = list()
        self['shading_groups'] = list()
        self['face_id_map'] = dict()
