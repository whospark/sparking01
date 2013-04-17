import sys, os

from PyQt4 import QtCore, QtGui
from PyDAQmx import *
import numpy as np
from scipy import signal
import scipy.io.wavfile as wv

from fg_form import Ui_fgform
from daq_tasks import AOTask,AITask

class FGenerator(QtGui.QMainWindow):
    def __init__(self, parent=None):
        #auto generated code intialization
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_fgform()
        self.ui.setupUi(self)

        #manual costumization
        cnames = get_ao_chans(b"Dev1")
        self.ui.aochan_box.addItems(cnames)
        cnames = get_ai_chans(b"Dev1")
        self.ui.aichan_box.addItems(cnames)
        self.ui.start_button.clicked.connect(self.start_gen)
        self.ui.stop_button.clicked.connect(self.stop_gen)
        self.ui.sr_edit.textChanged.connect(self.update_time)
        self.ui.npts_edit.textChanged.connect(self.update_time)
        self.ui.aisr_edit.textChanged.connect(self.update_time)
        self.ui.ainpts_edit.textChanged.connect(self.update_time)        
        self.update_time()

    def update_time(self):
        #update the time display if one of the parameters changes
        sr = int(self.ui.sr_edit.text())
        npts = int(self.ui.npts_edit.text())
        airate = int(self.ui.aisr_edit.text())
        readnpts = int(self.ui.ainpts_edit.text())

        aot = npts/sr
        ait = readnpts/airate

        self.ui.aotime.setText("AO time: " + str(aot))
        self.ui.aitime.setText("AI time: " + str(ait))

    def start_gen(self):
        sr = int(self.ui.sr_edit.text())
        npts = int(self.ui.npts_edit.text())
        amp = int(self.ui.amp_edit.text())
        freq = int(self.ui.freq_edit.text())
        aochan = self.ui.aochan_box.currentText().encode()
        aichan = self.ui.aichan_box.currentText().encode()
        self.readnpts = int(self.ui.ainpts_edit.text())
        airate = int(self.ui.aisr_edit.text())
        self.reset_plot = self.ui.reset_box.isChecked()

        self.indata = []
        self.npts = npts
        self.ncollected = 0
        self.curr_plot_point = 0

        #plot data we intend to generate
        self.ui.inplot.axes.cla()
        self.aiplot, = self.ui.inplot.axes.plot([],[])
        
        self.ui.outplot.axes.set_xlim(0,npts)
        self.ui.outplot.axes.set_ylim(-amp,amp)
        self.ui.inplot.axes.set_ylim(-amp,amp)
        if self.reset_plot:
            self.ui.inplot.axes.set_xlim(0,self.readnpts)   
        else:
            self.ui.inplot.axes.set_xlim(0,npts)   
        self.ui.inplot.axes.hold(True)

        #in/out data
        if self.ui.sin_radio.isChecked():
            outdata = amp * np.sin(freq * np.linspace(0, 2*np.pi, npts))
        elif self.ui.square_radio.isChecked():
            outdata = amp * np.sign(np.sin(freq * np.linspace(0, 2*np.pi, npts)))
        elif self.ui.saw_radio.isChecked():
            outdata = amp * signal.sawtooth(freq * np.linspace(0, 2*np.pi, npts))
        else:
            #import audio files to output
            stimFolder = "C:\\Users\\amy.boyle\\sampledata\\M1_FD024"
            stimFileList = os.listdir(stimFolder)
            print('Found '+str(len(stimFileList))+' stim files')
            #ok, so how to cycle through files...
            sr,outdata = wv.read(stimFolder+"\\"+stimFileList[0])
            outdata = outdata.astype(float)
            mx = np.amax(outdata)
            outdata = outdata/mx
            self.ui.outplot.axes.set_xlim(0,len(outdata))

        self.ui.outplot.axes.plot(range(len(outdata)),outdata)

        self.ui.outplot.draw()
        self.ui.inplot.draw()
        QtGui.QApplication.processEvents()

        try:
            self.ai = AITask(aichan,airate,npts)

            # two ways to sync -- give the AOTask the ai sample clock for its source,
            # or have it trigger off the ai

            #first way
            self.ao = AOTask(aochan,sr,npts,b"ai/SampleClock")

            #second way
            #self.ao = AOTask(aochan,sr,npts)
            #self.ao.CfgDigEdgeStartTrig(b"ai/StartTrigger", DAQmx_Val_Rising)
            print("amax of outdata: " + str(np.amax(outdata)))
            
            self.ao.write(outdata)
            #register callback to plot after npts samples acquired into buffer
            self.ai.register_callback(self.every_n_callback,self.readnpts)
            self.ao.start()
            self.ai.StartTask()
        except:
            print('ERROR! TERMINATE!')
            self.ai.stop()
            self.ao.stop()
            raise

    def every_n_callback(self,task):
        #print("booya you watery tart")
        r = c_int32()
        inbuffer = np.zeros(self.readnpts)
        task.ReadAnalogF64(self.readnpts,10.0,DAQmx_Val_GroupByScanNumber,inbuffer,
                           self.readnpts,byref(r),None)
        #print("****************************dddd")
        self.ncollected += r.value
        self.curr_plot_point += r.value
        #print(self.ncollected)
        #store data in a numpy array where columns are trace sweeps
        #print(inbuffer.shape)
        self.indata.append(inbuffer.tolist())
        if self.reset_plot:
            self.aiplot.set_data(range(len(inbuffer)),inbuffer)
        else:
            xl = self.ui.inplot.axes.axis() #axis limits
            #print("axis "+str(xl[1]) + ", ncollected " + str(self.ncollected))
            if self.ncollected > xl[1]:
                #print('reset')
                self.ui.inplot.axes.set_xlim(self.ncollected,self.ncollected+self.npts)
            self.ui.inplot.axes.plot(range(self.ncollected-self.readnpts,self.ncollected),inbuffer)
        self.ui.inplot.draw()
        QtGui.QApplication.processEvents()

    def stop_gen(self):
        self.ao.stop()
        self.ai.stop()
        self.ui.inplot.axes.hold(False)


def get_ao_chans(dev):
    buf = create_string_buffer(256)
    buflen = c_uint32(sizeof(buf))
    DAQmxGetDevAOPhysicalChans(dev, buf, buflen)
    pybuf = buf.value
    chans = pybuf.decode('utf-8').split(",")
    #print(chans)
    return chans  

def get_ai_chans(dev):
    buf = create_string_buffer(512)
    buflen = c_uint32(sizeof(buf))
    DAQmxGetDevAIPhysicalChans(dev, buf, buflen)
    pybuf = buf.value
    chans = pybuf.decode('utf-8').split(",")
    #print(chans)
    return chans

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = FGenerator()
    myapp.show()
    sys.exit(app.exec_())
