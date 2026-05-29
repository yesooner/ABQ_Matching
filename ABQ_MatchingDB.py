# -*- coding: utf-8 -*-
from abaqusGui import *
from abaqusConstants import *


class MatchingDB(AFXDataDialog):

    def __init__(self, form, title):
        AFXDataDialog.__init__(
            self,
            form,
            title,
            self.OK | self.CANCEL,
            DIALOG_ACTIONS_SEPARATOR)

        okBtn = self.getActionButton(self.ID_CLICKED_OK)
        okBtn.setText('OK')

        cancelBtn = self.getActionButton(self.ID_CLICKED_CANCEL)
        cancelBtn.setText('Cancel')

        aligner = AFXVerticalAligner(
            p=self,
            opts=LAYOUT_FILL_X,
            x=0,
            y=0,
            w=0,
            h=0,
            pl=DEFAULT_SPACING,
            pr=DEFAULT_SPACING,
            pt=DEFAULT_SPACING,
            pb=DEFAULT_SPACING)

        AFXTextField(
            p=aligner,
            ncols=18,
            labelText='Model-Name:',
            tgt=form.modelNameKw,
            sel=0,
            opts=AFXTEXTFIELD_STRING)
        AFXTextField(
            p=aligner,
            ncols=18,
            labelText='Set-Master:',
            tgt=form.setMasterKw,
            sel=0,
            opts=AFXTEXTFIELD_STRING)
        AFXTextField(
            p=aligner,
            ncols=18,
            labelText='Set-Slave:',
            tgt=form.setSlaveKw,
            sel=0,
            opts=AFXTEXTFIELD_STRING)
        AFXTextField(
            p=aligner,
            ncols=18,
            labelText='Name suffix:',
            tgt=form.serialNumberKw,
            sel=0,
            opts=AFXTEXTFIELD_STRING)
