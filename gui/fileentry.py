from pathlib import Path
import configparser

from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtWidgets import QLineEdit

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
    def __init__(self, name):
        super().__init__()
        self.id=name
        self.filename=None
        self.scalers=None

    def mouseDoubleClickEvent(self, event):      
        self.getFile()

    def getFile(self):
        directory=FileField.currentpath if FileField.currentpath is not None else '.'
        directory=str(directory)
        #print("directory", directory)
        filename,_=Qt.QFileDialog.getOpenFileName(self,'Open file',directory,"List files (*.lst)")
        print(filename)
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
            self.valueChanged.emit(self.id,pp)

    def getScalerData( self, filepath ):
        """
        get scaler data from mpa file.
        input:
            filepath:  .mpapath from FileField object for run file
        """
        if not filepath.exists():
            print("No mpa file exists")
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

class FilePicker(QTabWidget):
    """
    Create a tabbed widget with file entry points for calibration, ne213 and fc
    Accumulate file names in dict self.files.
    """
    valueChanged=pyqtSignal(int)
    def __init__(self):

        super().__init__()
        self.calibfiles = QWidget()
        self.ne213files = QWidget()
        self.fcfiles    = QWidget()

        self._makeCalibTab()
        self._makeNE213Tab()
        self._makeFCTab()

        self.editNa=None
        self.editCs=None
        self.editAmBe=None
        self.editTAC=None
        self.editNE213=None
        self.editFC=None
        self.countfiles=6 # number of files to get

        self.files={}
        
    def _makeCalibTab(self):

        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("22Na") )
        self.editNa=FileField("22Na")
        hlayout.addWidget( self.editNa )
        layout.addLayout( hlayout )
        self.editNa.valueChanged.connect(self.setFilePath)
        
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("137Cs") )
        self.editCs=FileField("137Cs")
        hlayout.addWidget( self.editCs )
        layout.addLayout( hlayout )
        self.editCs.valueChanged.connect(self.setFilePath)
       
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("AmBe") )
        self.editAmBe=FileField("AmBe")
        hlayout.addWidget( self.editAmBe )
        layout.addLayout( hlayout )
        self.editAmBe.valueChanged.connect(self.setFilePath)
        
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("TAC") )
        self.editTAC=FileField("TAC")
        hlayout.addWidget( self.editTAC )
        layout.addLayout( hlayout )
        self.editTAC.valueChanged.connect(self.setFilePath)

        self.calibfiles.setLayout(layout)
        self.addTab( self.calibfiles, "Calibration" )

    def _makeNE213Tab(self):
        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("NE213") )
        self.editNE213=FileField("NE213")
        hlayout.addWidget( self.editNE213 )
        layout.addLayout( hlayout )
        self.editNE213.valueChanged.connect(self.setFilePath)
        self.ne213files.setLayout(layout)
        self.addTab( self.ne213files, "NE213" )
        
    def _makeFCTab(self):
        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("Fission") )
        self.editFC=FileField("Fission")
        hlayout.addWidget( self.editFC )
        layout.addLayout( hlayout )
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
        self.valueChanged.emit(len(self.files)) # notify if file count changed
        
        

        
