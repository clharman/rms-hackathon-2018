# -*- coding: utf-8 -*-
"""
Created on Fri Jul 20 11:38:10 2018

@author: Hack7
"""

import time
import numpy.random as rand
from PIL import Image

# core modules
import logging.config
import math
import pkg_resources

# 3rd party modules
import cfg_load
import gym
import numpy as np
import matplotlib.pyplot as plt
import sys

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
        self.probability_kill = 0.9
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
        num_threats_input = rand.randint(4,10)
        time_difficulty_input = rand.randint(1,3)
        threat_difficulty_input = rand.randint(1,3)
        magazine_difficulty_input = rand.randint(1,3)
        self.iGen = inputGenerator(num_threats_input,time_difficulty_input,threat_difficulty_input,magazine_difficulty_input)
        newParams = inputGenerator.GenRaidEnvParams(self.iGen)
        #print("Target Params are",newParams)
        self.rInc = newParams[0]
        self.thetaInc = newParams[1]
        self.MagSize = newParams[2]
        self.probability_kill = newParams[3]
        self.Angle = 0
        self.projCount = 0 # Ids for the projectiles
        
        self.viewer = None

        self.stateGrid = np.zeros((self.thetaInc,self.rInc,3))
        self.targets = []
        self.interceptors = []

        self.action_space = gym.spaces.Discrete(4)
        self.damageTaken = 0
        self.threatsKilled = 0
        self.simDone = False
        self.dictActions = { 0:'Shoot', 1:'Left', 2:'Right', 3:'Wait'}
        
        self.state = [self.stateGrid,self.Angle,self.MagSize,len(self.targets)]
        
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
        self.damageTaken = 0
        self.simTime = 0
        self.threatsKilled = 0
        
        # Setup the initial state
        for tar in self.targets:
            if tar.start_time == 0:
                tar.range = 0
                if not (tar.kind == 'Threat1' or tar.kind == 'Threat2'):
                    print("Unrecognized threat kind")
                else:
                    self.stateGrid[tar.location][0][self.targetDict[tar.kind]] = tar.id
        
        self.state = [self.stateGrid,self.Angle,self.Ammo,self.numThreats]
        
        # Return a long single dimension array version of state
        return np.append(np.reshape(self.stateGrid,-1),[self.Angle,self.Ammo, self.numThreats-self.threatsKilled])

    def step(self,action):
        curTime = self.simTime
        newTime = curTime+1
        #print("SimTime is now: ",newTime)
        for tar in self.targets:
            if tar.alive:
                curTheta = tar.location
                curRange = tar.range
                newRange = newTime*tar.speed - tar.start_time*tar.speed
                if newRange >= self.rInc:
                    self.stateGrid[curTheta][curRange][self.targetDict[tar.kind]] = 0
                    #print("You got hit!!!")
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
                #print("Took a shot, remaining ammo is:",self.Ammo)
            #else:
                #print("Can't shoot! Out of ammo!")
        elif self.dictActions[action] == 'Left':
            #tempAngle = self.Angle - 1
            # Wrap around
            #if tempAngle < 0:
            #    tempAngle = self.thetaInc -1
            self.Angle = (self.Angle - 1) % self.thetaInc
            #print("TURNED LEFT!")
        elif self.dictActions[action] == 'Right':
            #tempAngle = self.Angle + 1
            # Wrap around
            #if tempAngle >= self.thetaInc:
            #    tempAngle = 0
            self.Angle = (self.Angle + 1) % self.thetaInc
            #print("TURNED RIGHT!")
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
                        #print("HIT A TARGET!!!", HitTarId)
                    elif row[1] != 0:
                        HitTarId = row[1]
                        #print("HIT A TARGET!!!", HitTarId)
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
                                #print("Rand draw was: ",effect)
                                # Interceptor dies regardless of if the target dies
                                cept.alive = False
                                #print(self.stateGrid.shape, cept.location, cept.range, len(self.targetDict), cept.kind)
                                self.stateGrid[cept.location][cept.range][self.targetDict[cept.kind]] = 0
                                if effect < self.probability_kill:
                                    tar.alive = False
                                    self.stateGrid[tar.location][tar.range][self.targetDict[tar.kind]] = 0
                                    self.threatsKilled += 1
                                    #print("KILLED A TARGET!!!")
            

                
        
        self.simTime = newTime
        self.simDone = self.CheckDone()
        self.state = [self.stateGrid,self.Angle,self.Ammo]
        # Return a long single dimension array version of state
        # TODO: Try a reward for aiming toward a threat???? Really need render working to see if it does this already
        
        threatsKilled = self.threatsKilled

        linedUpWithThreat = np.any(self.stateGrid[:,self.Angle,0]) or np.any(self.stateGrid[:,self.Angle,1])

        self.reward = linedUpWithThreat * 0.5 + threatsKilled

        return np.append(np.reshape(self.stateGrid,-1),[self.Angle,self.Ammo, self.numThreats-self.threatsKilled]),self.reward,self.simDone, []
    #End of UpdateState

    def CheckDone(self):
        done = False
        lastStart = 0
        for tar in self.targets:
            lastStart = max(tar.start_time,lastStart)
        if self.simTime > lastStart+self.rInc+1:
            done = True
            #print("End of Wave! Here's how you did:")
            if self.threatsKilled == len(self.targets):
                print("RAID DEFEATED")
            else:
                print("Killed ", self.threatsKilled, " Out of ", len(self.targets), " targets")
            print(self.Ammo, " out of ", self.MagSize, " shots left")
                
        return done

    def PrintState(self,state):
        #print("The current gun angle is:")
        #print(self.Angle*30)
        print("The current sim state is:")
        print(state)
        
    def render(self):
        # Set up figure

        # Set up landscape
        theta = np.linspace(0, 360, num=self.thetaInc, endpoint=False)
        r = np.linspace(0, self.rInc, num=self.rInc, endpoint=False)
        plt.clf()
        ax = plt.subplot(111, projection='polar')
        ax.set_rticks(r)

        ax.set_thetagrids(theta)
        ax.grid(True)

        # Plot threats and interceptors
        t1s = np.where(self.stateGrid[:,:,0])
        t2s = np.where(self.stateGrid[:,:,1])
        ins = np.where(self.stateGrid[:,:,2])

        ax.plot(theta[t1s[0]]*np.pi/180, self.rInc - r[t1s[1]], 'rx')
        ax.plot(theta[t2s[0]]*np.pi/180, self.rInc - r[t2s[1]], 'r+')
        ax.plot(theta[ins[0]]*np.pi/180, self.rInc - r[ins[1]], 'bo')
        # Plot turret angle
        turret_length = 4
        ax.plot([theta[self.Angle]*np.pi/180, theta[self.Angle]*np.pi/180], [0, turret_length], 'k-')
        plt.title('%s killed. %s hits taken. %s angle index.' % (self.threatsKilled, self.damageTaken, self.Angle))
        plt.savefig('env.png')
        ax.set_rmax(r[-1]+1)
        plt.pause(0.0001)

    def renderFancy(self):
        
        # Open image files
        image_background = Image.open('TestImages\star-background.bmp')
        image_tie = Image.open('TestImages\TIEfighter2-fathead.bmp')
        image_xwing = Image.open('TestImages\X-Wing1.bmp')
        image_laser = Image.open('TestImages\laser.bmp')
    
        # Size for the targets
        basewidth_targ = 160
    
        # Size for the x_wing
        basewidth_gun = 220
        
        # Size for the laser projectile
        basewidth_laser = 100
    
        bg_w, bg_h = image_background.size
        bg_rad = int(min(bg_w/2,bg_h/2))
    
        # Compute stuff for the TIE image
        wpercent_tie = (basewidth_targ / float(image_tie.size[0]))
        hsize_tie = int((float(image_tie.size[1]) * float(wpercent_tie)))
        image_tie = image_tie.resize((basewidth_targ, hsize_tie), Image.ANTIALIAS)
        imgTie_w, imgTie_h = image_tie.size
    
        offset_tie = []
        for tar in self.targets:
            mod_rad = ((self.rInc - tar.range)/self.rInc)*bg_rad
            offset_vertical = int(mod_rad*math.cos(math.radians(tar.location*30))+(bg_h - imgTie_h)//2)
            offset_horizontal = int(mod_rad*math.sin(math.radians(tar.location*30))+(bg_w - imgTie_w)//2)
            offset_temp = (offset_horizontal, offset_vertical)
            offset_tie.append(offset_temp)
    
        # Compute stuff for the X-Wing image
        wpercent_xwing = (basewidth_gun / float(image_xwing.size[0]))
        hsize_xwing = int((float(image_xwing.size[1]) * float(wpercent_xwing)))
        image_xwing = image_xwing.resize((basewidth_gun, hsize_xwing), Image.ANTIALIAS)
        image_xwing = image_xwing.transpose(Image.ROTATE_180)
        image_xwing = image_xwing.rotate(-30*self.Angle-10)
        imgXwing_w, imgXwing_h = image_xwing.size
        
        offset_xwing = ((bg_w - imgXwing_w) // 2, (bg_h - imgXwing_h) // 2)
        
        # Stuff for the laser images
        wpercent_las = (basewidth_laser / float(image_laser.size[0]))
        hsize_las = int((float(image_laser.size[1]) * float(wpercent_las)))
        image_laser = image_laser.resize((basewidth_laser, hsize_las), Image.ANTIALIAS)
        imgLas_w, imgLas_h = image_laser.size
        
        offset_laser = []
        for cept in self.interceptors:
            mod_rad = ((cept.range - self.rInc)/self.rInc)*bg_rad
            offset_vertical = int(mod_rad*math.cos(math.radians(cept.location*30))+(bg_h - imgLas_h)//2)
            offset_horizontal = int(-1*mod_rad*math.sin(math.radians(cept.location*30))+(bg_w - imgLas_w)//2)
            offset_temp = (offset_horizontal, offset_vertical)
            offset_laser.append(offset_temp)

        image_temp = image_background
        image_temp.paste(image_xwing,offset_xwing)
        for i in range(len(self.targets)):
            if self.targets[i].alive:
                if self.simTime >= self.targets[i].start_time:
                    image_temp.paste(image_tie,offset_tie[i])
    
        for i in range(len(self.interceptors)):
            if self.interceptors[i].alive:
                image_laser_rot = image_laser.transpose(Image.ROTATE_90)
                image_temp.paste(image_laser_rot,offset_laser[i])
    
        image = image_temp
        image.save('TestImages\out.png')
        image.show()
        
if __name__ == "__main__":
    
    theSim = RaidEnv()
    
    curState = theSim.reset()
    
    theSim.PrintState(curState)
    for i in range(100):
        #time.sleep(1.000)
        
        if i == 2:
            out = theSim.step(0)
        elif i >= 3 and i < 7:
            out = theSim.step(2)
        elif i == 7:
            out = theSim.step(0)
        elif i == 8:
            out = theSim.step(0)
        elif i >= 10 and i < 13:
            out = theSim.step(2)
        elif i == 14:
            out = theSim.step(0)
        elif i >= 15 and i <22:
            out = theSim.step(1)
        elif i == 23 or i == 24 or i == 25:
            out = theSim.step(0)
        else:
            out = theSim.step(3)
        
        theSim.PrintState(out[0])
        
        if i % 3 == 0:
            theSim.render()
        
        if out[2]:
            break



print("End of Script")