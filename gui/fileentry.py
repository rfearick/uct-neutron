from pathlib import Path
import configparser

from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtWidgets import QLineEdit

import logging
import analysisdata

"""
Gather the file names needed for analysis
"""

scaler_names=['sc#01','sc#02','sc#03','sc#04','sc#05','sc#06']

class FileField(QLineEdit):
    """
    Subclass the QLineEdit to repurpose it for file field duty.

    Double click will bring up the file dialog.
    This widget uses the standard python pathlib to parse and manipulate file
    paths, in an OS independent way.
    """
    currentpath=None
    valueChanged=pyqtSignal('QString',Path)
    
    def __init__(self, tag):
        super().__init__()
        self.tag=tag
        self.filename=None
        self.scalers=None

    def mouseDoubleClickEvent(self, event):      
        self.getFile()

    def getFile(self):
        directory=FileField.currentpath if FileField.currentpath is not None else '.'
        directory=str(directory)
        #print("directory", directory)
        filename,_=Qt.QFileDialog.getOpenFileName(self,'Open file',directory,"List files (*.lst)")
        #print(filename)
        if filename == '': return
        pp=Path(filename)
        if pp.exists():
            self.filename=filename
            self.path=pp
            self.name=pp.name
            self.stem=pp.stem
            self.parentpath=pp.parent
            if FileField.currentpath is None or FileField.currentpath != self.parentpath:
                FileField.currentpath=pp.parent           
            self.setText(pp.name)
            #print("input file:",filename)
            #print("parent    :",pp.parent)
            mpapath=pp.with_suffix(".mpa")
            #print("mpafile   :",mpapath.exists())
            scalers=self.getScalerData(mpapath)
            ##print("scalers",scalers)
            self.valueChanged.emit(self.tag,pp)

    def setFile(self,filename):
        pp=Path(filename)
        if pp.exists():
            self.filename=filename
            self.path=pp
            self.name=pp.name
            self.stem=pp.stem
            self.parentpath=pp.parent
            if FileField.currentpath is None or FileField.currentpath != self.parentpath:
                FileField.currentpath=pp.parent           
            self.setText(pp.name)
            #print("input file:",filename)
            #print("parent    :",pp.parent)
            mpapath=pp.with_suffix(".mpa")
            #print("mpafile   :",mpapath.exists())
            scalers=self.getScalerData(mpapath)
            ##print("scalers",scalers)
            self.valueChanged.emit(self.tag,pp)
        

    def getScalerData( self, filepath ):
        """
        get scaler data from mpa file.
        input:
            filepath:  .mpapath from FileField object for run file
        """
        if not filepath.exists():
            #print("No mpa file exists")
            logger=logging.getLogger("neutrons")
            logger.warn("No mpa file exists: "+filepath.name)
            self.scalers=None
            return None
        if self.scalers is not None:
            return self.scalers
        f=open(filepath,"r")
        lines=['[settings]'] # config part lacks initial header
        for l in f:
            if "[DATA" in l:
                break
            lines.append(l)
        C=configparser.ConfigParser(strict=False,inline_comment_prefixes=(';',))
        C.read_string(''.join(lines))
        scalers={}
        for i,sc in enumerate(scaler_names):
            scdata=C.getint("MS-12 A",sc)
            scalers[sc]=scdata
        f.close()
        self.scalers=scalers
        return self.scalers

class DataField(QLineEdit):
    """
    Subclass the QLineEdit to repurpose it for data field duty.
    This allows us to set a tag for ID

    """
    currentpath=None
    valueChanged=pyqtSignal('QString','QString')
    
    def __init__(self, tag):
        super().__init__()
        self.tag=tag
        self.data=None
        self.editingFinished.connect(self.sendData)

    def sendData( self ):
        data=self.text()
        #try:
        #    data=float(data)
        #except:
        #    data=0.0
        self.valueChanged.emit(self.tag,data)
                    
    def getFile(self):
        directory=FileField.currentpath if FileField.currentpath is not None else '.'
        directory=str(directory)
        #print("directory", directory)
        filename,_=Qt.QFileDialog.getOpenFileName(self,'Open file',directory,"List files (*.lst)")
        #print(filename)
        if filename == '': return
        pp=Path(filename)
        if pp.exists():
            self.filename=filename
            self.path=pp
            self.name=pp.name
            self.stem=pp.stem
            self.parentpath=pp.parent
            if FileField.currentpath is None or FileField.currentpath != self.parentpath:
                FileField.currentpath=pp.parent           
            self.setText(pp.name)
            #print("input file:",filename)
            #print("parent    :",pp.parent)
            mpapath=pp.with_suffix(".mpa")
            #print("mpafile   :",mpapath.exists())
            scalers=self.getScalerData(mpapath)
            ##print("scalers",scalers)
            self.valueChanged.emit(self.tag,pp)


class FilePicker(QTabWidget):
    """
    Create a tabbed widget with file entry points for calibration, ne213 and fc
    Accumulate file names in dict self.files.
    """
    valueChanged=pyqtSignal('QString')
    fileChanged=pyqtSignal(int)
    dataChanged=pyqtSignal('QString','QString')
    def __init__(self):

        super().__init__()
        self.calibdata  = QWidget()
        self.calibfiles = QWidget()
        self.ne213files = QWidget()
        self.fcfiles    = QWidget()
        
        self.editTACdt=None
        self.editTdist=None
        self.editCgain=None
        #self.editTgamma=None
        self.editNa=None
        self.editCs=None
        self.editAmBe=None
        self.editTAC=None
        self.editNE213=None
        self.editDefTOF=None # define time of flight spectrum
        self.editTgamma=None     # for gamma flash from target to define Tgamma
        self.editFC=None
        self.countfiles=6 # number of files to get

        self.files={}
        
        self._makeDataTab()
        self._makeCalibTab()
        self._makeNE213Tab()
        self._makeFCTab()

    def _makeDataTab(self):
        layout=QVBoxLayout()
        adata=analysisdata.AnalysisData()

        layout.addWidget( QLabel("TAC interval [ns]") )
        self.editTACdt=DataField("TAC dt")
        layout.addWidget( self.editTACdt )
        self.editTACdt.setText("%4.1f"%(adata.TAC_interval,))
        #layout.addLayout( hlayout )
        layout.addStretch(1)
        self.editTACdt.valueChanged.connect(self.setCalibData)
        
        layout.addWidget( QLabel("Target distance [m]") )
        self.editTdist=DataField("Tdist")
        layout.addWidget( self.editTdist )
        self.editTdist.setText("%5.3f"%(adata.target_distance,))
        #layout.addLayout( hlayout )
        layout.addStretch(1)
        self.editTdist.valueChanged.connect(self.setCalibData)
        
        layout.addWidget( QLabel("Calibration gain boost") )
        self.editCgain=DataField("Cgain")
        layout.addWidget( self.editCgain )
        self.editCgain.setText("%3.1f"%(adata.calibration_gain,))
        #layout.addLayout( hlayout )
        layout.addStretch(1)
        self.editCgain.valueChanged.connect(self.setCalibData)
        
        #layout.addWidget( QLabel("Tgamma from TOF[ns]") )
        #self.editTgamma=DataField("Tgamma")
        #layout.addWidget( self.editTgamma )
        #self.editTgamma.setText("0.0")
        ##layout.addLayout( hlayout )
        #layout.addStretch(1)
        #self.editTgamma.valueChanged.connect(self.setCalibData)
        
        self.calibdata.setLayout(layout)
        self.addTab( self.calibdata, "Analysis Data" )
        
        
    def _makeCalibTab(self):

        layout=QVBoxLayout()
        #hlayout=QHBoxLayout()
        layout.addWidget( QLabel("22Na:") )
        self.editNa=FileField("Na")
        layout.addWidget( self.editNa )
        #layout.addLayout( hlayout )
        layout.addSpacing(5)
        self.editNa.valueChanged.connect(self.setFilePath)
        
        #hlayout=QHBoxLayout()
        layout.addWidget( QLabel("137Cs:") )
        self.editCs=FileField("Cs")
        layout.addWidget( self.editCs )
        #layout.addLayout( hlayout )
        layout.addSpacing(5)
        self.editCs.valueChanged.connect(self.setFilePath)
       
        #hlayout=QHBoxLayout()
        layout.addWidget( QLabel("AmBe:") )
        self.editAmBe=FileField("AmBe")
        layout.addWidget( self.editAmBe )
        #layout.addLayout( hlayout )
        layout.addSpacing(5)
        self.editAmBe.valueChanged.connect(self.setFilePath)
        
        #hlayout=QHBoxLayout()
        layout.addWidget( QLabel("TAC:") )
        self.editTAC=FileField("TAC")
        layout.addWidget( self.editTAC )
        #layout.addLayout( hlayout )
        layout.addSpacing(5)
        self.editTAC.valueChanged.connect(self.setFilePath)

        layout.addStretch(1)

        self.calibfiles.setLayout(layout)
        self.addTab( self.calibfiles, "Calibration" )
        self.calibtags=("Na","Cs","AmBe","TAC")

    def _makeNE213Tab(self):
        layout=QVBoxLayout()
        #hlayout=QHBoxLayout()
        layout.addWidget( QLabel("NE213:") )
        self.editNE213=FileField("NE213")
        layout.addWidget( self.editNE213 )
        #layout.addLayout( hlayout )
        layout.addStretch(1)
        self.editNE213.valueChanged.connect(self.setFilePath)

        layout.addWidget( QLabel("NE213:TOF channel") )
        self.editDefTOF=DataField("TOFchannel")
        layout.addWidget( self.editDefTOF )
        self.editDefTOF.setText("ADC3")
        #layout.addLayout( hlayout )
        layout.addStretch(1)
        #self.editDefTOF.valueChanged.connect(self.setFilePath)

        layout.addWidget( QLabel("NE213:Tgamma [ns]") )
        self.editTgamma=DataField("Tgamma")
        layout.addWidget( self.editTgamma )
        self.editTgamma.setText("0.0")
        #layout.addLayout( hlayout )
        layout.addStretch(1)
        self.editTgamma.valueChanged.connect(self.setCalibData)
        
        self.ne213files.setLayout(layout)
        self.addTab( self.ne213files, "NE213" )
        
    def _makeFCTab(self):
        layout=QVBoxLayout()
        #hlayout=QHBoxLayout()
        layout.addWidget( QLabel("Fission:") )
        self.editFC=FileField("FC")
        layout.addWidget( self.editFC )
        #layout.addLayout( hlayout )
        layout.addStretch(1)
        self.editFC.valueChanged.connect(self.setFilePath)
        self.fcfiles.setLayout(layout)
        self.addTab( self.fcfiles, "Fission Chamber" )

    @pyqtSlot('QString',Path)
    def setFilePath(self, ident, pathname):
        """
        pack file paths into dict.
        """
        #print(ident,pathname)
        self.files[ident]=pathname
        #print(self.files)
        self.fileChanged.emit(len(self.files)) # notify if file count changed

    def setFiles(self, files):
        #self.files=files
        #print(self.editNa)
        self.editNa.setFile(files['Na'])
        self.editCs.setFile(files['Cs'])
        self.editAmBe.setFile(files['AmBe'])
        self.editTAC.setFile(files['TAC'])
        self.editNE213.setFile(files['NE213'])
        self.editFC.setFile(files['FC'])

    @pyqtSlot('QString','QString')
    def setCalibData(self, ident, data):
        """
        set data from entry field.
        """
        print(ident,data)
        #self.files[ident]=pathname
        #print(self.files)
        print(type(data))
        self.dataChanged.emit(str(ident),str(data)) # notify if file count changed

        
        

        
