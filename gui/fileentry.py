from pathlib import Path

from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtWidgets import QLineEdit

"""
Gather the file names needed for analysis
"""

class FileField(QLineEdit):
    """
    Subclass the QLineEdit to repurpose it for file field duty.

    Double click will bring up the file dialog.
    This widget uses the standard python pathlib to parse and manipulate file
    paths, in an OS independent way.
    """
    currentpath=None
    def __init__(self):
        super().__init__()
        self.filename=None

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

class FilePicker(QTabWidget):
    """
    Create a tabbed widget with file entry points for calibration, ne213 and fc
    """
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
        
    def _makeCalibTab(self):

        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("22Na") )
        self.editNa=FileField()
        hlayout.addWidget( self.editNa )
        layout.addLayout( hlayout )
        
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("137Cs") )
        self.editCs=FileField()
        hlayout.addWidget( self.editCs )
        layout.addLayout( hlayout )
       
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("AmBe") )
        self.editAmBe=FileField()
        hlayout.addWidget( self.editAmBe )
        layout.addLayout( hlayout )
        
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("TAC") )
        self.editTAC=FileField()
        hlayout.addWidget( self.editTAC )
        layout.addLayout( hlayout )

        self.calibfiles.setLayout(layout)
        self.addTab( self.calibfiles, "Calibration" )

    def _makeNE213Tab(self):
        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("NE213") )
        self.editNE213=FileField()
        hlayout.addWidget( self.editNE213 )
        layout.addLayout( hlayout )
        self.ne213files.setLayout(layout)
        self.addTab( self.ne213files, "NE213" )
        
    def _makeFCTab(self):
        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("Fission") )
        self.editFC=FileField()
        hlayout.addWidget( self.editFC )
        layout.addLayout( hlayout )
        self.fcfiles.setLayout(layout)
        self.addTab( self.fcfiles, "Fission Chamber" )

        
