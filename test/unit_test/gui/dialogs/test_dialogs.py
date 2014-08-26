import os

from spikeylab.gui.dialogs import SavingDialog, ScaleDialog, SpecDialog, \
                            CalibrationDialog, CellCommentDialog, ViewSettingsDialog
from spikeylab.data.dataobjects import AcquisitionData

import test.sample as sample

from nose.tools import assert_equal

from PyQt4.QtTest import QTest 
from PyQt4.QtGui import QApplication, QLineEdit
from PyQt4.QtCore import Qt

class TestCalibrationDialog():
    def setUp(self):
        self.fscale = 1000
        self.defaults = {'calf':20000, 'caldb':100,  'calv':0.1, 'calname':'calibration_1', 
                         'use_calfile':False, 'frange':(5000, 1e5)}
        cal_data_file = AcquisitionData(sample.calibration_filename(), filemode='r')
        self.dlg = CalibrationDialog(fscale=self.fscale, defaultVals=self.defaults,
                                     datafile=cal_data_file)
        self.dlg.show()

    def tearDown(self):
        self.dlg.close()
        self.dlg.deleteLater()

    def test_no_calfile_accept(self):
        assert self.dlg.ui.noneRadio.isChecked() == True
        QTest.mouseClick(self.dlg.ui.buttonBox.button(self.dlg.ui.buttonBox.Ok), Qt.LeftButton)
        return_vals = self.dlg.values()
        print self.defaults, return_vals

        assert return_vals['use_calfile'] == False

    def test_calfile_accept(self):
        self.dlg.ui.calfileRadio.setChecked(True)
        self.dlg.ui.calChoiceCmbbx.setCurrentIndex(0)
        assert self.dlg.ui.noneRadio.isChecked() == False
        QTest.mouseClick(self.dlg.ui.buttonBox.button(self.dlg.ui.buttonBox.Ok), Qt.LeftButton)
        
        return_vals = self.dlg.values()
        assert return_vals['calname'] == 'calibration_1'
        assert return_vals['use_calfile'] == True

    def test_frequency_range(self):
        self.dlg.ui.calfileRadio.setChecked(True)
        self.dlg.ui.calChoiceCmbbx.setCurrentIndex(0)

        QTest.mouseClick(self.dlg.ui.rangeBtn, Qt.LeftButton)

        # extract the calibration ourselves
        cal_data_file = AcquisitionData(sample.calibration_filename(), filemode='r')
        calname = cal_data_file.calibration_list()[0]
        x, freqs = cal_data_file.get_calibration(calname, reffreq=15000)

        assert self.dlg.ui.frangeLowSpnbx.value()*self.fscale == max(freqs[0], self.dlg.ui.frangeLowSpnbx.minimum()*self.fscale)
        assert self.dlg.ui.frangeHighSpnbx.value()*self.fscale == min(freqs[-1], self.dlg.ui.frangeHighSpnbx.maximum()*self.fscale)

    def test_plot_curve(self):
        self.dlg.ui.calfileRadio.setChecked(True)
        self.dlg.ui.calChoiceCmbbx.setCurrentIndex(0)

        QTest.mouseClick(self.dlg.ui.plotBtn, Qt.LeftButton)

        assert self.dlg.pw is not None

        self.dlg.pw.close()
        self.dlg.pw.deleteLater()

class TestCommentDialog():
    def test_enter_text(self):
        dlg = CellCommentDialog()
        dlg.show()
        msg = "No one expects the Spanish Inquisition!"
        dlg.ui.commentTxtedt.appendPlainText(msg)
        assert dlg.comment() == msg
        dlg.close()
        dlg.deleteLater()

class TestSavingDialog():
    def test_load_previous_file_no_default(self):
        dlg = SavingDialog(directory=sample.sampledir())
        self.hack_filename(dlg, sample.datafile())
        fname, mode = dlg.getfile()
        assert os.path.normpath(fname) == sample.datafile()
        assert mode == 'a'
        dlg.close()
        dlg.deleteLater()

    def test_load_previous_file_as_default(self):
        dlg = SavingDialog(sample.datafile())
        fname, mode = dlg.getfile()
        assert os.path.normpath(fname) == sample.datafile()
        assert mode == 'a'
        dlg.close()
        dlg.deleteLater()

    def test_create_new_file_with_default(self):
        dlg = SavingDialog(sample.datafile())
        dlg.show()
        QTest.qWait(100)
        self.hack_filename(dlg, 'newfile')
        fname, mode = dlg.getfile() 
        print os.path.normpath(fname), os.path.join(sample.sampledir(), 'newfile.hdf5')
        assert os.path.normpath(fname) == os.path.join(sample.sampledir(), 'newfile.hdf5')
        assert mode == 'w-'
        dlg.close()
        dlg.deleteLater()

    def test_create_new_file_no_default(self):
        dlg = SavingDialog(directory=sample.sampledir())
        self.hack_filename(dlg, 'newfile')
        fname, mode = dlg.getfile()
        assert os.path.normpath(fname) == os.path.join(sample.sampledir(), 'newfile.hdf5')
        assert mode == 'w-'
        dlg.close()
        dlg.deleteLater()

    def hack_filename(self, dlg, fname):
        # copy-pasted from SavingDialog code...
        layout = dlg.layout()
        for i in range(layout.count()):
            try:
                w = layout.itemAt(i).widget()
                if isinstance(w, QLineEdit):
                    w.setText(fname)
            except:
                # wasn't a widget
                pass

class TestScaleDialog():
    def test_accept_defaults(self):
        defaults = {'fscale':1000, 'tscale':0.001}
        dlg = ScaleDialog(defaultVals=defaults)
        retvals = dlg.values()
        assert retvals[0] == defaults['fscale']
        assert retvals[1] == defaults['tscale']
        dlg.close()
        dlg.deleteLater()

    def test_change_scale(self):
        defaults = {'fscale':1000, 'tscale':0.001}
        dlg = ScaleDialog(defaultVals=defaults)
        dlg.ui.secBtn.setChecked(True)
        dlg.ui.hzBtn.setChecked(True)
        retvals = dlg.values()
        assert retvals[0] == 1
        assert retvals[1] == 1
        dlg.close()
        dlg.deleteLater()

class TestSpecDialog():
    def test_accept_defaults(self):
        defaults = {'nfft': 512, 'window':'blackman', 'overlap':90}
        dlg = SpecDialog(defaultVals=defaults)
        retvals = dlg.values()
        assert_equal(retvals, defaults)
        dlg.close()
        dlg.deleteLater()

    def test_change_vals(self):
        defaults = {'nfft': 512, 'window':'blackman', 'overlap':90}
        dlg = SpecDialog(defaultVals=defaults)
        idx = dlg.ui.windowCmbx.currentIndex()
        if idx < dlg.ui.windowCmbx.count() -1:
            dlg.ui.windowCmbx.setCurrentIndex(idx+1)
        else:
            dlg.ui.windowCmbx.setCurrentIndex(idx-1)
        dlg.ui.nfftSpnbx.setValue(256)
        dlg.ui.overlapSpnbx.setValue(50)
        retvals = dlg.values()
        assert retvals['nfft'] == 256
        assert retvals['overlap'] == 50
        assert retvals['window'] != 'blackman'
        assert retvals['window'] != ''
        assert retvals['window'] is not None
        dlg.close()
        dlg.deleteLater()

class TestViewDialog():
    def test_accept_defaults_empty_attributes(self):
        defaults = {'fontsz': 15, 'display_attributes':{}}
        dlg = ViewSettingsDialog(defaultVals=defaults)
        retvals = dlg.values()
        assert retvals['fontsz'] == defaults['fontsz']
        for attlists in retvals['display_attributes'].values():
            assert len(attlists) == 0
        dlg.close()
        dlg.deleteLater()

    def test_accept_defaults_with_attributes(self):
        default_attrs = {'Pure Tone': ['frequency'], 'silence': ['duration'],
                    'vocalization':['duration', 'risefall']}
        defaults = {'fontsz': 15, 'display_attributes':default_attrs}
        dlg = ViewSettingsDialog(defaultVals=defaults)
        retvals = dlg.values()
        assert retvals['fontsz'] == defaults['fontsz']
        for comp, attlist in retvals['display_attributes'].items():
            if comp in default_attrs:
                assert_equal(default_attrs[comp], attlist)
            else:
                assert len(attlist) == 0

        dlg.close()
        dlg.deleteLater()
