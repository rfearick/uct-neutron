# uct-neutron

This directory contains Python codes for analysing neutron data.

At some stage, some of these may be redone in C++ for efficiency.

Data are derived from ADCs fed to Fast/Comtec MPA3 multiparameter system.

Two types of files are important:

- lst files: Files with extension .lst.

  These are mixed text/binary files, written throughout the run.

  The file has a text header in MS ini format,
  followed by binary list data from adcs and timers.

  The list data is what we need to sort to generate the spectra for analysis.

  These files may be large.

- mpa files: Files with extension .mpa.

  These are text files with spectrum data, written after the run.

  The file has a text header in MS ini format, followed by spectrum data
  with one interger per line (channel).

  The header data contains the scalar data at the end of run; this is all
  we need.

## Analysis sequence

1. Assemble analysis runs. Gather all files needed, i.e.

   a. Calibration data. lst files for 22na, 137Cs, AmBe, TAC.
   b. Data runs. lst and mpa files for NE213, FC, 0deg, 16deg, etc.
   c. Note that the lst file contains scalar data at start of run;
      mpa file contains scalar data at end of run.

2. Do a calibration.

   Uses calibration.py

   Uses all four calibration lst files to calibrate L and T.

3. Initial sort of data file, without calibration.

   Uses eventlist.py and run-dependent sort.py

   This is needed to select T0 in the TOF spectrum and constants
   in the L vs. L+S spectrum.

   Should also set thresholds on 1-d spectra and gates on 2-d spectra.

4. Run a sort of data file with calibration and gates to generate required
   spectra.