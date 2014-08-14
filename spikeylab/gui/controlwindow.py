import os
import json
import logging

import yaml
from PyQt4 import QtCore, QtGui

import spikeylab.tools.systools as systools
from spikeylab.tools.util import convert2native
from spikeylab.gui.stim.abstract_editor import AbstractEditorWidget
from spikeylab.stim.abstract_stimulus import AbstractStimulusComponent
from spikeylab.gui.stim.stimulusview import StimulusView
from maincontrol_form import Ui_ControlWindow
from spikeylab.tools.systools import get_src_directory

with open(os.path.join(get_src_directory(),'settings.conf'), 'r') as yf:
    config = yaml.load(yf)
USE_ATTEN = config['use_attenuator']

class ControlWindow(QtGui.QMainWindow):
    """ Base class just to handle loading, saving, and validity of user inputs"""
    def __init__(self, inputsFilename, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.ui = Ui_ControlWindow()
        self.ui.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.calibrationDisplay = self.ui.plotDock.displays['calibration']
        self.extendedDisplay = self.ui.plotDock.displays['calexp']
        self.scrollplot = self.ui.plotDock.displays['chart']
        self.display = self.ui.plotDock.displays['standard']
        self.ui.plotDock.switchDisplay('standard')
        # make a list of which widgets should be updated when scales are changed
        self.timeInputs = [self.ui.windowszSpnbx, self.ui.binszSpnbx]
        self.frequencyInputs = [self.ui.aisrSpnbx, self.ui.aosrSpnbx]
        self.timeLabels = [self.ui.tunit_lbl, self.ui.tunit_lbl_2]
        self.frequencyLabels = [self.ui.funit_lbl, self.ui.funit_lbl_2]

        self.ui.protocolView.installEventFilter(self.ui.stimulusChoices.trash())
        self.loadInputs(inputsFilename)
        self.inputsFilename = inputsFilename

        for calstim in self.acqmodel.bs_calibrator.get_stims()[::-1]: #tsk
            self.ui.calibrationWidget.addOption(calstim)

        # keep a reference to a dummy stimulus view, to be able to update
        # default attributes in stimulus builder from explore components
        self.dummyview = StimulusView()
        for stim in self.exploreStimuli:
            editor = stim.showEditor()
            editor.attributesSaved.connect(self.dummyview.updateDefaults)
            # intial from saved values
            self.dummyview.updateDefaults(stim.__class__.__name__, stim.stateDict())
            self.ui.parameterStack.addWidget(editor)
            self.ui.exploreStimTypeCmbbx.addItem(stim.name)

        try:
            settings = QtCore.QSettings("audiolab")
            if settings is not None:
                self.restoreGeometry(settings.value("geometry").toByteArray())
                self.restoreState(settings.value("windowState").toByteArray())
            else:
                logger = logging.getLogger('main')
                logger.warning('Unable to restore QSettings for audiolab')
            # self.ui.psth.restoreGeometry(settings.value("psth_dock/geometry"))

            self.ui.protocolProgressBar.setStyleSheet("QProgressBar { text-align: center; }")
            self.ui.protocolProgressBar.setMinimum(0)
        except Exception as e:
            logger = logging.getLogger('main')
            logger.exception("Error Initializing main GUI")

    def verifyInputs(self, mode):
        if mode == 'chart':
            if self.ui.aisrSpnbx.value()*self.fscale > 100000:
                QtGui.QMessageBox.warning(self, "Invalid Input", "Recording samplerate cannot exceed 100kHz for chart acquisition")
                return False
        elif mode is not None:
            # if (1./self.ui.reprateSpnbx.value()) < self.ui.windowszSpnbx.value()*self.tscale + 0.05:
            #     QtGui.QMessageBox.warning(self, "Invalid Input", "A minimum of 50ms time between repetitions required. Current interval {}, required {}".format((1./self.ui.reprateSpnbx.value()), self.ui.windowszSpnbx.value()*self.tscale + 0.05))
            #     return False
            if self.ui.tabGroup.currentWidget().objectName() == 'tabExplore':
                # each widget should be in charge of putting its own stimulus together
                stimIndex = self.ui.exploreStimTypeCmbbx.currentIndex()
                stimWidget = self.ui.parameterStack.widget(stimIndex)
                stimWidget.saveToObject()
                selectedStim = self.exploreStimuli[stimIndex]
                failmsg = selectedStim.verify(samplerate=self.ui.aosrSpnbx.value()*self.fscale)
                if failmsg:
                    QtGui.QMessageBox.warning(self, "Invalid Input", failmsg)
                    return False
                if selectedStim.duration() > self.ui.windowszSpnbx.value()*self.tscale:
                    QtGui.QMessageBox.warning(self, "Invalid Input",
                            "Window size must equal or exceed stimulus length")
                    return False
                # if selectedStim.intensity() > self.calvals['caldb']:
                #     QtGui.QMessageBox.warning(self, "Invalid Input",
                #             "Intensity must be below calibrated maximum {}dB SPL".format(self.calvals['caldb']))
                #     return False
            elif self.ui.tabGroup.currentWidget().objectName() == 'tabProtocol':
                protocol_model = self.acqmodel.protocol_model()
                failure = protocol_model.verify(float(self.ui.windowszSpnbx.value())*self.tscale)
                if failure:
                    QtGui.QMessageBox.warning(self, "Invalid Input", failure)
                    return False
            elif self.ui.tabGroup.currentWidget().objectName() == 'tabCalibrate':
                if self.ui.calibrationWidget.ui.savecalCkbx.isChecked() or not self.ui.calibrationWidget.currentSelection() == 'Tone Curve':
                    calibration_stimulus = self.acqmodel.calibration_stimulus('noise')
                    self.ui.calibrationWidget.saveToObject()
                else:
                    calibration_stimulus = self.acqmodel.calibration_stimulus('tone')

                failmsg = calibration_stimulus.verify(float(self.ui.windowszSpnbx.value())*self.tscale)
                if failmsg:
                    QtGui.QMessageBox.warning(self, "Invalid Input", failmsg)
                    return False
                # also check that the recording samplerate is high enough in this case
                failmsg = calibration_stimulus.verifyExpanded(samplerate=self.ui.aisrSpnbx.value()*self.fscale)
                if failmsg:
                    failmsg = failmsg.replace('Generation', 'Recording')
                    QtGui.QMessageBox.warning(self, "Invalid Input", failmsg)
                    return False
            if USE_ATTEN and not self.acqmodel.attenuator_connection():
                failmsg = "Error Connection to attenuator, make sure it it turned on and connected, and try again"
                QtGui.QMessageBox.warning(self, "Connection Error", failmsg)
                return False
        return True

    def updateUnitLabels(self, tscale, fscale, setup=False):

        AbstractEditorWidget.scales = [tscale, fscale]

        if tscale != self.tscale:
            self.tscale = tscale

            AbstractStimulusComponent.update_tscale(self.tscale)
            AbstractEditorWidget.purgeDeletedWidgets()
            time_inputs = self.timeInputs + AbstractEditorWidget.tunit_fields
            time_labels = self.timeLabels + AbstractEditorWidget.tunit_labels

            self.display.setTscale(self.tscale)
            
            if self.tscale == 0.001:
                for field in time_inputs:
                    field.setMaximum(3000)
                    if not setup:
                        field.setValue(field.value()/0.001)
                    field.setDecimals(0)
                    field.setMinimum(1)
                for lbl in time_labels:
                    lbl.setText(u'ms')
            elif self.tscale == 1:
                for field in time_inputs:
                    field.setDecimals(3)
                    field.setMinimum(0.001)
                    if not setup:
                        field.setValue(field.value()*0.001)
                    field.setMaximum(20)
                for lbl in time_labels:
                    lbl.setText(u's')
            else:
                print self.tscale
                raise Exception(u"Invalid time scale")

        if fscale != self.fscale:
            self.fscale = fscale

            AbstractStimulusComponent.update_fscale(self.fscale)
            frequency_inputs = self.frequencyInputs + AbstractEditorWidget.funit_fields
            frequency_labels = self.frequencyLabels + AbstractEditorWidget.funit_labels

            self.display.setFscale(self.fscale)
            self.calibrationDisplay.setFscale(self.fscale)

            if self.fscale == 1000:
                for field in frequency_inputs:
                    field.setDecimals(3)
                    field.setMinimum(0.001)
                    if not setup:
                        field.setValue(field.value()/1000)
                    field.setMaximum(500)
                for lbl in frequency_labels:
                    lbl.setText(u'kHz')

            elif self.fscale == 1:
                for field in frequency_inputs:
                    field.setMaximum(500000)
                    if not setup:
                        field.setValue(field.value()*1000)
                    field.setDecimals(0)
                    field.setMinimum(1)
                for lbl in frequency_labels:
                    lbl.setText(u'Hz')
            else:
                print self.fscale
                raise Exception(u"Invalid frequency scale")
            
    def saveInputs(self, fname):
        # save current inputs to file for loading next time
        if not fname:
            return
            
        appdir = systools.get_appdir()
        if not os.path.isdir(appdir):
            os.makedirs(appdir)
        fname = os.path.join(appdir, fname)

        savedict = {}
        savedict['threshold'] = self.ui.threshSpnbx.value()
        savedict['binsz'] = self.ui.binszSpnbx.value()
        savedict['aisr'] = self.ui.aisrSpnbx.value()
        savedict['tscale'] = self.tscale
        savedict['fscale'] = self.fscale
        savedict['saveformat'] = self.saveformat
        savedict['ex_nreps'] = self.ui.exNrepsSpnbx.value()
        savedict['reprate'] = self.ui.reprateSpnbx.value()
        savedict['windowsz'] = self.ui.windowszSpnbx.value()
        savedict['raster_bounds'] = self.display.spiketracePlot.getRasterBounds()
        savedict['specargs'] = self.specArgs
        savedict['viewSettings'] = self.viewSettings
        savedict['calvals'] = self.calvals
        savedict['calparams'] = self.acqmodel.calibration_template()
        savedict['calreps'] = self.ui.calibrationWidget.ui.nrepsSpnbx.value()

        # parameter settings
        for stim in self.exploreStimuli:
            editor = self.ui.parameterStack.widgetForName(stim.name)
            editor.saveToObject()
            savedict[stim.name] = stim.stateDict()

        savedict = convert2native(savedict)
        with open(fname, 'w') as jf:
            json.dump(savedict, jf)

    def loadInputs(self, fname):
        inputsfname = os.path.join(systools.get_appdir(), fname)
        try:
            with open(inputsfname, 'r') as jf:
                inputsdict = json.load(jf)
        except:
            logger = logging.getLogger('main')
            logger.exception("Unable to load app data")
            inputsdict = {}
        

        self.ui.threshSpnbx.setValue(inputsdict.get('threshold', 0.5))
        self.stashedAisr = inputsdict.get('aisr', 100)
        self.ui.aisrSpnbx.setValue(self.stashedAisr)
        self.ui.windowszSpnbx.setValue(inputsdict.get('windowsz', 100))
        self.ui.binszSpnbx.setValue(inputsdict.get('binsz', 5))        
        self.saveformat = inputsdict.get('saveformat', 'hdf5')
        self.ui.exNrepsSpnbx.setValue(inputsdict.get('ex_nreps', 5))
        self.ui.reprateSpnbx.setValue(inputsdict.get('reprate', 1))
        self.display.spiketracePlot.setRasterBounds(inputsdict.get('raster_bounds', (0.5,1)))
        self.specArgs = inputsdict.get('specargs',{u'nfft':512, u'window':u'hanning', u'overlap':90, 'colormap':{'lut':None, 'state':None, 'levels':None}})
        self.display.setSpecArgs(**self.specArgs)  
        self.viewSettings = inputsdict.get('viewSettings', {'fontsz': 10, 'display_attributes':{}})
        self.ui.stimDetails.setDisplayAttributes(self.viewSettings['display_attributes'])
        self.ui.reviewer.setDisplayAttributes(self.viewSettings['display_attributes'])
        font = QtGui.QFont()
        font.setPointSize(self.viewSettings['fontsz'])
        QtGui.QApplication.setFont(font)
        self.ui.calibrationWidget.ui.nrepsSpnbx.setValue(inputsdict.get('calreps', 5))
        self.calvals = inputsdict.get('calvals', {'calf':20000, 'caldb':100, 
                                      'calv':0.1, 'use_calfile':False, 
                                      'frange':(5000, 1e5), 'calname': ''})
        self.calvals['use_calfile'] = False
        self.calvals['calname'] = ''
        self.ui.refDbSpnbx.setValue(self.calvals['caldb'])
        tscale = inputsdict.get('tscale', 0.001)
        fscale = inputsdict.get('fscale', 1000)

        self.tscale = 0
        self.fscale = 0
        self.updateUnitLabels(tscale, fscale, setup=True)

        cal_template = inputsdict.get('calparams', None)
        if cal_template is not None:
            try:
                self.acqmodel.load_calibration_template(cal_template)
            except:
                logger = logging.getLogger('main')
                logger.exception("Unable to load previous calibration settings")
                
            for stim in self.exploreStimuli:
                try:
                    stim.loadState(inputsdict[stim.name])

                except KeyError:
                    logger = logging.getLogger('main')
                    logger.exception('Unable to load saved inputs for {}'.format(stim.__class__))
        else:
            logger = logging.getLogger('main')
            logger.debug('No saved stimului inputs')
 
        self.ui.aosrSpnbx.setValue(self.acqmodel.explore_genrate()/self.fscale)

    def closeEvent(self, event):
        self.acqmodel.stop_listening()
        self.saveInputs(self.inputsFilename)

        # save GUI size
        settings = QtCore.QSettings("audiolab")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        logger = logging.getLogger('main')
        logger.info('All user settings saved')

