# -*- coding: utf-8 -*-
from abaqusGui import *
from abaqusConstants import ALL
from kernelAccess import mdb, session
import os
import sys
import importlib

if sys.version_info[0] < 3:
    importlib.reload = reload


def _default_model_name():
    try:
        vp_name = session.currentViewportName
        model_name = session.sessionState[vp_name]['modelName']
        if model_name in mdb.models.keys():
            return model_name
    except:
        pass
    try:
        return list(mdb.models.keys())[0]
    except:
        return 'Model-1'


class ConnectorMatchingForm(AFXForm):

    def __init__(self, owner):
        AFXForm.__init__(self, owner)
        self.cmd = AFXGuiCommand(
            mode=self,
            method='connector_matching',
            objectName='ABQ_Matching_kernel',
            registerQuery=False)
        self.modelNameKw = AFXStringKeyword(self.cmd, 'modelName', True, _default_model_name())
        self.setMasterKw = AFXStringKeyword(self.cmd, 'setMaster', True, '')
        self.setSlaveKw = AFXStringKeyword(self.cmd, 'setSlave', True, '')
        self.serialNumberKw = AFXStringKeyword(self.cmd, 'serialNumber', True, '1')

    def getFirstDialog(self):
        import ABQ_MatchingDB
        importlib.reload(ABQ_MatchingDB)
        self.dialog = ABQ_MatchingDB.MatchingDB(self, 'Connector_matching')
        return self.dialog

    def okToCancel(self):
        return False


class SpringMatchingForm(AFXForm):

    def __init__(self, owner):
        AFXForm.__init__(self, owner)
        self.cmd = AFXGuiCommand(
            mode=self,
            method='spring_matching',
            objectName='ABQ_Matching_kernel',
            registerQuery=False)
        self.modelNameKw = AFXStringKeyword(self.cmd, 'modelName', True, _default_model_name())
        self.setMasterKw = AFXStringKeyword(self.cmd, 'setMaster', True, '')
        self.setSlaveKw = AFXStringKeyword(self.cmd, 'setSlave', True, '')
        self.serialNumberKw = AFXStringKeyword(self.cmd, 'serialNumber', True, '1')

    def getFirstDialog(self):
        import ABQ_MatchingDB
        importlib.reload(ABQ_MatchingDB)
        self.dialog = ABQ_MatchingDB.MatchingDB(self, 'Spring_matching')
        return self.dialog

    def okToCancel(self):
        return False


thisPath = os.path.abspath(__file__)
thisDir = os.path.dirname(thisPath).replace('\\', '/')
if thisDir not in sys.path:
    sys.path.append(thisDir)

kernelInitString = (
    'import os, sys\n'
    'if "%s" not in sys.path: sys.path.append("%s")\n'
    'import ABQ_Matching_kernel\n'
) % (thisDir, thisDir)

toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerGuiMenuButton(
    buttonText='ABQ_Matching|Connector_matching',
    object=ConnectorMatchingForm(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString=kernelInitString,
    applicableModules=['Assembly', 'Interaction', 'Step', 'Load', 'Mesh', 'Job'],
    version='1.0',
    author='ABQ_Matching',
    description='Nearest-node matching for connector elements.',
    helpUrl='N/A')

toolset.registerGuiMenuButton(
    buttonText='ABQ_Matching|Spring_matching',
    object=SpringMatchingForm(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString=kernelInitString,
    applicableModules=['Assembly', 'Interaction', 'Step', 'Load', 'Mesh', 'Job'],
    version='1.0',
    author='ABQ_Matching',
    description='Nearest-node matching for two-point springs.',
    helpUrl='N/A')


class ABQMatchingToolbar(AFXToolsetGui):
    ID_CONNECTOR, ID_SPRING = range(AFXToolsetGui.ID_LAST, AFXToolsetGui.ID_LAST + 2)

    def __init__(self):
        AFXToolsetGui.__init__(self, toolsetName='ABQ_Matching')
        FXMAPFUNC(self, SEL_COMMAND, self.ID_CONNECTOR, ABQMatchingToolbar.onCmdConnector)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_SPRING, ABQMatchingToolbar.onCmdSpring)

        group = AFXToolbarGroup(self)
        connector_icon = afxCreatePNGIcon(os.path.join(thisDir, 'connector.png'))
        spring_icon = afxCreatePNGIcon(os.path.join(thisDir, 'spring.png'))
        AFXToolButton(group, '\tConnector_matching', connector_icon, self, self.ID_CONNECTOR)
        AFXToolButton(group, '\tSpring_matching', spring_icon, self, self.ID_SPRING)
        self.form = None

    def _activate_form(self, form):
        try:
            self.form.cancel(None, 0)
        except:
            pass
        sendCommand(kernelInitString, False)
        self.form = form
        self.form.activate()

    def onCmdConnector(self, sender, sel, ptr):
        self._activate_form(ConnectorMatchingForm(self))
        return

    def onCmdSpring(self, sender, sel, ptr):
        self._activate_form(SpringMatchingForm(self))
        return


mw = getAFXApp().getAFXMainWindow()
mw.registerToolset(ABQMatchingToolbar(), GUI_IN_MENUBAR | GUI_IN_TOOLBAR)
