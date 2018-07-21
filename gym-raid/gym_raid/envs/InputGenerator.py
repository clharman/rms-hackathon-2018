# -*- coding: utf-8 -*-
"""
Created on Sat Jul 21 13:21:43 2018

@author: Hack7
"""

# Input param generator
class inputGenerator:
    def __init__(self):
        pass
    
    def GenRaidEnvParams():
        RangeIncrements = 25
        ThetaIncrements = 12
        MagazineSize = 20
        
        return RangeIncrements,ThetaIncrements,MagazineSize
        
    def GenTargetEnvParams():
        NumberOfTargets = 4
        TargetStartTimes = [0,0,3,12]
        TargetStartLocations = [0,4,7,0]
        TargetType = ['Threat1','Threat2','Threat1','Threat1']
        
        return NumberOfTargets, TargetStartTimes,TargetStartLocations, TargetType
        