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
    name  :    name given to histogram
    xname :    label for x axis
    yname :    label for y axis
    """
    def __init__( self, parent, h, name, xname, yname  ):
        super().__init__(parent=parent)
        self.plotmodel=parent.plotmodel
        self.histo=h
        self.name=name
        self.xname=xname
        self.yname=yname
        self.fig=None
        print("plot object created")
        parent.listview.doubleClicked.connect(self.doubleclickPlot)
        self.timer=Qt.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update)
        parent.bthread.finished.connect(self.stop_update)
       
    def insertPlot(self, parentitem):
        """
        insert plot repr into list view widget
        """
        plot=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),self.name)
        #self.plotmodel.appendRow(plot)
        parentitem.appendRow(plot)
        plot.setData(self)
   
    def doubleclickPlot(self,p):
        """
        handle double click signal from listview
        plot corresponding data
        """
        from polygonlasso import MyLassoSelector
        plot=self.plotmodel.itemFromIndex(p)
        s=plot.data()
        if s != self: return
        h=self.histo
        nfig=p.row()+1
        fig=plt.figure(nfig)
        print(plt.get_fignums(),nfig, h.dims)
        self.drawPlot(h)
        fig.canvas.draw_idle()
        if self.fig is None:
            if h.dims==2:
                ax=fig.gca()
                self.lasso=MyLassoSelector(ax,onselect,useblit=False)
                print("lasso")
            self.fig=nfig
            fig.canvas.manager.window.closing.connect(self.closed)
            self.timer.start()

    def drawPlot(self,h):
        """
        draw the plot on matplotlib canvas
        """
        if h.dims==1:
            data,yl,xl=h.get_plotdata()
            plt.plot(data,drawstyle='steps-mid')
            plt.ylabel(yl+' '+self.yname)
            plt.xlabel(self.xname)
        else:
            data,yl,xl=h.get_plotlabels()
            plt.imshow(data,origin='lower',vmax=2000)
            plt.xlabel(yl+' '+self.xname)
            plt.ylabel(xl+' '+self.yname)
    
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
        print('fig',self.fig, ' end update')
        self.timer.stop()

    @pyqtSlot()
    def closed(self):
        """
        stop timer when window closed
        """
        self.timer.stop()
        print('figs ',plt.get_fignums())
        print("Window closed ",'thread',self.parent().bthread.isRunning())

class SpectrumItemModel(Qt.QStandardItemModel):
    def __init__(self, parent):
        super().__init__(parent=parent)

    #def insertPlots(self, plotlist):
        

        
def SetupSort(parent):
    """
    Setup a sort of data
    This is hardwired here.
    At some point this will change; there should be some sort builder program.
    """
    infile="../../NE213 100 MeV data/NE213_010_100MeV_0deg.lst"
    #infile="../NE213 100 MeV data/NE213_019_137Cs.lst"
    #infile="../NE213 100 MeV data/NE213_017_22Na.lst"

    E=EventSource(infile)
    #G=E.eventstream()

    h1=Histogram(E, ADC1+ADC2+ADC3, 'ADC1', 512)
    h2=Histogram(E, ADC1+ADC2+ADC3, 'ADC2', 512)
    h3=Histogram(E, ADC1+ADC2+ADC3, 'ADC3', 512)
    h4=Histogram(E, ADC4, 'ADC4', 512)
    h21=Histogram(E, ADC1+ADC2+ADC3, ('ADC1','ADC2'), (256,256),label=('L','S'))

    histlist=[h1,h2,h3,h4,h21]
    S=Sorter( E, histlist)

    s1=SpectrumPlot( parent, h1, "adc 1", "channel", "counts per channel")
    s2=SpectrumPlot( parent, h2, "ADC 2", "channel", "counts per channel")
    s3=SpectrumPlot( parent, h3, "adc 3", "channel", "counts per channel")
    s4=SpectrumPlot( parent, h4, "adc 4", "channel", "counts per channel")
    s21=SpectrumPlot( parent, h21, "adc1 v adc2", "Long", "Short")

    model=parent.plotmodel
    rootitem=model.invisibleRootItem()
    treeitem=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"data sorted")
    model.appendRow(treeitem)
    s1.insertPlot(treeitem)
    s2.insertPlot(treeitem)
    s3.insertPlot(treeitem)
    s4.insertPlot(treeitem)
    s21.insertPlot(treeitem)

    return S

    """
    # some of this to be included in future
    sortadc=[]
    deadtimer=[]
    t0=time.perf_counter()
    """

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
        print("start task")
        # task.start() ?
        sortadc=self.task.start()
        print("end task")
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
        print("start task")
        # task.start() ?
        sortadc=self.sorter.sort()
        print("end task")
        self.finished.emit()
        
        # sort returns histogram data of adc distribution -- do something with it
        

# initial analysis tasks
analysis_tasks=["Calibrate","Sort"]

class NeutronAnalysisDemo(Qt.QMainWindow):
    """
    Application container  widget

    Handles toolbar and status.
    """
    def __init__(self, *args):
        Qt.QMainWindow.__init__(self, *args)

        self.freezeState = 0
        self.changeState = 0
        self.averageState = 0
        self.autocState = 0

        self.mainwin=Qt.QWidget(self)
        self.setGeometry(10,10,1024,768)
        self.setCentralWidget(self.mainwin)
        #self.setUnifiedTitleAndToolBarOnMac(True)
              
        self.stack=Qt.QDockWidget("Tasks",self)
        self.stack.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        self.tasklist=Qt.QListWidget(self.stack)
        self.tasklist.addItems(analysis_tasks)
        self.tasklist.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        self.stack.setWidget(self.tasklist)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.stack)
        
        self.dock=Qt.QDockWidget("Done",self)
        self.donelist=Qt.QListWidget(self.dock)
        self.donelist.addItems(["Done","Also"])
        self.donelist.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        self.dock.setWidget(self.donelist)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock)
 
        # example code taken from dualscopeN.py
        toolBar = Qt.QToolBar(self)
        self.addToolBar(toolBar)
        sb=self.statusBar()
        sbfont=Qt.QFont("Helvetica",12)
        sb.setFont(sbfont)
        sb.showMessage("Status=1")

        self.btnFreeze = Qt.QToolButton(toolBar)
        self.btnFreeze.setText("Button1")
        self.btnFreeze.setIcon(Qt.QIcon(Qt.QPixmap(icons.stopicon)))
        self.btnFreeze.setCheckable(True)
        self.btnFreeze.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnFreeze)

        self.btnPrint = Qt.QToolButton(toolBar)
        self.btnPrint.setText("Print")
        self.btnPrint.setIcon(Qt.QIcon(Qt.QPixmap(icons.print_xpm)))
        self.btnPrint.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnPrint)

        """
        self.btnMode = Qt.QToolButton(toolBar)
        self.btnMode.setText("fft")
        self.btnMode.setIcon(Qt.QIcon(Qt.QPixmap(icons.pwspec)))
        self.btnMode.setCheckable(True)
        self.btnMode.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnMode)

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
        self.plotmodel=SpectrumItemModel(self)#Qt.QStandardItemModel(self)
        self.plotdock=Qt.QDockWidget("Plots",self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plotdock)
        self.listview=Qt.QTreeView(self)
        #self.listview.setViewMode(Qt.QListView.IconMode)
        self.listview.setModel(self.plotmodel)
        self.listview.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        self.plotdock.setWidget(self.listview)
                                  
        # setup timer for plot updates
        self.timer=Qt.QTimer()
        self.timer.setInterval(2000)

        self.tasklist.doubleClicked.connect(self.filer)
        #self.btnFreeze.clicked.connect(self.filer)

    def startSorting(self):
        """
        start a sort process
        this will evolve to dispatch different sorts at various times
        """
        # setup sort in background
        self.bthread=Qt.QThread()
        S=SetupSort(self)
        bobj=BackgroundSort(S)
        bobj.moveToThread(self.bthread)
        self.bthread.started.connect(bobj.task)
        bobj.finished.connect(self.cleanupThread)
        self.bobj=bobj # keep reference
        
        # start sort
        self.bthread.start()
        print('thread',self.bthread.isRunning())

    @pyqtSlot()
    def cleanupThread(self):
        """
        quit background thread when sorting done
        """
        print("cleanup")
        self.bthread.quit()

    def filer(self,p):
        # placeholder...
        m=self.tasklist.itemFromIndex(p)
        print("enter filer",m.text())
        self.startSorting()
        """
        import calibrate as calibrator
        self.calib=calibrator.Calibrator(calibrator.infileNa,
                                         calibrator.infileCs,
                                         calibrator.infileAmBe,
                                         calibrator.infileTAC)
        self.calib.sort()
        self.calibplot=calibrator.CalibrationPlotter(self.calib)
        self.calibplot.plot_all_spectra()
        """
        #dlg=Qt.QFileDialog.getOpenFileNames(self,'Open file','.')
        #print(dlg)
        
    def printPlot(self):
        p = QPrinter()

# Admire! 
app = Qt.QApplication(sys.argv)
demo=NeutronAnalysisDemo()
demo.show()
#demo.startSorting()
sys.exit(app.exec_())
