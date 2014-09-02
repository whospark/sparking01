import os

def sampledir():
    return os.path.abspath(os.path.dirname(__file__))

def sampleimage():
    return os.path.join(sampledir(), 'sample_image.jpg')

def samplewav():
    return os.path.join(sampledir(), 'asample_syl.wav')

def samplewav333():
    return os.path.join(sampledir(), 'asample_syl333.wav')

def calibration_filename():
    return os.path.join(sampledir(), 'calibration.hdf5')

def datafile():
    return os.path.join(sampledir(), 'dummydata.hdf5')

def test_template():
    return os.path.join(sampledir(), 'multitone.json')

def badinputs():
    return os.path.join(sampledir(), 'controlinputs.json')

def batlabvocal():
    return os.path.join(sampledir(), 'batlabvocal.json')

def reallylong():
    return os.path.join(sampledir(), 'ohgodwhenwillitend.json')