# -*- coding: utf-8 -*-
"""
Created on Fri Jul 20 11:38:10 2018

@author: Hack7
"""

import time
import numpy.random as rand

# core modules
import logging.config
import math
import pkg_resources

# 3rd party modules
import cfg_load
import gym
import numpy as np

path = 'config.yaml'  # always use slash in packages
filepath = pkg_resources.resource_filename('gym_raid', path)
config = cfg_load.load(filepath)
logging.config.dictConfig(config['LOGGING'])

# Projectile class for threats and projectiles
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

# Input param generator
# Levels are ints from 1 to 5
class inputGenerator():
    def __init__(self,num_threats=1,time_difficulty=1,threat_difficulty=1,magazine_difficulty=1):
        self.RangeIncrements = 25
        self.ThetaIncrements = 12
        self.probability_kill = 0.7
        self.num_threats = num_threats
        self.time_difficulty = time_difficulty
        self.threat_difficulty = threat_difficulty
        self.magazine_difficulty = magazine_difficulty

    def GenRaidEnvParams(self):
        # Number of bullets determined by pk, threat count, and difficulty (5 is basically impossible)
        self.MagazineSize = math.ceil((self.num_threats / self.probability_kill) * 5 / self.magazine_difficulty)

        return self.RangeIncrements, self.ThetaIncrements, self.MagazineSize, self.probability_kill
        
    def GenTargetEnvParams(self):

        TargetStartTimes = rand.randint(0, math.ceil(self.num_threats * (self.RangeIncrements/2) * 1 / self.time_difficulty), self.num_threats)
        TargetStartLocations = rand.randint(0, 12, self.num_threats)

        TargetType = []
        for i in rand.uniform(0,1,self.num_threats):
            if(i > self.threat_difficulty/10):
                TargetType.append('Threat1')
            else:
                TargetType.append('Threat2')
        
        return self.num_threats, TargetStartTimes,TargetStartLocations, TargetType

# Constructor takes
# RangeIncrements: int of the number of range (y) increments
# ThetaIncrements: int of the number of theta (x) increments
# NumTargets: 
# Target StartTimes
# Target StartLocations
# MagazineSize: int the maximum number of interceptors
#
class RaidEnv(gym.Env):
    
    def __init__(self):
        self.simTime = 0
        self.iGen = inputGenerator(5,1,1,1)
        newParams = inputGenerator.GenRaidEnvParams(self.iGen)
        self.rInc = newParams[0]
        self.thetaInc = newParams[1]
        self.MagSize = newParams[2]
        self.probability_kill = newParams[3]
        self.Angle = 0
        self.projCount = 0 # Ids for the projectiles
        
        self.stateGrid = np.zeros((self.thetaInc,self.rInc,3))
        self.targets = []
        self.interceptors = []

        self.action_space = gym.spaces.Discrete(4)
        self.damageTaken = 0
        self.threatsKilled = 0
        self.simDone = False
        self.dictActions = { 0:'Shoot', 1:'Left', 2:'Right', 3:'Wait'}
        
        self.state = [self.stateGrid,self.Angle,self.MagSize]
        
        #Intialize random number generator for consistency
        rand.seed(12)
    
    def reset(self):
        NumTargets, TarStartTimes, TarStartLocations, TarTypes = inputGenerator.GenTargetEnvParams(self.iGen)
        self.numThreats = NumTargets
        tars = []
        for i in range(self.numThreats):
            tars.append(Projectile(TarTypes[i],TarStartTimes[i],TarStartLocations[i],-1,self.projCount+1))
            self.projCount += 1
        self.targets = tars
        self.interceptors = []
        self.targetDict = {'Threat1':0,'Threat2':1,'Inter':2}
        self.Ammo = self.MagSize
        
        # Setup the initial state
        for tar in self.targets:
            if tar.start_time == 0:
                tar.range = 0
                if not (tar.kind == 'Threat1' or tar.kind == 'Threat2'):
                    print("Unrecognized threat kind")
                else:
                    self.stateGrid[tar.location][0][self.targetDict[tar.kind]] = tar.id
        
        self.state = [self.stateGrid,self.Angle,self.Ammo]
        
        # Return a long single dimension array version of state
        return np.append(np.reshape(self.stateGrid,-1),[self.Angle,self.Ammo])

    def step(self,action):
        curTime = self.simTime
        newTime = curTime+1
        print("SimTime is now: ",newTime)
        for tar in self.targets:
            if tar.alive:
                curTheta = tar.location
                curRange = tar.range
                newRange = newTime*tar.speed - tar.start_time*tar.speed
                if newRange >= self.rInc:
                    self.stateGrid[curTheta][curRange][self.targetDict[tar.kind]] = 0
                    print("You got hit!!!")
                    self.damageTaken += 1
                    tar.alive = False
                elif newRange >= 0: #TODO: This could result in threats stomping each other
                    self.stateGrid[curTheta][curRange][self.targetDict[tar.kind]] = 0
                    self.stateGrid[curTheta][newRange][self.targetDict[tar.kind]] = tar.id
                    tar.range = newRange
        
        for cept in self.interceptors:
            if cept.alive:
                curRange = cept.range
                newRange = (newTime - cept.start_time)*cept.speed + self.rInc - 1
                if newRange < 0:
                    self.stateGrid[cept.location][curRange][self.targetDict[cept.kind]] = 0
                    cept.alive = False
                else:
                    self.stateGrid[cept.location][curRange][self.targetDict[cept.kind]] = 0
                    self.stateGrid[cept.location][newRange][self.targetDict[cept.kind]] = cept.id
                    cept.range = newRange
        
        
        # Perform action
        if self.dictActions[action] == 'Shoot':
            if self.Ammo > 0:
                # Shooting means creating a new interceptor at current angle for the new time
                self.interceptors.append(Projectile('Inter',newTime,self.Angle,self.rInc-1,self.projCount+1))
                self.projCount += 1
                self.stateGrid[self.Angle][self.rInc-1][2] = self.projCount
                self.Ammo -= 1
                print("TOOK A SHOT!!!")
                print("Remaining ammo is:",self.Ammo)
            else:
                print("Can't shoot! Out of ammo!")
        elif self.dictActions[action] == 'Left':
            tempAngle = self.Angle - 1
            # Wrap around
            if tempAngle < 0:
                tempAngle = self.thetaInc -1
            self.Angle = tempAngle
            print("TURNED LEFT!")
        elif self.dictActions[action] == 'Right':
            tempAngle = self.Angle + 1
            # Wrap around
            if tempAngle >= self.thetaInc:
                tempAngle = 0
            self.Angle = tempAngle
            print("TURNED RIGHT!")
        elif self.dictActions[action] == 'Wait':
            pass
        else:
            print("ERROR: Gave an unexpected action.")
        
        # Check "hit" for theta in self.thetaInc (see if int has crossed target)
        for col in self.stateGrid:
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
                                effect = rand.uniform(0,1)
                                print("Rand draw was: ",effect)
                                # Interceptor dies regardless of if the target dies
                                cept.alive = False
                                self.state[cept.location][cept.range][self.targetDict[cept.kind]] = 0
                                if effect > self.probability_kill:
                                    tar.alive = False
                                    self.stateGrid[tar.location][tar.range][self.targetDict[tar.kind]] = 0
                                    self.threatsKilled += 1
                                    print("KILLED A TARGET!!!")
            

                
        
        self.simTime = newTime
        self.simDone = self.CheckDone()
        self.state = [self.stateGrid,self.Angle,self.Ammo]
        # Return a long single dimension array version of state
        self.reward = self.threatsKilled
        return np.append(np.reshape(self.stateGrid,-1),[self.Angle,self.Ammo]),self.reward,self.simDone, []
    #End of UpdateState

    def CheckDone(self):
        done = False
        lastStart = 0
        for tar in self.targets:
            lastStart = max(tar.start_time,lastStart)
        if self.simTime > lastStart+self.rInc+1:
            done = True
            print("End of Wave! Here's how you did:")
            if self.threatsKilled == len(self.targets):
                print("Congrats you defeated the wave!!!")
            else:
                print("You failed to defeat the wave.")
                print("There were",len(self.targets),"targets and you killed",self.threatsKilled)
                print("and you got hit",self.damageTaken,"times.")
                
        return done

    def PrintState(self,state):
        #print("The current gun angle is:")
        #print(self.Angle*30)
        print("The current sim state is:")
        print(state)

if __name__ == "__main__":
    RangeNumPixels = 25
    ThetaNumPixels = 12
    NumberOfTargets = 4
    TargetStartTimes = [0,0,3,12]
    TargetStartLocations = [0,4,7,0]
    TargetType = ['Threat1','Threat2','Threat1','Threat1']
    MaxAmmo = 20
    
    theSim = RaidEnv()
    
    curState = theSim.reset()
    
    theSim.PrintState(curState)
    for i in range(max(TargetStartTimes)+30):
        #time.sleep(1.000)
        
        if i == 2:
            out = theSim.step("Shoot")
        elif i >= 3 and i < 7:
            out = theSim.step("Right")
        elif i == 7:
            out = theSim.step("Shoot")
        elif i == 8:
            out = theSim.step("Shoot")
        elif i >= 10 and i < 13:
            out = theSim.step("Right")
        elif i == 14:
            out = theSim.step("Shoot")
        elif i >= 15 and i <22:
            out = theSim.step("Left")
        elif i == 23 or i == 24 or i == 25:
            out = theSim.step("Shoot")
        else:
            out = theSim.step("Wait")
        
        theSim.PrintState(out[0])
        if out[2]:
            break



print("End of Script")