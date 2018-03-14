"""
==========
testgui.py
==========

Demonstration of GUI for neutron TOF analysis.

Sort lst files and display histograms for NE213 and FC detectors.

Also permits calibration of NE213 spectra.

-----
"""
#!/usr/bin/env python

# working multithread pyqt5 code
# taken from develop/testbed3.py

"""
TODO
SpectrumPlot -- too many names
SpectrumPlot -- handle start of sort/interaction with update timer
"""

import sys
sys.path.append("..") # for eventlist.py
from eventlist import Histogram, Sorter, EventSource
from eventlist import EventFlags

#simplify event flags
TIMER   =EventFlags.TIMER
PAD     =EventFlags.PAD
RTC     =EventFlags.RTC
SYNCHRON=EventFlags.SYNCHRON
ADCEVENT=EventFlags.ADCEVENT
ADC1=EventFlags.ADC1
ADC2=EventFlags.ADC2
ADC3=EventFlags.ADC3
ADC4=EventFlags.ADC4

# event groups
GROUP_NE213=ADC1+ADC2+ADC3
GROUP_MONITOR=ADC4
GROUP_FC=ADC1+ADC3


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

from supportclasses import PlotTreeModel, PlotTreeView
from analysisdata import Calibration, AnalysisData

import icons    # part of this package -- toolbar icons
import time

plt.ion()       # turn on interactive mode of matplotlib

def onselect(verts):
    print(verts)

class SpectrumPlotter(Qt.QObject):
    """
    define a spectrum plot

    Parameters
    ----------

    parent:    main window; defines the plot model we use
    h     :    histogram to plot
    tree  :    StardardItemModel row into which plot is inserted in TreeView
    name  :    name given to histogram
    xname :    label for x axis -- default to None
    yname :    label for y axis -- default to None
    """
    def __init__( self, parent, h, tree, name, xname=None, yname=None  ):
        super().__init__(parent=parent)
        self.plotmodel=parent.plotmodel
        self.histo=h
        self.unsorted=True
        self.tree=tree
        self.name=name
        self.xname=xname if xname is not None else "channel"
        self.yname=yname if yname is not None else "counts per channel"
        self.fig=None
        self.calibration=Calibration()
        #print("plot object created")
        self.timer=Qt.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update)
        parent.bthread.finished.connect(self.stop_update)
   
    def openPlot(self):
        """
        Called from PlotTreeView to display the plot.
        Plots data corresponding to histogram.
        If sorting in progress, starts a timer to update plot at intervals.
        """
        h=self.histo
        fig=plt.figure(self.name)
        nfig=fig.number
        #print('fig',plt.get_fignums(),nfig, h.dims, self.unsorted)
        self.drawPlot(h)
        fig.canvas.draw_idle()
        if self.fig is None:
            if h.dims==2:
                from polygonlasso import MyLassoSelector
                ax=fig.gca()
                self.lasso=MyLassoSelector(ax,onselect,useblit=False)
                #print("lasso")
        self.fig=nfig
        fig.canvas.manager.window.closing.connect(self.closed)
        if self.unsorted: self.timer.start()

    def drawPlot(self,h):
        """
        Draw the plot on matplotlib canvas.
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
        """
        Return a calibrated x-axis for the plot.
        """
        x=None
        if 'NE213' not in self.tree.text():
            return x,xl
        calib=self.calibration
        try:
            # must compensate for histo size
            factor=1024//size  # -> divisor
            if adc==calib.EADC:
                m=calib.slope/factor
                c=calib.intercept/factor
                x=np.arange(0.0,float(size),1.0)
                x=(1.0/m)*x-c/m
                xl="Energy [MeVee]"
            elif adc==calib.TADC:
                m=calib.TAC/factor
                x=np.arange(0.0,float(size),1.0)
                x=x/m
                xl="T [ns]"              
        except:
                x=np.arange(0.0,float(size),1.0)
        return x, xl
        
    
    @pyqtSlot()
    def update(self):
        """
        Update the plot if timer is active (i.e. sorting active).
        """
        nfig=self.fig
        fig=plt.figure(nfig)
        plt.cla()
        self.drawPlot(self.histo)

    @pyqtSlot()
    def stop_update(self):
        """
        Stop updating plot when sorting done.
        """
        #print('fig',self.fig, ' end update')
        self.unsorted=False
        self.timer.stop()

    @pyqtSlot()
    def closed(self):
        """
        Stop timer when window closed.
        """
        self.timer.stop()

                
def SetupSort(parent):
    """
    Setup a sort of data
    This is hardwired here.
    At some point this will change; there should be some sort builder program.
    """
    #filepath="../../../All raw data and analyses from iTL neutrons 2009/100MeV/NE213/"
    #fileNE213="NE213_025.lst"  # 0deg natLi
    #fileNE213="NE213_026.lst"  # 0deg 12C 
    #fileNE213="NE213_028.lst"  # 16deg natLi
    #fileNE213="NE213_029.lst"  # 16deg 12C 

    filepicker=parent.filepick
    
    #infile=filepath+fileNE213
    infile=filepicker.files['NE213']
    print(infile)

    # check if spectrum calibrated
    calibration=Calibration()
    if(len(calibration.checkvars())==5):
        print("Spectrum is calibrated")

    cutL=2.5
    print("cutL at 2.5 Mev in ch ",calibration.channel(2.5))

    # check if TOF start position calculated
    """
    TOFadc=filepicker.editDefTOF.text()
    print("ADC for TOF is "+TOFadc)
    TOFTgamma=filepicker.editTgamma.text()
    try:
        Tgamma=float(TOFTgamma)
    except:
        print("Tgamma error")
        Tgamma=0.0
    """
    analysisdata=AnalysisData()
    Tgamma=analysisdata.Tgamma
    TOFStartSet=Tgamma != 0.0
    print("TOF Tgamma is ",Tgamma)

    # set up event source
    E=EventSource(infile)
    
    # define histograms
    h1=Histogram(E, GROUP_NE213, 'ADC1', 512)
    h2=Histogram(E, GROUP_NE213, 'ADC2', 512)
    h3=Histogram(E, GROUP_NE213, 'ADC3', 512)
    h4=Histogram(E, GROUP_MONITOR, 'ADC4', 512)
    h21=Histogram(E, GROUP_NE213, ('ADC1','ADC2'), (256,256),label=('L','S'))
    h13=Histogram(E, GROUP_NE213, ('ADC1','ADC3'), (256,256),label=('L','T'))
    histlist=[h1,h2,h3,h4,h21,h13]

    # define sort process
    S=Sorter( E, histlist)

    # create tree for plots widget
    tree=parent.plotmodel
    branch=tree.appendGroup( "NE213 data" )

    # create plot items 
    CreatePlot( parent, tree, branch, h1, "NE213 Adc 1" )
    CreatePlot( parent, tree, branch, h2, "NE213 Adc 2" )
    CreatePlot( parent, tree, branch, h3, "NE213 Adc 3" )
    CreatePlot( parent, tree, branch, h4, "NE213 Adc 4" )
    CreatePlot( parent, tree, branch, h21, "NE213 Adc1 v Adc2", xname="Long", yname="Short" )
    CreatePlot( parent, tree, branch, h13, "NE213 Adc1 v Adc3", xname="Long", yname="TOF" )

    return S

    """
    # some of this to be included in future
    sortadc=[]
    deadtimer=[]
    t0=time.perf_counter()
    """

def CreatePlot( parent, tree, branch, histo, name, xname=None, yname=None ):
    """
    Create a plot object and insert into plot tree.

    Parameters
    ----------
    parent : object
        Qt parent of plot, i.e. top level gui.
    tree : PlotTreeModel
        Tree into which plot is inserted.
    branch : tree node
        Branch in tree to which plot is linked.
    histo : Histogram
        Histogram to be plotted
    name : str
        Name user will see for histogram.
    """
    s=SpectrumPlotter( parent, histo, branch, name, xname=xname, yname=yname)
    tree.appendAt( branch, name, s)
    
    
def SortCallback(v0,v1,v2,v3,cutL):
    """
    Callback from sorter to perform calculated sorting
    i.e. use calibrated spectrum to calculate data to sort
    taken from sort-with-calib.py
    """
    Tcon=9.159*calTof/0.3
    T0=Tgamma+Tcon
    Tof=T0-v2+rand()-0.5   # calculate TOF and spread randomly over channel
    if v0<cutL: return
    h3t.increment([0,0,int(Tof),0])
    # if Tof too small to be n, ignore rest
    if v2>Tgamma2: return

    # calculate neutron energy from relativistic kinematics
    betan=Tcon/Tof
    if betan>= 1.0:
        print("sqrt",v2,betan,Tof)
        return
    En=939.565*(1.0/np.sqrt(1.0-betan*betan)-1.0)
    En=int(En*4+0.5)&1023
    
    #print(Tof,vn,En,int(Tof))
    #h1cut.increment(v)
    #h2cut.increment(v)
    hE.increment([0,0,En,0])
    #h3.increment(v)
    hv.increment([0,0,int(betan*1000.0+0.5),0])

class CalculatedEventSort(object):
    """
    Placeholder, not integrated with rest of code.
    """
    def __init__( self, calibration ):

        
        calibration=Calibration()
        data=AnalysisData()
        self.analysisdata=data
        speed_of_lightdata.speed_of_light # m/ns
        target_distance=data.target_distance # m , flight path target to detector
        slopeTof=calibration.TAC # TAC calibration in channel/ns
        choffset=target_distance*slopeTof/speed_of_light # channel offset due to flight path
        chT0=self.analysisdata.Tgamma*slopeTof + choffset # channel of gamma flash at detector
        self.chT0=T0 # keep copy
        self.choffset=choffset
        self.chTgamma2=self.chT0-5 # arbitrary cutoff
        self.cutL=calibration.channel(2.5) # convert to channel

    def sort(v0,v1,v2,v3):
        
        Tof=self.chT0-v2+rand()-0.5   # calculate TOF and spread randomly over channel
        if v0<self.cutL: return
        h3t.increment([0,0,int(Tof),0])
        # if Tof too small to be n, ignore rest
        if v2>self.chTgamma2: return

        # calculate neutron energy from relativistic kinematics
        betan=choffset/Tof
        if betan>= 1.0:
            print("sqrt",v2,betan,Tof)
            return
        En=939.565*(1.0/np.sqrt(1.0-betan*betan)-1.0)
        En=int(En*4+0.5)&1023

        #print(Tof,vn,En,int(Tof))
        #h1cut.increment(v)
        #h2cut.increment(v)
        hE.increment([0,0,En,0])
        #h3.increment(v)
        hv.increment([0,0,int(betan*1000.0+0.5),0])

def SetupFCSort(parent):
    """
    Setup a sort of fission chamber data
    This is hardwired here.
    At some point this will change; there should be some sort builder program.
    """
    filepicker=parent.filepick
    
    infile=filepicker.files['FC']

    # define event source
    E=EventSource(infile)

    # set up histograms
    h1=Histogram(E, GROUP_FC, 'ADC1', 512)
    h3=Histogram(E, GROUP_FC, 'ADC3', 512)
    h4=Histogram(E, GROUP_MONITOR, 'ADC4', 512)
    h13=Histogram(E, GROUP_FC, ('ADC1','ADC3'), (256,256),label=('L','T'))
    histlist=[h1,h3,h4,h13]

    # define sort task
    S=Sorter( E, histlist)

    # create tree for plots widget
    tree=parent.plotmodel
    branch=tree.appendGroup( "Fission Chamber" )
    
    # create plot items
    CreatePlot( parent, tree, branch, h1, "FC Adc 1")
    CreatePlot( parent, tree, branch, h3, "FC Adc 3")
    CreatePlot( parent, tree, branch, h4, "FC Adc 4")
    CreatePlot( parent, tree, branch, h13, "FC Adc1 v Adc3", xname="Long", yname="TOF")

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
    """
    Stream python logger output to a QtListView.

    Parameters
    ----------
    list : listview
        A listview for output.
    
    """
    def __init__(self, list):
        self.list=list

    def write(self,data):
        """
        Write data to list view.

        1) must remove line feed at end
        2) seems to be a spurious line feed coming through as well
        """
        if len(data)<=1: return
        if data[-1] in ['\r','\n']: data=data[0:-1]
        Qt.QListWidgetItem(data,self.list)

    def flush(self):
        pass

class NeutronAnalysisDemo(Qt.QMainWindow):
    """
    Main application container  widget

    Handles toolbar and status.
    """
    def __init__(self, *args):
        Qt.QMainWindow.__init__(self, *args)

        self.calibrator=None
        self.calibration=Calibration()
        d=AnalysisData()
        d.Tgamma=0.0
        """
        calibration values:
        Only the NE213 spectra are calibrated.
        Calibration is stored in a dict()
        The following keys are known:
        'EADC':      adc used for calibrating energy
        'TADC':      adc used for calibrating TOF
        'slope':     gamma calibration slope in channel/MeVee
        'intercept': gamma calibration intercept in channel
        'TAC':       TDC slope in ch/ns
        'Tgamma':    Time of gamma burst in raw TOF, used to calc T0 
        """
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

        
        self.btnAvge = Qt.QToolButton(toolBar)
        self.btnAvge.setText("data")
        #self.btnAvge.setIcon(Qt.QIcon(Qt.QPixmap(icons.avge)))
        self.btnAvge.setIcon(Qt.QIcon("drive.png"))
        #self.btnAvge.setCheckable(True)
        self.btnAvge.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnAvge)
        """
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
        self.plotview=PlotTreeView(self)
        self.plotmodel=PlotTreeModel(self)
        self.plotview.setModel(self.plotmodel)
        self.plotview.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        label=self.makeLabel("Plot list")
        vlayout.addWidget(label)
        vlayout.addWidget(self.plotview)
        vlayout.setContentsMargins(1,1,1,1) # cut down margins from 11px
        self.plotwidget.setLayout(vlayout)
        self.mainwin.addWidget(self.plotwidget)
                                  
        self.tasklist.doubleClicked.connect(self.runTask)
        self.filepick.fileChanged.connect(self.setFilePaths)
        self.filepick.valueChanged.connect(self.setFilePaths)
        self.btnFreeze.clicked.connect(self.openFile)
        self.btnMode.clicked.connect(self.saveFile)
        self.btnAvge.clicked.connect(self.saveDataAsHDF)
        self.bthread = None

    def makeLabel(self, title):
        """
        Centralize label creation here so all customisation in one place.

        Parameters
        ----------
        title : str
            Text of label.

        Returns
        -------
            label : A Qt label.
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
        Start a sort process.

        This will evolve to dispatch different sorts at various times.

        Parameters
        ----------
        setupsorter: function
            Function to set up the sort process.
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
        Quit background thread when sorting done.
        """
        #print("cleanup")
        self.bthread.quit()

    def runTask(self,p):
        """
        Placeholder...

        Run an analysis task.

        Should be replaced by something else when all tasks have been decided.

        Parameters
        ----------
        p : index
            A Qt index from task list indicating which task has been double
            clicked.
        """
        m=self.tasklist.itemFromIndex(p)
        sorttype=m.text()
        logger.info("Run task: "+sorttype)
        if sorttype=="Sort NE213":
            self.startSorting(SetupSort)
        elif sorttype=="Sort FC":
            self.startSorting(SetupFCSort)
        elif sorttype=="Calibrate":
            import calibrate as calibrator
            self.calibrator=calibrator.Calibrator(self.filepick.files['Na'],
                                             self.filepick.files['Cs'],
                                             self.filepick.files['AmBe'],
                                             self.filepick.files['TAC'])
            logger.info("Start sort for calibration")
            self.calibrator.sort()
            # create tree for plots widget
            tree=self.plotmodel
            branch=tree.appendGroup( "Calibration" )
            #item=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"calib")       
            self.calibplot=calibrator.CalibrationPlotter(self.calibrator)
            tree.appendAt(branch, "calib", self.calibplot)
            self.calibplot.openPlot()

    def updateCalibration(self):
        pass
        if self.calibrator is not None:
            self.calibration.update(self.calibrator.calibration)
        
    
    def openFile(self,p):
        """
        Read a file name from open file dialog.

        Parameters
        ----------
        p : ignored
        """
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
        """
        Save a file to file picked in save file dialog.

        Parameters
        ----------
        p : ignored
        """
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

    def saveDataAsHDF(self, p):
        """
        Save histogram data to hdf5 file.

        Parameters
        ----------
        p : ignored
        """
        #if self.filepick.files is None:
        #    logger.warn("Nothing to save")
        #    return
        import h5py
        def _savedata(path,sp):
            h=sp.histo
            if h.dims==1:
                print(path+"/data")
                dset=f.create_dataset(path+"/data",data=h.data)
                dset.attrs['type']="h1"
                dset.attrs['adc']=h.adc1
                dset.attrs['adcrange']=h.adcrange1
                dset.attrs['size']=h.size1
                dset.attrs['divisor']=h.divisor1
                print(h.adc1,h.size1,h.adcrange1,h.divisor1,len(h.data))
            elif h.dims==2:
                print(path+"/data")
                dset=f.create_dataset(path+"/data",data=h.data)
                dset.attrs['type']="h2"
                dset.attrs['adc1']=h.adc1
                dset.attrs['adc2']=h.adc2
                dset.attrs['adcrange1']=h.adcrange1
                dset.attrs['adcrange2']=h.adcrange2
                dset.attrs['size1']=h.size1
                dset.attrs['size2']=h.size2
                dset.attrs['divisor1']=h.divisor1
                dset.attrs['divisor2']=h.divisor2
                print(h.adc1,h.size1,h.adcrange1,h.divisor1,len(h.data))
        filename,_=Qt.QFileDialog.getSaveFileName(self,'Save file',
                                                  '.',"HDF Data File (*.hdf5)")
        if filename == '': return
        f=h5py.File(filename,"w")
        self.plotmodel.saveData(_savedata)

    @pyqtSlot('QString')
    @pyqtSlot(int)
    def setFilePaths(self, count):
        """
        Save files entered in text entry widgets.
        """
        if isinstance(count, int):
            print("filepaths int",count)
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
        elif isinstance(count, str):
            print("filepaths float",count)
            print("Tgamma from field",count)
            try:
                Tg=float(count)
                d=AnalysisData()
                print("d",d.Tgamma)
                d.Tgamma=Tg
                if 'TAC' in self.calibration.keys():
                    Tcon=d.target_distance/d.speed_of_light  # in ns
                    T0=Tg+Tcon
                    print("Tcon, T0=",Tcon,T0)
                    d.T0=T0
            except:
                logger.error("Tgamma is not a float")
        
            
    def printPlot(self):
        """
        Placeholder.
        """
        p = QPrinter()

if __name__=="__main__":        
    # Admire! 
    app = Qt.QApplication(sys.argv)
    demo=NeutronAnalysisDemo()
    demo.show()
    #demo.startSorting()
    sys.exit(app.exec_())
