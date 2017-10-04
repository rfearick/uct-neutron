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

# Make 3 pairs of axes for spectra and their 1st derivatives, and one for
# calibrations.

f1=plt.figure(1,(8,8))
ax11=plt.subplot2grid( (4,4), (0,0),colspan=2)
ax12=plt.subplot2grid( (4,4), (1,0),colspan=2)
ax21=plt.subplot2grid( (4,4), (0,2),colspan=2)
ax22=plt.subplot2grid( (4,4), (1,2),colspan=2)
ax31=plt.subplot2grid( (4,4), (2,0),colspan=2)
ax32=plt.subplot2grid( (4,4), (3,0),colspan=2)
ax4 =plt.subplot2grid( (4,4), (2,2),colspan=2,rowspan=2)
plt.tight_layout()
plt.show()
