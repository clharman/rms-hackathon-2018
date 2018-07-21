# -*- coding: utf-8 -*-
"""
Created on Fri Jul 20 11:38:10 2018

@author: Hack7
"""

import numpy as np
import time
import random as rand

class Projectile:
    def __init__(self,kind,start,loc,rng,Id):
        self.start_time = start
        self.location = loc #Theta location
        self.range = rng #Range location
        self.kind = kind
        self.id = Id
        self.alive = True
        speed = 0
        if kind == 'Threat1':
            speed = 1
        elif kind == 'Threat2':
            speed = 2
        elif kind == 'Inter':
            speed = -1
        self.speed = speed


# Constructor takes
# RangeIncrements: int of the number of range (y) increments
# ThetaIncrements: int of the number of theta (x) increments
# NumTargets: 
# Target StartTimes
# Target StartLocations
# MagazineSize: int the maximum number of interceptors
#
class SimpSim:
    
    def __init__(self, RangeIncrements, ThetaIncremets, NumTargets, TarStartTimes, 
                 TarStartLocations, TarTypes, MagazineSize):
        self.simTime = 0
        self.rInc = RangeIncrements
        self.thetaInc = ThetaIncremets
        self.Ammo = MagazineSize
        self.Angle = 0
        self.projCount = 0 # Ids for the projectiles
        
        self.state = np.zeros((self.thetaInc,self.rInc,3))
        
        self.numThreats = NumTargets
        tars = []
        for i in range(self.numThreats):
            tars.append(Projectile(TarTypes[i],TarStartTimes[i],TarStartLocations[i],-1,self.projCount+1))
            self.projCount += 1
        self.targets = tars
        self.interceptors = []
        self.targetDict = {'Threat1':0,'Threat2':1,'Inter':2}
        
        # Setup the initial state
        for tar in self.targets:
            if tar.start_time == 0:
                tar.range = 0
                if tar.kind == 'Threat1':
                    self.state[tar.location][0][0] = tar.id
                elif tar.kind == 'Threat2':
                    self.state[tar.location][0][1] = tar.id
                else:
                    print("Unrecognized threat kind")
                    
        self.damageTaken = 0
        self.threatsKilled = 0
        
        #Intialize random number generator for consistency
        rand.seed(12)
    
    def GetSimState(self):
        return self.state

    def UpdateState(self,action):
        curTime = self.simTime
        newTime = curTime+1
        print("SimTime is now: ",newTime)
        for tar in self.targets:
            if tar.alive:
                curTheta = tar.location
                curRange = tar.range
                newRange = newTime*tar.speed - tar.start_time*tar.speed
                if newRange >= self.rInc:
                    self.state[curTheta][curRange][self.targetDict[tar.kind]] = 0
                    print("You got hit!!!")
                    self.damageTaken += 1
                    tar.alive = False
                elif newRange >= 0: #TODO: This could result in threats stomping each other
                    self.state[curTheta][curRange][self.targetDict[tar.kind]] = 0
                    self.state[curTheta][newRange][self.targetDict[tar.kind]] = tar.id
                    tar.range = newRange
        
        for cept in self.interceptors:
            if cept.alive:
                curRange = cept.range
                newRange = (newTime - cept.start_time)*cept.speed + self.rInc - 1
                if newRange < 0:
                    self.state[cept.location][curRange][self.targetDict[cept.kind]] = 0
                    cept.alive = False
                else:
                    self.state[cept.location][curRange][self.targetDict[cept.kind]] = 0
                    self.state[cept.location][newRange][self.targetDict[cept.kind]] = cept.id
                    cept.range = newRange
        
        
        # Perform action
        if action == "Shoot":
            if self.Ammo > 0:
                # Shooting means creating a new interceptor at current angle for the new time
                self.interceptors.append(Projectile('Inter',newTime,self.Angle,self.rInc-1,self.projCount+1))
                self.projCount += 1
                self.state[self.Angle][self.rInc-1][2] = self.projCount
                self.Ammo -= 1
                print("TOOK A SHOT!!!")
                print("Remaining ammo is:",self.Ammo)
            else:
                print("Can't shoot! Out of ammo!")
        elif action == "Left":
            tempAngle = self.Angle - 1
            # Wrap around
            if tempAngle < 0:
                tempAngle = self.thetaInc -1
            self.Angle = tempAngle
            print("TURNED LEFT!")
        elif action == "Right":
            tempAngle = self.Angle + 1
            # Wrap around
            if tempAngle >= self.thetaInc:
                tempAngle = 0
            self.Angle = tempAngle
            print("TURNED RIGHT!")
        else:
            pass
        
        # Check "hit" for theta in self.thetaInc (see if int has crossed target)
        for col in self.state:
            IntIdsFound = []
            HitTarId = 0
            for row in col:
                if row[2] != 0:
                    IntIdsFound.append(row[2])
                if len(IntIdsFound) > 0:
                    if row[0] != 0:
                        HitTarId = row[0]
                        print("HIT A TARGET!!!")
                    elif row[1] != 0:
                        HitTarId = row[1]
                        print("HIT A TARGET!!!")
                if HitTarId != 0:
                    break
            
            if HitTarId != 0:
                for cept in self.interceptors:
                    for tar in self.targets:
                        for ID in IntIdsFound:
                            #Check current interceptor and target for the ones that collided
                            # also make sure target wasn't killed by a previous shot
                            if ID == cept.id and HitTarId == tar.id and tar.alive:
                                effect = rand.random()
                                print("Rand draw was: ",effect)
                                # Interceptor dies regardless of if the target dies
                                cept.alive = False
                                self.state[cept.location][cept.range][self.targetDict[cept.kind]] = 0
                                if effect > 0.3:
                                    tar.alive = False
                                    self.state[tar.location][tar.range][self.targetDict[tar.kind]] = 0
                                    self.threatsKilled += 1
                                    print("KILLED A TARGET!!!")
            

                
        
        self.simTime = newTime


    def CheckWin(self):
        print("End of Wave! Here's how you did:")
        if self.threatsKilled == len(self.targets):
            print("Congrats you defeated the wave!!!")
        else:
            print("You failed to defeat the wave.")
            print("There were",len(self.targets),"targets and you killed",self.threatsKilled)
            print("and you got hit",self.damageTaken,"times.")

    def PrintState(self):
        print("The current gun angle is:")
        print(self.Angle*30)
        print("The current sim state is:")
        print(self.state)

if __name__ == "__main__":
    RangeNumPixels = 25
    ThetaNumPixels = 12
    NumberOfTargets = 4
    TargetStartTimes = [0,0,3,12]
    TargetStartLocations = [0,4,7,0]
    TargetType = ['Threat1','Threat2','Threat1','Threat1']
    MaxAmmo = 20
    
    theSim = SimpSim(RangeNumPixels,ThetaNumPixels,NumberOfTargets,TargetStartTimes,
                     TargetStartLocations, TargetType, MaxAmmo)
    
    theSim.PrintState()
    for i in range(max(TargetStartTimes)+27):
        time.sleep(1.000)
        
        if i == 2:
            theSim.UpdateState("Shoot")
        elif i >= 3 and i < 7:
            theSim.UpdateState("Right")
        elif i == 7:
            theSim.UpdateState("Shoot")
        elif i == 8:
            theSim.UpdateState("Shoot")
        elif i >= 10 and i < 13:
            theSim.UpdateState("Right")
        elif i == 14:
            theSim.UpdateState("Shoot")
        elif i >= 15 and i <22:
            theSim.UpdateState("Left")
        elif i == 23 or i == 24 or i == 25:
            theSim.UpdateState("Shoot")
        else:
            theSim.UpdateState("Wait")
        
        theSim.PrintState()
        
    theSim.CheckWin()


print("End of Script")