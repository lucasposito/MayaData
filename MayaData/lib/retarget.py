from maya import cmds, mel, OpenMayaUI

from pathlib import Path
from PySide2 import QtWidgets
from shiboken2 import wrapInstance
import pyautogui


maya_window = OpenMayaUI.MQtUtil.mainWindow()
maya_window = wrapInstance(int(maya_window), QtWidgets.QWidget)

file_filter = 'Fbx (*.fbx)'
dialog = QtWidgets.QDialog(maya_window)


def run():
    selection = cmds.ls(sl=True)

    hips = 'mocap_ref:spine_C0_0_jnt'

    if len(selection) != 2:
        print('Please select first the source then secondly the target')
        return

    source = cmds.listRelatives(selection[0], ad=True, f=True) + [selection[0]]
    neutral_pose = {jnt: cmds.xform(jnt, m=True, q=True) for jnt in source}

    target = cmds.listRelatives(selection[1], ad=True, f=True) + [selection[1]]
    target_pose = {jnt: cmds.xform(jnt, m=True, q=True) for jnt in target}

    target_copy = {jnt: jnt.split(':')[-1] for jnt in target}

    # Import animations
    file_paths, selected_filter = QtWidgets.QFileDialog.getOpenFileNames(dialog, 'Select Anim', '', file_filter)

    parent_folder = None

    for path in file_paths:
        # cmds.parentConstraint(selection[0], target_copy[selection[1]], mo=True)
        cmds.pointConstraint(hips, target_copy[selection[1]], mo=True, skip='y')
        cmds.orientConstraint(hips, target_copy[selection[1]], mo=True, skip=['x', 'z'])

        [cmds.parentConstraint(jnt, target_copy[jnt], mo=True) for jnt in target if jnt != selection[1]]

        file_path = Path(path)
        cmds.file(str(file_path), i=True, type="FBX", iv=True, ra=True, mnc=False, options="v=0", pr=True)

        # Get full anim length
        cmds.playbackOptions(maxTime=max(cmds.keyframe(source[-1], q=True)))

        # Bake animations into target
        start = int(cmds.playbackOptions(q=True, minTime=True))
        end = int(cmds.playbackOptions(q=True, maxTime=True))

        cmds.bakeResults(list(target_copy.values()), sm=True, t=(start, end), pok=True, ral=False, rba=False, bol=False, mr=True)
        cmds.delete(list(target_copy.values()), sc=True)

        if not parent_folder:
            parent_folder = file_path.parent / 'retargeted'
            parent_folder.mkdir(parents=True, exist_ok=True)

        cmds.delete(cmds.listRelatives(target_copy[selection[1]], ad=True, typ=['parentConstraint', 'pointConstraint', 'orientConstraint']))

        # Export file
        cmds.select(list(target_copy.values()), r=True)
        target_path = parent_folder / file_path.stem
        cmds.file(str(target_path), force=True, options="v=0;", type="FBX export", es=True)
        if 'FbxWarningWindow' in cmds.lsUI(wnd=True):
            cmds.deleteUI('FbxWarningWindow')

        cmds.refresh()

        # Clear anim from source and set it to neutral pose
        cmds.cutKey(source + list(target_copy.values()), clear=True)
        [cmds.xform(jnt, m=neutral_pose[jnt]) for jnt in neutral_pose]
        [cmds.xform(jnt, m=target_pose[jnt]) for jnt in target_pose]
        [cmds.xform(target_copy[jnt], m=target_pose[jnt]) for jnt in target_pose]

        # set target human ik
        # mel.eval('hikSetCurrentSource("motion");')
        # mel.eval('hikUpdateSourceList();')

        # get the position by pyautogui.position()
        x1, y1 = 1797, 170
        x2, y2 = 1834, 193

        pyautogui.moveTo(x1, y1)
        pyautogui.click()

        pyautogui.moveTo(x2, y2)
        pyautogui.click()
        mel.eval('hikUpdateCurrentSourceFromUI()')
