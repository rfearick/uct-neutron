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
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
#from numpy import arange, sin, pi
import matplotlib
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.figure import Figure



import icons    # part of this package -- toolbar icons

import time

count=0

def InsertPlot(model, h, name):
    plot=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),name)
    model.appendRow(plot)
    plot.setData(h)
   

def SetupSort(model):
    infile="../../NE213 100 MeV data/NE213_010_100MeV_0deg.lst"
    #infile="../NE213 100 MeV data/NE213_019_137Cs.lst"
    #infile="../NE213 100 MeV data/NE213_017_22Na.lst"

    E=EventSource(infile)
    G=E.eventstream()

    h1=Histogram(E, ADC1+ADC2+ADC3, 'ADC1', 512)
    h2=Histogram(E, ADC1+ADC2+ADC3, 'ADC2', 512)
    h3=Histogram(E, ADC1+ADC2+ADC3, 'ADC3', 512)
    h4=Histogram(E, ADC4, 'ADC4', 512)
    #print(len(h2.data), h2.adc1,h2.divisor1, h2.adcrange1, h2.index1, h2.size1)
    h21=Histogram(E, ADC1+ADC2+ADC3, ('ADC1','ADC2'), (256,256),label=('L','S'))
    #print(np.shape(h21.data), h21.adc1,h21.divisor1, h21.adcrange1, h21.index1, h21.size1)
    #print(np.shape(h21.data), h21.adc2,h21.divisor2, h21.adcrange2, h21.index2, h21.size2)
    histlist=[h1,h2,h3,h4,h21]
    S=Sorter( E, histlist)

    InsertPlot(model, h1, "adc 1")
    InsertPlot(model, h2, "ADC 2")
    InsertPlot(model, h3, "Adc 3")
    InsertPlot(model, h4, "Adc 4")
    InsertPlot(model, h21, "2d")

    return S
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





class Backgd(Qt.QObject):

    def __init__(self, sorter):
        super().__init__()
        self.sorter = sorter
    

    def task(self):
        self.sorter.sort()
        

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

        

        toolBar = Qt.QToolBar(self)
        self.addToolBar(toolBar)
        sb=self.statusBar()
        sbfont=Qt.QFont("Helvetica",12)
        sb.setFont(sbfont)
        sb.showMessage("Status=1")

        self.btnFreeze = Qt.QToolButton(toolBar)
        self.btnFreeze.setText("Freeze")
        self.btnFreeze.setIcon(Qt.QIcon(Qt.QPixmap(icons.stopicon)))
        self.btnFreeze.setCheckable(True)
        self.btnFreeze.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnFreeze)

        self.btnPrint = Qt.QToolButton(toolBar)
        self.btnPrint.setText("Print")
        self.btnPrint.setIcon(Qt.QIcon(Qt.QPixmap(icons.print_xpm)))
        self.btnPrint.setToolButtonStyle(Qt.Qt.ToolButtonTextUnderIcon)
        toolBar.addWidget(self.btnPrint)

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

        self.plotmodel=Qt.QStandardItemModel(self)
        #self.plot1=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"Plot 1")
        #self.plotmodel.appendRow(self.plot1)
        #self.plot2=Qt.QStandardItem(Qt.QIcon(Qt.QPixmap(icons.pwspec)),"Plot 2")
        #self.plot1.setData(256)
        #self.plotmodel.appendRow(self.plot2)
        plotdock=Qt.QDockWidget("Plots",self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, plotdock)
        self.listview=Qt.QListView(self)
        self.listview.setViewMode(Qt.QListView.IconMode)
        self.listview.setModel(self.plotmodel)
        self.listview.setDragDropMode(Qt.QAbstractItemView.InternalMove)
        plotdock.setWidget(self.listview)

        S=SetupSort(self.plotmodel)
        self.bthread=Qt.QThread()
        bobj=Backgd(S)
        bobj.moveToThread(self.bthread)
        self.bthread.started.connect(bobj.task)
                                   

        self.timer=Qt.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.increment)
        self.bthread.start()
        ###self.timer.start()

        self.btnMode.clicked.connect(self.filer)
        self.listview.doubleClicked.connect(self.doubleclickPlot)

    def increment(self):
        global count
        s="%d"%(count,)
        print(s)
        self.donelist.addItems([s])

    def filer(self):
        print("enter filer")
        dlg=Qt.QFileDialog.getOpenFileNames(self,'Open file','.')
        print(dlg)
        

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

    def printPlot(self):
        p = QPrinter()

    def doubleclickPlot(self,p):
        plot=self.plotmodel.itemFromIndex(p)
        h=plot.data()
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
        plt.show()
        #sc = MyStaticMplCanvas(self, h, width=5, height=4, dpi=100)
        #self.dock.setWidget(sc)
        #print(p.row(),p.column(),n)
        #pass
                                         
                                         
        


# Admire! 
app = Qt.QApplication(sys.argv)
demo=NeutronAnalysisDemo()
demo.show()
sys.exit(app.exec_())
