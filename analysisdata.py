"""
Create singleton  to implement data holding classes
see:
http://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html

Implement classes to hold data for calibration and analysis constants.

Only a single instance of a class is created so we encapsulate global data
"""

class Singleton(type):
    """
    metaclass for single instance classes
    """
    instance=None
    def __call__(cls, *args, **kw):
        if not cls.instance:
            cls.instance=super(Singleton,cls).__call__(*args,**kw)
        return cls.instance


class Calibration(object, metaclass=Singleton):
    """
    Data for calibration:

    EADC            -- ADC used for energy calibration
    TADC            -- ADC used for TDC calibration
    slope           -- slope of gamma calibration in channel/MeVee
    intercept       -- intercept of gamma calibration in channel
    TAC             -- TDC slope in ch/ns
    Tgamma          -- time in nsof gamma flash in raw TOF spectrum, used for TOF zero
    calibration_gain-- gain increase used for gamma calibration
    TAC_interval    -- spacing in ns of peaks from TAC calibrator setting 
    """
    
    __slots__=['EADC','TADC','slope','intercept','TAC','Tgamma','calibration_gain',
               'TAC_interval']

    def __init__(self):
        pass

class AnalysisData(object, metaclass=Singleton):
    """
    Data needed for analysis:

    speed_of_light        -- in m/ns
    target_distance       -- distance target to detector, in m
    target_distance_in_ch -- target distance in channels in TOF spectrum
    T0_in_ch              -- channel corresponding to T0 in TOF spectrum
    """
    
    #__slots__=['speed_of_light','target_distance','target_distance_in_ch',
    #           'T0_in_ch' ]
    
    def __init__(self):
        pass
