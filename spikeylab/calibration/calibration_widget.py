import logging

from PyQt4 import QtGui

from spikeylab.stim.types.stimuli_classes import WhiteNoise, FMSweep
from spikeylab.stim.tceditor import TuningCurveEditor
from .calwidget_form import Ui_CalibrationWidget

class CalibrationWidget(QtGui.QWidget):
    """Widget to handle inputs the running and testing of speaker calibration"""
    def __init__(self, parent=None):
        super(CalibrationWidget,self).__init__(parent)
        self.ui = Ui_CalibrationWidget()
        self.ui.setupUi(self)
        self.ui.curveWidget.ui.okBtn.hide()
        self.ui.curveWidget.ui.saveBtn.hide()
        self.ui.curveWidget.ui.durSpnbx.setEnabled(False)
        self.ui.curveWidget.ui.nrepsSpnbx.hide()
        self.ui.curveWidget.ui.label_31.hide()
        self.durationWidgets = [self.ui.curveWidget.ui.durSpnbx]

    def setCurveModel(self, model):
        """sets the stimulus model for the calibration curve test

        :param model: Stimulus model that has a tone curve configured
        :type mode: StimulusModel
        """
        self.stimModel = model
        self.ui.curveWidget.setStimulusModel(model)

    def setDuration(self, dur):
        """Sets the duration for the all of the calibration stimuli

        :param dur: duration of output, in current units for UI
        :type dur: float
        """
        for w in self.durationWidgets:
            w.setValue(dur)

    def addOption(self, stim):
        """Add a stimulus to the list of stims to use for testing calibration

        :param stim: stimulus to add to drop-down list
        :type stim: AbstractStimulusComponent
        """
        # set the editor widgets for noise and sweep
        self.ui.calTypeCmbbx.insertItem(0,stim.name)
        editor = stim.showEditor()
        # should probably make this less coupled
        durInput = editor.durationInputWidget()
        self.durationWidgets.append(durInput)
        durInput.setEnabled(False)
        self.ui.caleditorStack.insertWidget(0, editor)
        self.ui.calTypeCmbbx.setCurrentIndex(0)

    def saveToObject(self):
        """Save the current UI setting to the model"""
        for i in range(self.ui.caleditorStack.count()):
            try:
                self.ui.caleditorStack.widget(i).saveToObject()
            except AttributeError:
                logger = logging.getLogger('main')
                logger.debug('index {} does not have method saveToObject'.format(i))

    def currentIndex(self):
        """Current index of the calibration stim type list

        :returns: int -- index of the combo box
        """
        return self.ui.calTypeCmbbx.currentIndex()

    def currentSelection(self):
        """Name of the current calibration stim type

        :returns: str -- the text of the current item in the combo box
        """
        return self.ui.calTypeCmbbx.currentText()
        
    def isToneCal(self):
        """Whether the currently selected calibraiton stimulus type is the calibration curve

        :returns: boolean -- if the current combo box selection is calibration curve
        """
        return self.ui.calTypeCmbbx.currentIndex() == self.ui.calTypeCmbbx.count() -1

    def saveChecked(self):
        """Whether the UI is set to save the current calibration run

        :returns: boolean -- if the save calibraiton box is checked
        """
        return self.ui.savecalCkbx.isChecked()