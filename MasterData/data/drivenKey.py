from maya.api import OpenMaya


def get_driven_by_attr(node, attr='neutral'):

    def get_joint(node):
        if node.hasFn(OpenMaya.MFn.kJoint):
            return OpenMaya.MFnTransform(node).partialPathName()
        elif node.apiType() in [
            OpenMaya.MFn.kAnimCurveUnitlessToUnitless,
            OpenMaya.MFn.kAnimCurveUnitlessToDistance,
            OpenMaya.MFn.kAnimCurveUnitlessToAngular,
            OpenMaya.MFn.kAnimCurveUnitlessToTime,
            OpenMaya.MFn.kBlendWeighted
        ]:
            plug = OpenMaya.MFnDependencyNode(node).findPlug('output', False)
            for each in plug.destinations():
                return get_joint(each.node())

    main_plug = OpenMaya.MFnTransform(node).findPlug(attr, False)
    driven = {get_joint(connected.node()) for connected in main_plug.destinations()}
    driven.discard(None)
    return list(driven)
