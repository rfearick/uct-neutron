#!/usr/bin/env python

# working multithread pyqt5 code
# taken from develop/testbed3.py

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
plt.ion()

import icons    # part of this package -- toolbar icons
import time

count=0

class SpectrumPlot(Qt.QObject):
    def __init__( self, parent, h, name, xname, yname  ):
        super().__init__(parent=parent)
        #print('parentage',self.parent(),parent)
        #self.parent=parent
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
       
    def insertPlot(self, name):
        plot=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),name)
        self.plotmodel.appendRow(plot)
        plot.setData(self)
   
    def doubleclickPlot(self,p):
        plot=self.plotmodel.itemFromIndex(p)
        s=plot.data()
        if s != self: return
        h=self.histo
        print(p,plot,h)
        nfig=p.row()+1
        fig=plt.figure(nfig)
        print(plt.get_fignums())
        self.drawPlot(h)
        print(nfig, h.dims)
        fig.canvas.draw_idle()
        if self.fig is None:
            self.fig=nfig
            fig.canvas.manager.window.closing.connect(self.closed)
            self.timer.start()

    def drawPlot(self,h):
        if h.dims==1:
            data,yl,xl=h.get_plotdata()
            plt.plot(data,drawstyle='steps-mid')
            plt.ylabel(yl)
        else:
            data,yl,xl=h.get_plotlabels()
            plt.imshow(data,origin='lower',vmax=2000)
            plt.xlabel(yl)
            plt.ylabel(xl)
    
    @pyqtSlot()
    def update(self):
        nfig=self.fig
        fig=plt.figure(nfig)
        fig.clf()
        self.drawPlot(self.histo)

    @pyqtSlot()
    def stop_update(self):
        print('fig',self.fig, ' end update')
        self.timer.stop()

    @pyqtSlot()
    def closed(self):
        self.timer.stop()
        print(plt.get_fignums())
        print("Window closed")
        print('thread',self.parent().bthread.isRunning())
        
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
    G=E.eventstream()

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
    s21=SpectrumPlot( parent, h21, "adc 4", "Short", "Long")

    model=parent.plotmodel

    s1.insertPlot("adc 1")
    s2.insertPlot("ADC 2")
    s3.insertPlot("Adc 3")
    s4.insertPlot("Adc 4")
    s21.insertPlot("2d")

    return S

    """
    # some of this to be included in future
    sortadc=[]
    deadtimer=[]
    t0=time.perf_counter()
    # this section 100 s (macmini)
    # a few optimisations, now 96 s (macmini)
    sortadc=S.sort()
    plt.figure(1)
    data,yl,xl=h21.get_plotlabels()
    plt.imshow(data,origin='lower',vmax=2000)
    plt.xlabel(yl)
    plt.ylabel(xl)
    plt.figure(2)
    data,yl,xl=h2.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.figure(3)
    plt.hist(sortadc,bins=16,range=(0,15))
    plt.xlim(0,16)
    plt.ylabel('Adc distribution')
    plt.figure(4)
    data,yl,xl=h4.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.figure(5)
    data,yl,xl=h3.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    plt.figure(6)
    data,yl,xl=h1.get_plotdata()
    plt.plot(data,drawstyle='steps-mid')
    plt.ylabel(yl)
    """

class BackgroundSort(Qt.QObject):
    """
    Run sort in a background thread
    """
    finished=pyqtSignal()
    def __init__(self, sorter):
        super().__init__()
        self.sorter = sorter

    def task(self):
        print("start sort")
        sortadc=self.sorter.sort()
        print("end sort")
        self.finished.emit()
        
        # sort returns histogram data of adc distribution -- do something with it
        

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
        self.tasklist.addItems(["Calibrate","Sort"])
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
        self.plotmodel=Qt.QStandardItemModel(self)
        plotdock=Qt.QDockWidget("Plots",self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, plotdock)
        self.listview=Qt.QListView(self)
        self.listview.setViewMode(Qt.QListView.IconMode)
        self.listview.setModel(self.plotmodel)
        self.listview.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        plotdock.setWidget(self.listview)
                                  
        # setup timer for plot updates
        self.timer=Qt.QTimer()
        self.timer.setInterval(2000)
        ###self.timer.timeout.connect(self.increment)

        ###self.timer.start()

        self.btnFreeze.clicked.connect(self.filer)
        #self.listview.doubleClicked.connect(self.doubleclickPlot)

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
        print("cleanup")
        self.bthread.quit()

    def increment(self):
        global count
        s="%d"%(count,)
        print(s)
        self.donelist.addItems([s])

    def filer(self):
        print("enter filer")
        dlg=Qt.QFileDialog.getOpenFileNames(self,'Open file','.')
        print(dlg)
        
    """
    def mode(self, on):
        if on:
            self.changeState=1
            self.btnMode.setText("scope")
            self.btnMode.setIcon(Qt.QIcon(Qt.QPixmap(icons.scope)))
        else:
            self.changeState=0
            self.btnMode.setText("fft")
            self.btnMode.setIcon(Qt.QIcon(Qt.QPixmap(icons.pwspec)))
        if self.changeState==1:
            self.stack.setCurrentIndex(self.changeState)
        else:
            self.stack.setCurrentIndex(self.changeState)
    """
    
    def printPlot(self):
        p = QPrinter()

    @pyqtSlot()
    def doubleclickPlot(self,p):
        plot=self.plotmodel.itemFromIndex(p)
        s=plot.data()
        h=s.histo
        print(p,plot,h)
        nfig=p.row()+1
        plt.figure(nfig)
        if h.dims==1:
            data,yl,xl=h.get_plotdata()
            plt.plot(data,drawstyle='steps-mid')
            plt.ylabel(yl)
        else:
            data,yl,xl=h.get_plotlabels()
            plt.imshow(data,origin='lower',vmax=2000)
            plt.xlabel(yl)
            plt.ylabel(xl)
        #print(nfig, h.dims)
        plt.show()

# Admire! 
app = Qt.QApplication(sys.argv)
demo=NeutronAnalysisDemo()
demo.show()
demo.startSorting()
sys.exit(app.exec_())
