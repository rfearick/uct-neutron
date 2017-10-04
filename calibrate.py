# for mac
import matplotlib
matplotlib.use("Qt5Agg")

from eventlist import *

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import MultiCursor
from scipy.stats import linregress


"""
Calibrate neutron detector using gamma ray sources.

Calibration mainly uses Compton edges, and first escape peak (12C) of AmBe source.

Energies: 
   22Na      1.062 MeV
  137Cs      0.477 MeV
   12C       3.42, 4.20 MeV  (AmBe source0

Differentiating the spectrum and choosing the lowest point in the region of the 
Compton edge seems to work well enough for scintillation detectors.
See Safari et al., ArXiv 1610.09185

This simple demo presents 3 different calibration spectra and allows the user
to select the calibration points. When all calibration points are selected, the 
calibration is calculated via linear regression, and plotted in a 4th view.
"""

# use 3 calibration runs for demo, for 3 sources.
infileCs="../NE213 100 MeV data/NE213_019_137Cs.lst"
infileNa="../NE213 100 MeV data/NE213_017_22Na.lst"
infileAmBe="../NE213 100 MeV data/NE213_020_AmBe.lst"

# define event sources
ENa=EventSource(infileNa)
ECs=EventSource(infileCs)
EAmBe=EventSource(infileAmBe)

# get event generators
GNa=ENa.eventstream()
GCs=ECs.eventstream()
GAmBe=EAmBe.eventstream()

# define histograms; use fake adc4 to avoid problem in currently buggy eventlist.py
htmp=Histogram(ENa, ADC4, 'ADC4', 512, label="22Na")

hNa=Histogram(ENa, ADC1+ADC2+ADC3, 'ADC1', 512, label="22Na")
hCs=Histogram(ECs, ADC1+ADC2+ADC3, 'ADC1', 512, label="137Cs")
hAmBe=Histogram(EAmBe, ADC1+ADC2+ADC3, 'ADC1', 512, label='AmBe')

# sort data. eventually must make multistream sorter!
SNa=Sorter(ENa, [hNa,htmp] )
sortadc=SNa.sort()

htmp=Histogram(ECs, ADC4, 'ADC4', 512, label="22Na")

SCs=Sorter(ECs, [hCs,htmp] )
sortadc=SCs.sort()

htmp=Histogram(EAmBe, ADC4, 'ADC4', 512, label="22Na")

SAmBe=Sorter(EAmBe, [hAmBe,htmp] )
sortadc=SAmBe.sort()

# calibration data
chans=[None,None,None,None]
edges=[1.062,0.477,3.42,4.20]

# define callbacks for matplotlib multicursor
def pos_callback(event):
    """
    read position in data coords when mouse button clicked.
    put data into chan array at correct index.
    when all 4 data points, calibrate and plot line 
    """
    print(event.inaxes)
    ax=event.inaxes
    if ax in axesgroup1:
        currentaxes=axesgroup1
        chans[0]=event.xdata
    elif ax in axesgroup2:
        currentaxes=axesgroup2
        chans[1]=event.xdata
    elif ax in axesgroup3:
        currentaxes=axesgroup3
        if chans[2]==None:
            chans[2]=event.xdata
        elif chans[3]==None:
            chans[3]=event.xdata
    else:
        return
    currentaxes[0].axvline(event.xdata)
    currentaxes[1].axvline(event.xdata)
    if chans[0] is not None and chans[1] is not None and chans[2] is not None and chans[3] is not None:
        if chans[2]>chans[3]:
            c3=chans[2]
            c2=chans[3]
            chans[2]=c2
            chans[3]=c3
        slope, intercept,r,p,stderr=linregress(edges,chans)
        print("slope,intercept",slope,intercept)
        xt=np.linspace(0.0,5.0,100.0)
        #plt.figure(4)
        ax4.plot(edges,chans,'bo')
        ax4.plot(xt,intercept+xt*slope)
        plt.draw()

    print(event.xdata)

def fig_callback(event):
    """
    Connect button click to active axes.
    """
    global fcur, cid_multi, multi
    print("enter",event.canvas)
    c=event.canvas
    
cid_multi=None
fcur=None


# Make 3 pairs of axes for spectra and their 1st derivatives, and one for
# calibrations.

f1=plt.figure(1,(8,8))
ax11=plt.subplot2grid( (4,4), (0,0),colspan=2)
data,yl,xl=hNa.get_plotlabels()
plt.plot(data,drawstyle='steps-mid')
plt.ylabel(yl)
plt.xlabel("channel")
plt.xlim(0,150)
ax12=plt.subplot2grid( (4,4), (1,0),colspan=2)
diffdata=data[1:]-data[0:-1]
plt.plot(diffdata,drawstyle='steps-mid')
plt.ylabel(yl)
plt.xlabel("channel")
plt.xlim(0,150)
#plt.ylim(-200,200)
axesgroup1=(ax11,ax12)
multi1 = MultiCursor(f1.canvas, axesgroup1, color='r', lw=2,
                     horizOn=False, vertOn=True, useblit=False)

ax21=plt.subplot2grid( (4,4), (0,2),colspan=2)
data,yl,xl=hCs.get_plotlabels()
plt.plot(data,drawstyle='steps-mid')
plt.ylabel(yl)
plt.xlabel("channel")
plt.xlim(0,50)
ax22=plt.subplot2grid( (4,4), (1,2),colspan=2)
diffdata=data[1:]-data[0:-1]
plt.plot(diffdata,drawstyle='steps-mid')
plt.ylabel(yl)
plt.xlabel("channel")
plt.xlim(0,50)
#plt.ylim(-200,200)
axesgroup2=(ax21,ax22)
multi2 = MultiCursor(f1.canvas, axesgroup2, color='r', lw=2,
                    horizOn=False, vertOn=True, useblit=False)

ax31=plt.subplot2grid( (4,4), (2,0),colspan=2)
data,yl,xl=hAmBe.get_plotlabels()
plt.plot(data,drawstyle='steps-mid')
plt.ylabel(yl)
plt.xlabel("channel")
plt.xlim(50,150)
plt.ylim(0,2000)
ax32=plt.subplot2grid( (4,4), (3,0),colspan=2)
diffdata=data[1:]-data[0:-1]
plt.plot(diffdata,drawstyle='steps-mid')
plt.ylabel(yl)
plt.xlabel("channel")
plt.xlim(50,150)
plt.ylim(-200,200)
axesgroup3=[ax31,ax32]
multi3 = MultiCursor(f1.canvas, axesgroup3, color='r', lw=2,
                    horizOn=False, vertOn=True, useblit=False)

ax4 =plt.subplot2grid( (4,4), (2,2),colspan=2,rowspan=2)
plt.xlabel('Energy [MeV]')
plt.ylabel('Channel')
plt.tight_layout()


cid_multi=f1.canvas.mpl_connect('button_press_event',pos_callback)
cid1=f1.canvas.mpl_connect('axes_enter_event',fig_callback)
#cid2=f1.canvas.mpl_connect('axes_enter_event',fig_callback)
#cid3=f1.canvas.mpl_connect('axes_enter_event',fig_callback)


plt.show()
