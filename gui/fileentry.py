from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtWidgets import QLineEdit


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

    def _makeCalibTab(self):

        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("22Na") )
        hlayout.addWidget( QLineEdit() )
        layout.addLayout( hlayout )
        
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("137Cs") )
        hlayout.addWidget( QLineEdit() )
        layout.addLayout( hlayout )
       
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("AmBe") )
        hlayout.addWidget( QLineEdit() )
        layout.addLayout( hlayout )
        
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("TAC") )
        hlayout.addWidget( QLineEdit() )
        layout.addLayout( hlayout )

        self.calibfiles.setLayout(layout)
        self.addTab( self.calibfiles, "Calibration" )
        
    def _makeNE213Tab(self):
        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("NE213") )
        hlayout.addWidget( QLineEdit() )
        layout.addLayout( hlayout )
        self.ne213files.setLayout(layout)
        self.addTab( self.ne213files, "NE213" )
        
    def _makeFCTab(self):
        layout=QVBoxLayout()
        hlayout=QHBoxLayout()
        hlayout.addWidget( QLabel("Fission") )
        hlayout.addWidget( QLineEdit() )
        layout.addLayout( hlayout )
        self.fcfiles.setLayout(layout)
        self.addTab( self.fcfiles, "Fission Chamber" )

        
