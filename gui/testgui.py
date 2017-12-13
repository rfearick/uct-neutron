#!/usr/bin/env python

# working multithread pyqt5 code
# taken from develop/testbed3.py

"""
TODO
SpectrumPlot -- too many names
SpectrumPlot -- handle start of sort/interaction with update timer
"""

#filepath="../../../All raw data and analyses from iTL neutrons 2009/100MeV/NE213/"


import sys
sys.path.append("..") # for eventlist.py
from eventlist import Histogram, Sorter, EventSource
from eventlist import EventFlags
TIMER   =EventFlags.TIMER
PAD     =EventFlags.PAD
RTC     =EventFlags.RTC
SYNCHRON=EventFlags.SYNCHRON
ADCEVENT=EventFlags.ADCEVENT
ADC1=EventFlags.ADC1
ADC2=EventFlags.ADC2
ADC3=EventFlags.ADC3
ADC4=EventFlags.ADC4

from PyQt5 import Qt, QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import numpy as np
import matplotlib
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector
import configparser
import logging

#logging.basicConfig(level=logging.INFO)
logger=logging.getLogger("neutrons")
logger.propagate=False  # don't log message via root logger to console
logger.setLevel(logging.INFO)

plt.ion()       # turn on interactive mode of matplotlib

import icons    # part of this package -- toolbar icons
import time

count=0

def onselect(verts):
    print(verts)

class SpectrumPlot(Qt.QObject):
    """
    define a spectrum plot
    parent:    main window; defines the plot model we use
    h     :    histogram to plot
    tree  :    StardardItemModel row into which plot is inserted in TreeView
    name  :    name given to histogram
    xname :    label for x axis
    yname :    label for y axis
    """
    def __init__( self, parent, h, tree, name, xname, yname  ):
        super().__init__(parent=parent)
        self.plotmodel=parent.plotmodel
        self.histo=h
        self.unsorted=True
        self.tree=tree
        self.name=name
        self.xname=xname
        self.yname=yname
        self.fig=None
        print("plot object created")
        self.timer=Qt.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update)
        parent.bthread.finished.connect(self.stop_update)
        # now insert ourself into listview
        self.insertPlot(tree)

       
    def insertPlot(self, parentitem):
        """
        insert plot repr into list view widget
        """
        plot=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),self.name)
        parentitem.appendRow(plot)
        plot.setData(self)
   
    def openPlot(self):
        """
        handle double click signal from listview
        plot corresponding data
        """
        from polygonlasso import MyLassoSelector
        h=self.histo
        fig=plt.figure(self.name)
        nfig=fig.number
        #print('fig',plt.get_fignums(),nfig, h.dims, self.unsorted)
        self.drawPlot(h)
        fig.canvas.draw_idle()
        if self.fig is None:
            if h.dims==2:
                ax=fig.gca()
                self.lasso=MyLassoSelector(ax,onselect,useblit=False)
                #print("lasso")
        self.fig=nfig
        fig.canvas.manager.window.closing.connect(self.closed)
        if self.unsorted: self.timer.start()

    def drawPlot(self,h):
        """
        draw the plot on matplotlib canvas
        """
        if h.dims==1:
            adc=h.adc1
            data,yl,xl=h.get_plotdata()
            x,xl=self._getCalibratedScale(adc,h,xl,h.size1) ##xl->self.xname?
            if x is None:
                plt.plot(data,drawstyle='steps-mid')
                plt.ylabel(yl+' '+self.yname)
                plt.xlabel(self.xname)
            else:
                plt.plot(x,data,drawstyle='steps-mid')
                plt.ylabel(yl+' '+self.yname)
                plt.xlabel(xl)
                
        else:
            adc1=h.adc1
            adc2=h.adc2
            data,xl,yl=h.get_plotlabels()
            x,xl=self._getCalibratedScale(adc1,h,xl,h.size1)
            y,yl=self._getCalibratedScale(adc2,h,yl,h.size2)
            if x is None: x=[0,h.size1]
            if y is None: y=[0,h.size2]
            plt.imshow(data,origin='lower',vmax=2000,
                       extent=[x[0],x[-1],y[0],y[-1]],
                       aspect='auto')
            ax=plt.gca()
            plt.xlabel(xl+' '+self.xname)
            plt.ylabel(yl+' '+self.yname)

    def _getCalibratedScale(self, adc, h, xl, size):
            x=None
            calib=self.parent().calib
            if calib is not None:
                calib=self.parent().calib.calibration
                try:
                    # must compensate for histo size
                    factor=1024//size  # -> divisor
                    if adc==calib['EADC']:
                        m=calib['slope']/factor
                        c=calib['intercept']/factor
                        x=np.arange(0.0,float(size),1.0)
                        x=(1.0/m)*x-c/m
                        xl="Energy [MeVee]"
                    elif adc==calib['TADC']:
                        m=calib['TAC']/factor
                        x=np.arange(0.0,float(size),1.0)
                        x=x/m
                        xl="T [ns]"              
                except:
                        x=np.arange(0.0,float(size),1.0)
            return x, xl
        
    
    @pyqtSlot()
    def update(self):
        """
        update the plot if timer is active (i.e. sorting active)
        """
        nfig=self.fig
        fig=plt.figure(nfig)
        plt.cla()
        self.drawPlot(self.histo)

    @pyqtSlot()
    def stop_update(self):
        """
        cease updating plot when sorting done
        """
        #print('fig',self.fig, ' end update')
        self.unsorted=False
        self.timer.stop()

    @pyqtSlot()
    def closed(self):
        """
        stop timer when window closed
        """
        self.timer.stop()

class SpectrumItemModel(Qt.QStandardItemModel):
    def __init__(self, parent):
        super().__init__(parent=parent)
        parent.listview.doubleClicked.connect(self.openPlot)
        self.parent=parent

    def openPlot(self,p):
        """
        Find where double-click and open the plot
        """
        plot=self.parent.plotmodel.itemFromIndex(p)
        s=plot.data()
        if s is not None:
            s.openPlot()
                
def SetupSort(parent):
    """
    Setup a sort of data
    This is hardwired here.
    At some point this will change; there should be some sort builder program.
    """
    filepath="../../../All raw data and analyses from iTL neutrons 2009/100MeV/NE213/"
    fileNE213="NE213_025.lst"  # 0deg natLi
    #fileNE213="NE213_026.lst"  # 0deg 12C 
    #fileNE213="NE213_028.lst"  # 16deg natLi
    #fileNE213="NE213_029.lst"  # 16deg 12C 
    #infile="../../NE213 100 MeV data/NE213_010_100MeV_0deg.lst"
    
    infile=filepath+fileNE213
    if parent.calib is not None:
        calibration=parent.calib.calibration
        if len(calibration)==5:
            print("Spectrum is calibrated")
    
    E=EventSource(infile)

    h1=Histogram(E, ADC1+ADC2+ADC3, 'ADC1', 512)
    h2=Histogram(E, ADC1+ADC2+ADC3, 'ADC2', 512)
    h3=Histogram(E, ADC1+ADC2+ADC3, 'ADC3', 512)
    h4=Histogram(E, ADC4, 'ADC4', 512)
    h21=Histogram(E, ADC1+ADC2+ADC3, ('ADC1','ADC2'), (256,256),label=('L','S'))
    h13=Histogram(E, ADC1+ADC2+ADC3, ('ADC1','ADC3'), (256,256),label=('L','T'))
    histlist=[h1,h2,h3,h4,h21,h13]
    S=Sorter( E, histlist)

    # create tree for plots widget
    model=parent.plotmodel
    tree=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"NE213 data")
    model.appendRow(tree)

    # create plot items 
    s1=SpectrumPlot( parent, h1, tree, "NE213 Adc 1", "channel", "counts per channel")
    s2=SpectrumPlot( parent, h2, tree, "NE213 Adc 2", "channel", "counts per channel")
    s3=SpectrumPlot( parent, h3, tree, "NE213 Adc 3", "channel", "counts per channel")
    s4=SpectrumPlot( parent, h4, tree, "NE213 Adc 4", "channel", "counts per channel")
    s21=SpectrumPlot( parent, h21, tree, "NE213 Adc1 v Adc2", "Long", "Short")
    s13=SpectrumPlot( parent, h13, tree, "NE213 Adc1 v Adc3", "Long", "TOF")

    return S

    """
    # some of this to be included in future
    sortadc=[]
    deadtimer=[]
    t0=time.perf_counter()
    """

def SetupFCSort(parent):
    """
    Setup a sort of fission chamber data
    This is hardwired here.
    At some point this will change; there should be some sort builder program.
    """
    filepath="../../../All raw data and analyses from iTL neutrons 2009/100MeV/FC/"
    fileNE213="FC_035.lst"  # 0deg natLi

    infile=filepath+fileNE213
    
    E=EventSource(infile)
 
    h1=Histogram(E, ADC1+ADC3, 'ADC1', 512)
    h3=Histogram(E, ADC1+ADC3, 'ADC3', 512)
    h4=Histogram(E, ADC4, 'ADC4', 512)
    h13=Histogram(E, ADC1+ADC3, ('ADC1','ADC3'), (256,256),label=('L','T'))
    histlist=[h1,h3,h4,h13]
    S=Sorter( E, histlist)

    # create tree for plots widget
    model=parent.plotmodel
    tree=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"Fission chamber")
    model.appendRow(tree)
    # create plot items
    s1=SpectrumPlot( parent, h1, tree, "FC Adc 1", "channel", "counts per channel")
    s3=SpectrumPlot( parent, h3, tree, "FC Adc 3", "channel", "counts per channel")
    s4=SpectrumPlot( parent, h4, tree, "FC Adc 4", "channel", "counts per channel")
    s13=SpectrumPlot( parent, h13, tree, "FC Adc1 v Adc3", "Long", "TOF")

    return S

class Task(Qt.QObject):
    """
    Define a task potentially run in background
    """
    finished=pyqtSignal()
    def __init__(self, sorter):
        super().__init__()
        self.task = task

    def starttask(self):
        """
        start the sort task; emit signal when done to release background thread
        """
        logger.info("start task")
        # task.start() ?
        sortadc=self.task.start()
        logger.info("end task")
        self.finished.emit()

class BackgroundSort(Qt.QObject):
    """
    Run sort in a background thread
    """
    finished=pyqtSignal()
    def __init__(self, sorter):
        super().__init__()
        self.sorter = sorter
        
    def task(self):
        """
        start the sort task; emit signal when done to release background thread
        """
        logger.info("start sorting task")
        sortadc=self.sorter.sort()
        logger.info("end sorting task")
        self.finished.emit()     
        # sort returns histogram data of adc distribution -- do something with it
    
# initial analysis tasks
analysis_tasks=["Calibrate","Sort NE213","Sort FC"]

class ListLogger(object):
    def __init__(self, list):
        self.list=list

    def write(self,data):
        """
        1) must remove line feed at end
        2) seeks to be a spurious line feed coming through as well
        """
        if len(data)<=1: return
        if data[-1] in ['\r','\n']: data=data[0:-1]
        Qt.QListWidgetItem(data,self.list)

    def flush(self):
        pass

class NeutronAnalysisDemo(Qt.QMainWindow):
    """
    Application container  widget

    Handles toolbar and status.
    """
    def __init__(self, *args):
        Qt.QMainWindow.__init__(self, *args)

        self.calib=None
        self.freezeState = 0
        self.changeState = 0
        self.averageState = 0
        self.autocState = 0
        self.mainwin=Qt.QSplitter(self)
        self.logwin=Qt.QListWidget(self)
        vlayout=Qt.QVBoxLayout()
        vlayout.addWidget(self.mainwin)
        label=self.makeLabel("Analysis log")
        vlayout.addWidget(label)
        vlayout.addWidget(self.logwin)
        self.setGeometry(10,10,1024,768)
        #self.setCentralWidget(self.mainwin)
        w=Qt.QWidget()
        w.setLayout(vlayout)
        self.setCentralWidget(w)
        logstream=ListLogger(self.logwin)
        loghandler=logging.StreamHandler(logstream)
        loghandler.setFormatter(logging.Formatter(fmt='%(asctime)s : %(levelname)s : %(message)s'))
        logger.addHandler(loghandler)
        
        
        self.filewidget=Qt.QWidget()
        vlayout=Qt.QVBoxLayout()
        from fileentry import FilePicker
        self.filepick=FilePicker()
        label=self.makeLabel("Analysis Files")
        vlayout.addWidget(label)
        vlayout.addWidget(self.filepick)
        vlayout.setContentsMargins(1,1,1,1) # cut down margins from 11px
        self.filewidget.setLayout(vlayout)
        self.mainwin.addWidget(self.filewidget)

               
        self.taskwidget=Qt.QWidget()
        vlayout=Qt.QVBoxLayout()
        self.tasklist=Qt.QListWidget(self)
        self.tasklistitems={}  # keep a dict of these, may expand in future
        for task in analysis_tasks:
            item=Qt.QListWidgetItem(task,self.tasklist)
            item.setFlags(item.flags()&~QtCore.Qt.ItemIsEnabled)
            self.tasklistitems[task]=item
        self.tasklist.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        label=self.makeLabel("Task list")
        vlayout.addWidget(label)
        vlayout.addWidget(self.tasklist)
        vlayout.setContentsMargins(1,1,1,1) # cut down margins from 11px
        self.taskwidget.setLayout(vlayout)
        self.mainwin.addWidget(self.taskwidget)
 
        # example code taken from dualscopeN.py
        toolBar = Qt.QToolBar(self)
        self.addToolBar(toolBar)
        sb=self.statusBar()
        sbfont=Qt.QFont("Helvetica",12)
        sb.setFont(sbfont)
        sb.showMessage("Status=1")

        self.btnFreeze = Qt.QToolButton(toolBar)
        self.btnFreeze.setText("Open expt")
        self.btnFreeze.setIcon(Qt.QIcon(Qt.QPixmap(icons.stopicon)))
        self.btnFreeze.setCheckable(True)
        self.btnFreeze.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        self.btnFreeze.setToolTip("Open experiment file")
        toolBar.addWidget(self.btnFreeze)
        
        self.btnMode = Qt.QToolButton(toolBar)
        self.btnMode.setText("Save expt")
        self.btnMode.setIcon(self.style().standardIcon(Qt.QStyle.SP_DriveFDIcon))
        self.btnMode.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnMode)
        
        self.btnPrint = Qt.QToolButton(toolBar)
        self.btnPrint.setText("Print")
        self.btnPrint.setIcon(Qt.QIcon(Qt.QPixmap(icons.print_xpm)))
        self.btnPrint.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnPrint)

        """
        self.btnAvge = Qt.QToolButton(toolBar)
        self.btnAvge.setText("average")
        self.btnAvge.setIcon(Qt.QIcon(Qt.QPixmap(icons.avge)))
        self.btnAvge.setCheckable(True)
        self.btnAvge.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnAvge)

        self.btnAutoc = Qt.QToolButton(toolBar)
        self.btnAutoc.setText("correlate")
        self.btnAutoc.setIcon(Qt.QIcon(Qt.QPixmap(icons.avge)))
        self.btnAutoc.setCheckable(True)
        self.btnAutoc.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnAutoc)

        self.lstLabl = Qt.QLabel("Buffer:",toolBar)
        toolBar.addWidget(self.lstLabl)
        self.lstChan = Qt.QComboBox(toolBar)
        self.lstChan.insertItem(0,"8192")
        self.lstChan.insertItem(1,"16k")
        self.lstChan.insertItem(2,"32k")
        toolBar.addWidget(self.lstChan)
        
        self.lstLR = Qt.QLabel("Channels:",toolBar)
        toolBar.addWidget(self.lstLR)
        self.lstLRmode = Qt.QComboBox(toolBar)
        self.lstLRmode.insertItem(0,"LR")
        self.lstLRmode.insertItem(1,"L")
        self.lstLRmode.insertItem(2,"R")
        toolBar.addWidget(self.lstLRmode)
        """

        # set up a model for spectra plots
        self.plotwidget=Qt.QWidget()
        vlayout=Qt.QVBoxLayout()
        self.listview=Qt.QTreeView(self)
        self.plotmodel=SpectrumItemModel(self)#Qt.QStandardItemModel(self)
        #self.listview.setViewMode(Qt.QListView.IconMode)
        self.listview.setModel(self.plotmodel)
        self.listview.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        label=self.makeLabel("Plot list")
        vlayout.addWidget(label)
        vlayout.addWidget(self.listview)
        vlayout.setContentsMargins(1,1,1,1) # cut down margins from 11px
        self.plotwidget.setLayout(vlayout)
        self.mainwin.addWidget(self.plotwidget)
                                  
        self.tasklist.doubleClicked.connect(self.runTask)
        self.filepick.valueChanged.connect(self.setFilePaths)
        self.btnFreeze.clicked.connect(self.openFile)
        self.btnMode.clicked.connect(self.saveFile)
        self.bthread = None

    def makeLabel(self, title):
        """
        centralize label creation here so all customisation in one place
        """
        font=Qt.QFont("Helvetica",12,Qt.QFont.Bold)
        label=Qt.QLabel(title)
        label.setFont(font)
        label.setMargin(6)
        label.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
        label.setFrameStyle(Qt.QFrame.StyledPanel|Qt.QFrame.Raised)
        label.setContentsMargins(1,2,1,2)
        return label
        

    def startSorting(self, setupsorter):
        """
        start a sort process
        this will evolve to dispatch different sorts at various times
        """
        # setup sort in background
        if self.bthread is None:
            pass
        elif self.bthread.isRunning():
            logger.warn("Sort already in progress")
            return
        self.bthread=Qt.QThread()
        S=setupsorter(self)
        bobj=BackgroundSort(S)
        bobj.moveToThread(self.bthread)
        self.bthread.started.connect(bobj.task)
        bobj.finished.connect(self.cleanupThread)
        self.bobj=bobj # keep reference
        
        # start sort
        self.bthread.start()
        #print('thread',self.bthread.isRunning())

    @pyqtSlot()
    def cleanupThread(self):
        """
        quit background thread when sorting done
        """
        #print("cleanup")
        self.bthread.quit()

    def runTask(self,p):
        # placeholder...
        m=self.tasklist.itemFromIndex(p)
        sorttype=m.text()
        logger.info("Run task: "+sorttype)
        if sorttype=="Sort NE213":
            self.startSorting(SetupSort)
        elif sorttype=="Sort FC":
            self.startSorting(SetupFCSort)
        elif sorttype=="Calibrate":
            import calibrate as calibrator
            self.calib=calibrator.Calibrator(self.filepick.files['Na'],
                                             self.filepick.files['Cs'],
                                             self.filepick.files['AmBe'],
                                             self.filepick.files['TAC'])
            logger.info("Start sort for calibration")
            self.calib.sort()
            # create tree for plots widget
            model=self.plotmodel
            tree=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"Calibration")
            model.appendRow(tree)
            ploticon=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"calib")
            self.calibplot=calibrator.CalibrationPlotter(self.calib)
            self.calibplot.insertPlot(tree, ploticon)
            self.calibplot.plot_all_spectra() 
        
    
    def openFile(self,p):
        filename,_=Qt.QFileDialog.getOpenFileName(self,'Open file',
                                                  '.',"Experiment (*.exp)")
        if filename == '': return
        C=configparser.ConfigParser(strict=False,inline_comment_prefixes=(';',))
        C.optionxform=lambda option: option
        C.read(filename)
        files=C.items("Files")
        self.filepick.setFiles(dict(files))
        logger.info("Open file "+filename)

    def saveFile(self,p):
        if self.filepick.files is None:
            logger.warn("Nothing to save")
            return
        filename,_=Qt.QFileDialog.getSaveFileName(self,'Save file',
                                                  '.',"Experiment (*.exp)")
        if filename == '': return
        C=configparser.ConfigParser(strict=False,inline_comment_prefixes=(';',))
        C.optionxform=lambda option: option
        filedict={}
        filedict['Files']=self.filepick.files
        fd=filedict['Files']
        for key in fd:
            fd[key]=str(fd[key])
        C.read_dict(filedict)
        # future: ask on existing file - but not needed on OSX !
        f=open(filename,"w")
        C.write(f)
        f.close()
        logger.info("Write file: "+filename)

    @pyqtSlot(int)
    def setFilePaths(self, count):
        files=self.filepick.files
        calibfiles=set(self.filepick.calibtags)
        if calibfiles.issubset(files.keys()):
            item=self.tasklistitems["Calibrate"]
            #print(calibfiles)
            item.setFlags(item.flags()|QtCore.Qt.ItemIsEnabled)
        if "NE213" in files.keys():
            item=self.tasklistitems[analysis_tasks[1]]
            item.setFlags(item.flags()|QtCore.Qt.ItemIsEnabled)
        if "FC" in files.keys():
            item=self.tasklistitems[analysis_tasks[2]]
            item.setFlags(item.flags()|QtCore.Qt.ItemIsEnabled)
            
    def printPlot(self):
        p = QPrinter()

# Admire! 
app = Qt.QApplication(sys.argv)
demo=NeutronAnalysisDemo()
demo.show()
#demo.startSorting()
sys.exit(app.exec_())
