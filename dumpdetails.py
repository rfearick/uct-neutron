#! /usr/bin/env python
"""
dumpdetails.py

diagnostic analysis of neutron list data files.

usage: dumpdetails.py [-h] [-v] [-s SEEK] [-n COUNT] [-r]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity
  -s SEEK, --seek SEEK  set start byte in file for scan
  -n COUNT, --count COUNT
                        set number of words to process
  -r, --raw             Dump raw data words

"""

import numpy as np

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-s", "--seek", type=int, help="set start byte in file for scan")
parser.add_argument("-n", "--count", type=int, help="set number of words to process")
parser.add_argument("-r", "--raw", help="Dump raw data words",
                    action="store_true")
args = parser.parse_args()


goseek=0
#goseek=84141556
# seek should have start of events as lower limit -- move at some stage !!!
if args.seek != None:
    print("seek to",args.seek)
    goseek=args.seek
if args.verbose:
    print("verbosity turned on")
if args.count:
    count=args.count
    print("Count set to", count)
else:
    count=50
    
    

verbose=args.verbose or args.raw
#goseek=0
#goseek=84141556
#goseek=args.seek




# list stream identifers
TIMER=64
PAD=128
RTC=16
# marker between timer events and adc events
SYNCHRON=0xff

# our identifier for adc events
ADCEVENT=1

# adc bitmap
ADC1=1
ADC2=2
ADC3=4
ADC4=8

# number of adcs
TOTALADCS=4


def getevent( adcs, padded):
    """
    read an adc event from stream and decode 
    data words are padded if odd number of adcs fired 
    """
    # (basically from maciej)
    # Check bits to see which adcs fired.
    # Normalize so only lowest bit set
    # Keep results in isadc[].
    adc1=adcs&ADC1
    adc2=(adcs&ADC2)//ADC2
    adc3=(adcs&ADC3)//ADC3
    adc4=(adcs&ADC4)//ADC4
    isadc=[adc1,adc2,adc3,adc4]
    Nadcs=adc1+adc2+adc3+adc4
    # unpack values. If adc did not fire, return zero.
    if padded:
        b=f.read(2)
        if verbose:
            print( "        pad :",b)
        if b!= b'\xff\xff':
            global keepb
            print("    Pad error",b,f.tell())
            print("    Event    ",keepb)
    values=[0,0,0,0]
    for i in range(TOTALADCS):
        if isadc[i]==1:
            b=f.read(2)
            if verbose:
                print( "        word:",b)
           # assemble ADC word
            ints=256*int(b[1])+int(b[0])
            # mask adc word to adcrange
            ints=ints&1023
            values[i]=ints
    return Nadcs,isadc,values

# currently file is hardwired here !!!
infile="../NE213 100 MeV data/NE213_010_100MeV_0deg.lst"
filepath="../../All raw data and analyses from iTL neutrons 2009/100MeV/NE213/"
filename="NE213_025.lst"
infile=filepath+filename
f=open(infile,"rb",buffering=81920)


l=[]        
for b in f:
    l.append(b)
    s=b.decode()
    if "[LISTDATA]" in s: # marker for start of data (end of header)
        break
print("Start of events at", f.tell())

if goseek != 0:
    f.seek(goseek)
    verbose=True

keepb=None
#for i in range(50):
wordcount=0
while 1:
    if verbose:
        wordcount+=1
        if wordcount>count:
            break
    b=f.read(4) # read 4 byte word
    if len(b)<4:
        print('stop',b)
        break
    #print(b)
    if args.raw: continue
    if b==b'\x00\x00\x00\x00':
        here=f.tell()
        if verbose:
            print("    Null event")
            print("    ",keepb,b,here)
        continue
    # event type is in b[3]
    etype=b[3]
    b0=b[0]
    if etype == TIMER:
        if verbose:
            print("   TIMER")
        else:
            pass
    elif etype == SYNCHRON:
    #                if b[0]!=0xff and b[1]!=0xff and b[2]!=0xff:
    #                if etype & b[0] & b[1] & b[2]!=SYNCHRON:
        if b != b'\xff\xff\xff\xff':
            here=f.tell()
            print("    Hmm. Markers are more complicated.")
            print("    ",keepb,b,here)
            f.seek(here-2)
        else:
            if verbose:
                print("    SYNCHRON")
    elif (etype & RTC) != 0:
        print("    RTC")
    else:
        keepb=b
        padded=etype&PAD != 0
        #if b[0]==0:
        #    print(b,v)
        #    #b=f.read(16)
        #    print(b,oldb)
        #    continue
        n,a,v=getevent(b0, padded)
        if verbose:
            print("    ADCEVENT",n,b0,v)
    keepb=b

