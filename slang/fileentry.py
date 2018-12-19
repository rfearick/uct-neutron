from pathlib import Path
import configparser

from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from PyQt5.QtWidgets import (QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGroupBox, QRadioButton)
from PyQt5.QtWidgets import QLineEdit

import logging
from . import analysisdata

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
        filename,_=Qt.QFileDialog.getOpenFileName(self,'Open file',directory,"List files (*.lst)")
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
            mpapath=pp.with_suffix(".mpa")
            scalers=self.getScalerData(mpapath)
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
            mpapath=pp.with_suffix(".mpa")
            scalers=self.getScalerData(mpapath)
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

        self.editNE213=None
        self.editDefTOF=None # define time of flight spectrum
        self.editTgamma=None # for gamma flash from target to define Tgamma
        self.editFC=None
        #self.countfiles=6    # number of files to get

        self.files={}
        
        self._makeDataTab()
        self.addTab( self.calibfiles, "Calibration" )
        self._makeCalibTab()
        self._makeNE213Tab()
        self._makeFCTab()

    def _makeTabItem(self, layout, TabField, label, tag, fmt, connection):
        adata=analysisdata.AnalysisData()
        layout.addWidget( QLabel(label) )
        field=TabField(tag)
        setattr(self, "edit"+tag, field)
        #f=getattr(self, "edit_"+tag)
        layout.addWidget( field )
        if fmt is not None: field.setText(fmt%(getattr(adata,tag)))
        #layout.addStretch(1)
        field.valueChanged.connect(connection)
       

    def _makeDataTab(self):
        # label, tag=attribute name, format,connection
        datatabitems=(
            ("TAC interval [ns]","TAC_interval","%4.1f",self.setCalibData),
            ("Target distance [m]","target_distance","%5.3f",self.setCalibData),
            ("Calibration gain boost","calibration_gain","%3.1f",self.setCalibData),
            ("L threshold [MeVee]","L_threshold","%3.1f",self.setCalibData),
            ("Tgamma from TOF[ns]","Tgamma","%.2f",self.setCalibData)
        )
        
        layout=QVBoxLayout()
        adata=analysisdata.AnalysisData()
        for label, tag, fmt, conn in datatabitems:
            self._makeTabItem(layout, DataField, label, tag, fmt, conn)
        
        self.calibdata.setLayout(layout)
        self.addTab( self.calibdata, "Analysis Data" )
        
        
    def _makeCalibTab(self, style='radio'):

        # label, tag=attribute name, format,connection
        layout=QVBoxLayout()
        if style == 'sortfiles':
            calibtabitems=(
                ("22Na:", "Na", None, self.setFilePath),
                ("60Co:", "Co", None, self.setFilePath),
                ("137Cs:", "Cs", None, self.setFilePath),
                ("AmBe:", "AmBe", None, self.setFilePath),
                ("TAC:", "TAC", None, self.setFilePath),
                )
            for label, tag, fmt, conn in calibtabitems:
                self._makeTabItem(layout, FileField, label, tag, fmt, conn)

            #self.calibfiles.setLayout(layout)
        elif style == 'entervalues': 
            calibtabitems=(
                 ("Gamma slope [MeV/ch]", "slope", None, self.setCalibData), 
                 ("Gamma intercept [MeV]", "intercept", None, self.setCalibData), 
                 ("TAC slope [ns/ch]", "TAC", None, self.setCalibData)
                 )
            for label, tag, fmt, conn in calibtabitems:
                self._makeTabItem(layout, DataField, label, tag, fmt, conn)
            layout.addStretch(2)
        else:
            layout=self._chooseCalibTab()
        oldlayout=self.calibfiles.layout()
        if oldlayout is None:
            self.calibfiles.setLayout(layout)
        else:
            print('count',oldlayout.count())
            # this following code is not obvious, and took some googling. See e.g.
            #stackoverflow.com/questions/22623151/python-how-to-unassign-layout-from-groupbox-in-pyqt
            import sip
            #for i in range(oldlayout.count()):
            while oldlayout.count():
                item=oldlayout.takeAt(0)
                #print(i,item, item.widget())
                w=item.widget()
                if w is not None:
                    w.deleteLater()
            sip.delete(oldlayout)
                
            self.calibfiles.setLayout(layout)
            
           
        #self.addTab( self.calibfiles, "Calibration" )
        self.calibtags=("Na","Cs","AmBe","TAC")

    def _makeNE213Tab(self):
        layout=QVBoxLayout()
        layout.addWidget( QLabel("NE213:") )
        self.editNE213=FileField("NE213")
        layout.addWidget( self.editNE213 )
        #layout.addStretch(1)
        self.editNE213.valueChanged.connect(self.setFilePath)

        layout.addWidget( QLabel("NE213:TOF channel") )
        self.editDefTOF=DataField("TOFchannel")
        layout.addWidget( self.editDefTOF )
        self.editDefTOF.setText("ADC3")
        layout.addStretch(1)

        #layout.addWidget( QLabel("NE213:Tgamma [ns]") )
        #self.editTgamma=DataField("Tgamma")
        #layout.addWidget( self.editTgamma )
        #self.editTgamma.setText("0.0")
        #layout.addStretch(1)
        #self.editTgamma.valueChanged.connect(self.setCalibData)
        
        self.ne213files.setLayout(layout)
        self.addTab( self.ne213files, "NE213" )
        
    def _makeFCTab(self):
        layout=QVBoxLayout()
        layout.addWidget( QLabel("Fission:") )
        self.editFC=FileField("FC")
        layout.addWidget( self.editFC )
        layout.addStretch(1)
        self.editFC.valueChanged.connect(self.setFilePath)
        self.fcfiles.setLayout(layout)
        self.addTab( self.fcfiles, "Fission Chamber" )

    def _chooseCalibTab(self):
        tab=QVBoxLayout()
        layout=QVBoxLayout()
        group=QGroupBox("Choose calibration option")
        b1=QRadioButton("Sort files for calibration")
        b2=QRadioButton("Enter calibration values")
        # emits toggled
        b1.toggled.connect(self._chooseCalibMethod)
        b2.toggled.connect(self._chooseCalibMethod)
        #b1.setChecked(True)
        self.radiosort=b1
        self.radioenter=b2
        layout.addWidget(b1)
        layout.addWidget(b2)
        layout.addStretch(1)
        group.setLayout(layout)
        tab.addWidget(group)
        tab.addStretch(1)
        return tab

    @pyqtSlot(bool)
    def _chooseCalibMethod(self, ident):
        if self.radiosort.isChecked():
            print('sort')
            self._makeCalibTab(style='sortfiles')
        if self.radioenter.isChecked():
            print('enter')
            self._makeCalibTab(style='entervalues')

    @pyqtSlot('QString',Path)
    def setFilePath(self, ident, pathname):
        """
        pack file paths into dict.
        """
        self.files[ident]=pathname
        self.fileChanged.emit(len(self.files)) # notify if file count changed

    def setFiles(self, files):
        """
        Set filename in fields from a file
        """
        fkey=files.keys()
        for f in fkey:
            getattr(self, "edit"+f).setFile(files[f])
        """
        if 'Na' in fkey: self.editNa.setFile(files['Na'])
        if 'Co' in fkey: self.editCo.setFile(files['Co'])
        if 'Cs' in fkey: self.editCs.setFile(files['Cs'])
        if 'AmBe' in fkey: self.editAmBe.setFile(files['AmBe'])
        if 'TAC' in fkey: self.editTAC.setFile(files['TAC'])
        if 'NE213' in fkey: self.editNE213.setFile(files['NE213'])
        if 'FC' in fkey: self.editFC.setFile(files['FC'])
        """

    def setDataTab(self):
        adata=analysisdata.AnalysisData()

        self.editTAC_interval.setText("%4.1f"%(adata.TAC_interval,))
        self.edittarget_distance.setText("%5.3f"%(adata.target_distance,))
        self.editcalibration_gain.setText("%3.1f"%(adata.calibration_gain,))
        self.editL_threshold.setText("%3.1f"%(adata.L_threshold,))
        self.editTgamma.setText("%.2f"%(adata.Tgamma,))

        
    @pyqtSlot('QString','QString')
    def setCalibData(self, ident, data):
        """
        set data from entry field.
        """
        self.dataChanged.emit(str(ident),str(data)) # notify if file count changed

        
        

        
