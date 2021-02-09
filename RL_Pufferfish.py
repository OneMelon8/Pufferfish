#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# Imports
import math
import json
import random
import time
import uuid
import functools
from past.utils import old_div
from collections import namedtuple
from threading import Thread

from malmo import MalmoPython as Malmo

from MissionXmlUtils import *
from PathUtils import *

import sys
import matplotlib.pyplot as plt
import numpy as np
from numpy.random import randint

import gym, ray
from gym.spaces import Discrete, Box
from ray.rllib.agents import ppo



# Global configurations

# File path to the arena map folder
# Add your path into one of these, commenting/uncommenting might be easier
#ABSOLUTE_PATH_TO_MAP = "C:/One/UCI/Classes/CS175/Arena"  # one
ABSOLUTE_PATH_TO_MAP = "C:/Users/ericn/OneDrive/Desktop/UCI/CS175 project in ai/Arena" # eric
# ABSOLUTE_PATH_TO_MAP = "C:/Users/Tianshu Wang/Desktop/Arena" # tianshu

# Mission configurations
MISSION_COUNT = 5

EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

# Agent configurations
AGENT_NAMES = ["Puffer", "Fish"]
AGENT_SPAWNS = ["<Placement x=\"0.5\" y=\"64\" z=\"-26.5\" yaw=\"0\"/>", "<Placement x=\"0.5\" y=\"64\" z=\"27.5\" yaw=\"180\"/>"]
AGENT_EQUIPMENTS = [(0, 4), (0, 4)]  # (weapon, armor)

# Attack cooldown map
ATTACK_COOLDOWNS = {
    "SWORD": 0.6,
    "AXE": 1,
    "OTHER": 0.25
}

# Agent dynamic stats
AGENT_LOCATIONS = [[0, 0, 0], [0, 0, 0]]
AGENT_COOLDOWNS = [0, 0]
AGENT_JUST_ATTACKED = [0, 0]
AGENT_SHIELD_COOLDOWNS = [0, 0]
AGENT_WEAPONS = ["SWORD", "SWORD"]
AGENT_IS_SHIELDING = [False, False]
AGENT_HOTBAR = [0, 0]
AGENT_HEALTH = [20.0, 20.0]

# File path to the arena map folder
# Add your path into one of these, commenting/uncommenting might be easier
#ABSOLUTE_PATH_TO_MAP = "C:/One/UCI/Classes/CS175/Arena"  # neo
ABSOLUTE_PATH_TO_MAP = "C:/Users/ericn/OneDrive/Desktop/UCI/CS175 project in ai/Arena" # eric
# ABSOLUTE_PATH_TO_MAP = "" # tianshu


class PVPTrainer(gym.Env):
    def __init__(self, env_config):
        # Static Parameters
        self.max_episode_steps = 100
        self.log_frequency = 10            
        
        # Rllib Parameters
        #self.action_space = Discrete(len(self.action_dict))
        self.action_space = Box(-1, 1, shape=(3 , ), dtype=np.float32)
        self.observation_space = Box(0, 1, shape=(2 * self.obs_size * self.obs_size, ), dtype=np.float32)

        # Malmo Parameters
        self.agent_host = Malmo.AgentHost()

        # DiamondCollector Parameters
        self.obs = None
        self.allow_break_action = False
        self.episode_step = 0
        self.episode_return = 0
        self.returns = []
        self.steps = []
    def reset(self):
        """
        Resets the environment for the next episode.

        Returns
            observation: <np.array> flattened initial obseravtion
        """
        # Reset Malmo
        world_state = self.init_malmo()

        # Reset Variables
        self.returns.append(self.episode_return)
        current_step = self.steps[-1] if len(self.steps) > 0 else 0
        self.steps.append(current_step + self.episode_step)
        self.episode_return = 0
        self.episode_step = 0

        # Log
        if len(self.returns) > self.log_frequency + 1 and             len(self.returns) % self.log_frequency == 0:
            self.log_returns()

        # Get Observation
        self.obs, self.allow_break_action = self.get_observation(world_state)

        return self.obs
    def step(self, action):
        """
        Take an action in the environment and return the results.

        Args
            action: <int> index of the action to take

        Returns
            observation: <np.array> flattened array of obseravtion
            reward: <int> reward from taking action
            done: <bool> indicates terminal state
            info: <dict> dictionary of extra information
        """
        
        console.log(action)

        '''
        # Get Action
        
        #map the attack to either 0(negative) or 1(positive)
        if action[2] < 0:
            self.agent_host.sendCommand('move ' + str(action[0]))
            self.agent_host.sendCommand('turn ' + str(action[1]))
            self.agent_host.sendCommand('attack ' + str(0))
            
        elif self.allow_break_action:
            self.agent_host.sendCommand('move ' + str(0))
            self.agent_host.sendCommand('turn ' + str(0))
            self.agent_host.sendCommand('attack ' + str(1))
            time.sleep(2)
        '''
            
        self.episode_step += 1
        
        '''    
        if command != 'attack 1' or self.allow_break_action:
            self.agent_host.sendCommand(command)
            time.sleep(.2)
            
        '''
        #if action[2] < 0 or self.allow_break_action:
        #self.agent_host.sendCommand('move ' + str(action[0]))
        #self.agent_host.sendCommand('turn ' + str(action[1]))
        #self.agent_host.sendCommand('attack ' + str(action[2]))
        
        self.episode_step += 1
            
        # Get Observation
        world_state = self.agent_host.getWorldState()
        for error in world_state.errors:
            print("Error:", error.text)
        self.obs, self.allow_break_action = self.get_observation(world_state) 

        # Get Done
        done = not world_state.is_mission_running 

        # Get Reward
        reward = 0
        for r in world_state.rewards:
            reward += r.getValue()
        self.episode_return += reward

        return self.obs, reward, done, dict()
    def get_mission_xml(self):
        xml = f"""
        <?xml version="1.0" encoding="utf-8"?>
        <Mission
            xmlns="http://ProjectMalmo.microsoft.com"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <About>
                <Summary>Pufferfish</Summary>
            </About>
            <ServerSection>
                <ServerInitialConditions>
                    <Time>
                        <StartTime>6000</StartTime>
                        <AllowPassageOfTime>false</AllowPassageOfTime>
                    </Time>
                </ServerInitialConditions>
                <ServerHandlers>
                    <FileWorldGenerator src="{ABSOLUTE_PATH_TO_MAP}" forceReset="false"/>
                    <ServerQuitWhenAnyAgentFinishes/>
                </ServerHandlers>
            </ServerSection>
        """
        
        #agent puffer
        xml += f"""
        <AgentSection mode="Adventure">
            <Name>{AGENT_NAMES[0]}</Name>
            <AgentStart>
                {AGENT_SPAWNS[0]}
                {create_inventory(*AGENT_EQUIPMENTS[0])}
            </AgentStart>
            <AgentHandlers>
                <ContinuousMovementCommands turnSpeedDegs="360"/>
                <InventoryCommands/>
                <MissionQuitCommands/>
                <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="60" yrange="5" zrange="60"/>
                </ObservationFromNearbyEntities>
                <ObservationFromGrid>
                    <Grid name="blocks">
                        <min x="-5" y="0" z="-5"/>
                        <max x="5" y="0" z="5"/>
                    </Grid>
                </ObservationFromGrid>
                <ObservationFromRay/>
                <ObservationFromHotBar/>
                <ObservationFromFullStats/>
            </AgentHandlers>
        </AgentSection>
        """
        #agent fish
        xml += f"""
        <AgentSection mode="Adventure">
            <Name>{AGENT_NAMES[1]}</Name>
            <AgentStart>
                {AGENT_SPAWNS[1]}
                {create_inventory(*AGENT_EQUIPMENTS[1])}
            </AgentStart>
            <AgentHandlers>
                <ContinuousMovementCommands turnSpeedDegs="360"/>
                <InventoryCommands/>
                <MissionQuitCommands/>
                <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="60" yrange="5" zrange="60"/>
                </ObservationFromNearbyEntities>
                <ObservationFromGrid>
                    <Grid name="blocks">
                        <min x="-5" y="0" z="-5"/>
                        <max x="5" y="0" z="5"/>
                    </Grid>
                </ObservationFromGrid>
                <ObservationFromRay/>
                <ObservationFromHotBar/>
                <ObservationFromFullStats/>
            </AgentHandlers>
        </AgentSection>
        """

        xml += "</Mission>"
        return xml
    
    def init_malmo(self):
        """
        Initialize new malmo mission.
        """
        my_mission = Malmo.MissionSpec(self.get_mission_xml(), True)
        my_mission_record = Malmo.MissionRecordSpec()
        my_mission.requestVideo(800, 500)
        my_mission.setViewpoint(1)

        max_retries = 3
        my_clients = Malmo.ClientPool()
        my_clients.add(Malmo.ClientInfo('127.0.0.1', 10000)) # add Minecraft machines here as available

        for retry in range(max_retries):
            try:
                self.agent_host.startMission( my_mission, my_clients, my_mission_record, 0, 'DiamondCollector' )
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print("Error starting mission:", e)
                    exit(1)
                else:
                    time.sleep(2)

        world_state = self.agent_host.getWorldState()
        while not world_state.has_mission_begun:
            time.sleep(0.1)
            world_state = self.agent_host.getWorldState()
            for error in world_state.errors:
                print("\nError:", error.text)

        return world_state

    def get_observation(self, world_state):
        """
        Use the agent observation API to get a flattened 2 x 5 x 5 grid around the agent. 
        The agent is in the center square facing up.

        Args
            world_state: <object> current agent world state

        Returns
            observation: <np.array> the state observation
            allow_break_action: <bool> whether the agent is facing a diamond
        """
        obs = np.zeros((2 * self.obs_size * self.obs_size, ))
        allow_break_action = False

        while world_state.is_mission_running:
            time.sleep(0.3)
            world_state = self.agent_host.getWorldState()
            if len(world_state.errors) > 0:
                raise AssertionError('Could not load grid.')

            if world_state.number_of_observations_since_last_state > 0:
                # First we get the json from the observation API
                msg = world_state.observations[-1].text
                observations = json.loads(msg)

                # Get observation
                grid = observations['floorAll']
                for i, x in enumerate(grid):
                    obs[i] = x == 'diamond_ore' or x == 'lava'

                # Rotate observation with orientation of agent
                obs = obs.reshape((2, self.obs_size, self.obs_size))
                yaw = observations['Yaw']
                if yaw >= 225 and yaw < 315:
                    obs = np.rot90(obs, k=1, axes=(1, 2))
                elif yaw >= 315 or yaw < 45:
                    obs = np.rot90(obs, k=2, axes=(1, 2))
                elif yaw >= 45 and yaw < 135:
                    obs = np.rot90(obs, k=3, axes=(1, 2))
                obs = obs.flatten()

                allow_break_action = observations['LineOfSight']['type'] == 'diamond_ore'
                
                break

        return obs, allow_break_action

    def log_returns(self):
        """
        Log the current returns as a graph and text file

        Args:
            steps (list): list of global steps after each episode
            returns (list): list of total return of each episode
        """
        box = np.ones(self.log_frequency) / self.log_frequency
        returns_smooth = np.convolve(self.returns[1:], box, mode='same')
        plt.clf()
        plt.plot(self.steps[1:], returns_smooth)
        plt.title('PVP Trainer')
        plt.ylabel('Return')
        plt.xlabel('Steps')
        plt.savefig('returns.png')

        with open('returns.txt', 'w') as f:
            for step, value in zip(self.steps[1:], self.returns[1:]):
                f.write("{}\t{}\n".format(step, value)) 

if __name__ == "__main__":
    ray.init()
    trainer = ppo.PPOTrainer(env=PVPTrainer, config={
        'env_config': {},           # No environment parameters to configure
        'framework': 'torch',       # Use pyotrch instead of tensorflow
        'num_gpus': 0,              # We aren't using GPUs
        'num_workers': 0            # We aren't using parallelism
    })

'''
# Imports
import math
import json
import random
import time
import uuid
import functools
from past.utils import old_div
from collections import namedtuple
from threading import Thread

import MalmoPython as Malmo

from Pufferfish.MissionXmlUtils import *
from Pufferfish.PathUtils import *

# Global configurations

# File path to the arena map folder
# Add your path into one of these, commenting/uncommenting might be easier
ABSOLUTE_PATH_TO_MAP = "C:/One/UCI/Classes/CS175/Arena"  # one
ABSOLUTE_PATH_TO_MAP = "C:/Users/ericn/OneDrive/Desktop/UCI/CS175 project in ai/Arena" # eric
# ABSOLUTE_PATH_TO_MAP = "C:/Users/Tianshu Wang/Desktop/Arena" # tianshu

# Mission configurations
MISSION_COUNT = 5

EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

# Agent configurations
AGENT_NAMES = ["Puffer", "Fish"]
AGENT_SPAWNS = ["<Placement x=\"0.5\" y=\"64\" z=\"-26.5\" yaw=\"0\"/>", "<Placement x=\"0.5\" y=\"64\" z=\"27.5\" yaw=\"180\"/>"]
AGENT_EQUIPMENTS = [(0, 4), (0, 4)]  # (weapon, armor)

# Attack cooldown map
ATTACK_COOLDOWNS = {
    "SWORD": 0.6,
    "AXE": 1,
    "OTHER": 0.25
}

# Agent dynamic stats
AGENT_LOCATIONS = [[0, 0, 0], [0, 0, 0]]
AGENT_COOLDOWNS = [0, 0]
AGENT_JUST_ATTACKED = [0, 0]
AGENT_SHIELD_COOLDOWNS = [0, 0]
AGENT_WEAPONS = ["SWORD", "SWORD"]
AGENT_IS_SHIELDING = [False, False]
AGENT_HOTBAR = [0, 0]
AGENT_HEALTH = [20.0, 20.0]


# Generate mission XML
def get_mission_xml():
    xml = f"""
    <?xml version="1.0" encoding="utf-8"?>
    <Mission
        xmlns="http://ProjectMalmo.microsoft.com"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <About>
            <Summary>Pufferfish</Summary>
        </About>
        <ServerSection>
            <ServerInitialConditions>
                <Time>
                    <StartTime>6000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                </Time>
            </ServerInitialConditions>
            <ServerHandlers>
                <FileWorldGenerator src="{ABSOLUTE_PATH_TO_MAP}" forceReset="false"/>
                <ServerQuitWhenAnyAgentFinishes/>
            </ServerHandlers>
        </ServerSection>
    """

    for a in range(2):
        xml += f"""
        <AgentSection mode="Adventure">
            <Name>{AGENT_NAMES[a]}</Name>
            <AgentStart>
                {AGENT_SPAWNS[a]}
                {create_inventory(*AGENT_EQUIPMENTS[a])}
            </AgentStart>
            <AgentHandlers>
                <ContinuousMovementCommands turnSpeedDegs="360"/>
                <InventoryCommands/>
                <MissionQuitCommands/>
                <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="60" yrange="5" zrange="60"/>
                </ObservationFromNearbyEntities>
                <ObservationFromGrid>
                    <Grid name="blocks">
                        <min x="-5" y="0" z="-5"/>
                        <max x="5" y="0" z="5"/>
                    </Grid>
                </ObservationFromGrid>
                <ObservationFromRay/>
                <ObservationFromHotBar/>
                <ObservationFromFullStats/>
            </AgentHandlers>
        </AgentSection>
        """

    xml += "</Mission>"
    return xml


# Safe start mission
def start_mission(agent_host, mission, client_pool, mission_record, index, mission_id):
    print(f"Attempting to start mission #{index} with ID = {mission_id}...")
    wait_time = 0
    while True:
        try:
            agent_host.startMission(mission, client_pool, mission_record, index, mission_id)
            break
        except Malmo.MissionException as ex:
            error_code = ex.details.errorCode
            if error_code == Malmo.MissionErrorCode.MISSION_SERVER_WARMING_UP:
                print(f"Server not quite ready yet - waiting; wait time = {wait_time}")
                time.sleep(2)
                wait_time += 2
            elif error_code == Malmo.MissionErrorCode.MISSION_INSUFFICIENT_CLIENTS_AVAILABLE:
                print("Not enough available Minecraft instances running.")
                print(f"Will wait in case they are starting up; wait time = {wait_time}")
                time.sleep(2)
                wait_time += 2
            elif error_code == Malmo.MissionErrorCode.MISSION_SERVER_NOT_FOUND:
                print("Server not found - has the mission with role 0 been started yet?")
                print(f"Will wait and retry; wait time = {wait_time}")
                time.sleep(2)
                wait_time += 2
            else:
                print(f"Unknown error: {ex.message}")
                print("Waiting will not help here - bailing immediately.")
                exit(1)


def wait_for_start(agent_hosts):
    print(f"Waiting for all agents to ready up...")
    start_flags = [False for _ in range(2)]
    start_time = time.time()

    # Wait for at most 2 minutes
    while not all(start_flags) and time.time() - start_time < 120:
        start_flags = [agent.peekWorldState().has_mission_begun for agent in agent_hosts]
        time.sleep(0.1)

    # Timed out
    if time.time() - start_time >= 120:
        print("Timed out while waiting for mission to start - bailing.")
        exit(1)

    # Ready!
    print(f"All agents ready, mission start!")


def select_hotbar_slot(agent, index, slot: int):
    """
    Selects the hotbar slot for the agent

    Args:
        agent (agent): Malmo agent
        index (int): agent index
        slot (int): the target hotbar slot to select [0-8]
    """
    assert 0 <= slot <= 8, f"Expected inventory slot (0-8), got \"{slot}\""

    if slot == 0:
        AGENT_WEAPONS[index] = "SWORD"
    elif slot == 1:
        AGENT_WEAPONS[index] = "AXE"
    else:
        AGENT_WEAPONS[index] = "OTHER"

    agent.sendCommand(f"hotbar.{slot + 1} 1")
    agent.sendCommand(f"hotbar.{slot + 1} 0")

    AGENT_COOLDOWNS[index] = ATTACK_COOLDOWNS[AGENT_WEAPONS[1]]
    AGENT_HOTBAR[index] = slot


def use_shield(agent, index: int, enemy_index: int, duration: float):
    """
    Agent shield himself for [DURATION] seconds

    Args:
        agent (agent): Malmo agent
        index (int): agent index
        enemy_index (float): enemy agent index
        duration (float): how long to shield for
    """
    # Select shield slot
    select_hotbar_slot(agent, index, 8)
    agent.sendCommand(f"use 1")
    AGENT_IS_SHIELDING[index] = True

    def release_shield_later():
        shield_broken = False
        for _ in range(100):
            if AGENT_JUST_ATTACKED[enemy_index] <= 0.1 and AGENT_WEAPONS[enemy_index] == "AXE":
                shield_broken = True
                break
            time.sleep(duration / 100)
        agent.sendCommand(f"use 0")
        AGENT_IS_SHIELDING[index] = False
        AGENT_SHIELD_COOLDOWNS[index] = 5 if shield_broken else 2

    thread = Thread(target=release_shield_later)
    thread.start()


def basic_agent(agent, agent_index, distance, pitch, yaw, nearby_blocks, line_of_sight):
    global ATTACK_COOLDOWNS, AGENT_COOLDOWNS
    enemy_index = 1 if agent_index == 0 else 0

    turn_speed, pitch_speed, move_speed, strafe_speed = calc_movement(AGENT_LOCATIONS[agent_index], AGENT_LOCATIONS[enemy_index], pitch, yaw, nearby_blocks)
    agent.sendCommand(f"turn {turn_speed}")
    agent.sendCommand(f"pitch {pitch_speed}")
    agent.sendCommand(f"move {move_speed * random.random() * 2}")
    agent.sendCommand(f"strafe {strafe_speed}")

    # Weapon policy:
    # - In general, use sword when enemy is using axe or fists
    # - When enemy is shielding, switch to axe and break shield
    # - When enemy is using sword, use sword/shield combo
    # - When low HP or enemy low HP, switch to axe for more damage
    best_weapon = "AXE" if AGENT_HEALTH[enemy_index] < 5 or AGENT_HEALTH[agent_index] < 7.5 or AGENT_HOTBAR[enemy_index] == 8 else "SWORD"
    if not AGENT_IS_SHIELDING[agent_index] and AGENT_WEAPONS[agent_index] != best_weapon:
        select_hotbar_slot(agent, agent_index, 1 if best_weapon == "AXE" else 0)

    # Shield policy:
    # - In general, don't hold shield against axe, can hold against other weapons
    # - When low HP, hold shield at all cost, bait attack, counter attack or run
    allow_shield = AGENT_WEAPONS[enemy_index] != "AXE" or AGENT_HEALTH[agent_index] < 5

    if distance <= 4 and AGENT_SHIELD_COOLDOWNS[agent_index] <= 0 and not AGENT_IS_SHIELDING[agent_index] and allow_shield and AGENT_COOLDOWNS[enemy_index] <= 0.5:
        # Raise shield for 0-2 seconds
        use_shield(agent, agent_index, enemy_index, random.random() * 3)
    elif line_of_sight is not None and line_of_sight["hitType"] == "entity" and line_of_sight["inRange"] and line_of_sight["type"] == AGENT_NAMES[enemy_index] \
            and AGENT_COOLDOWNS[agent_index] <= 0 and not AGENT_IS_SHIELDING[agent_index]:
        agent.sendCommand("attack 1")
        agent.sendCommand("attack 0")

        AGENT_JUST_ATTACKED[agent_index] = 0
        AGENT_COOLDOWNS[agent_index] = ATTACK_COOLDOWNS[AGENT_WEAPONS[agent_index]]


def agent_distance():
    return math.sqrt((AGENT_LOCATIONS[0][0] - AGENT_LOCATIONS[1][0]) ** 2 +
                     (AGENT_LOCATIONS[0][1] - AGENT_LOCATIONS[1][1]) ** 2 +
                     (AGENT_LOCATIONS[0][2] - AGENT_LOCATIONS[1][2]) ** 2)


if __name__ == "__main__":
    # Flush immediately
    print = functools.partial(print, flush=True)

    # Create agent host
    agent_hosts = [Malmo.AgentHost() for _ in range(2)]

    # Create client pool
    client_pool = Malmo.ClientPool()
    client_pool.add(Malmo.ClientInfo("127.0.0.1", 10000))
    client_pool.add(Malmo.ClientInfo("127.0.0.1", 10002))

    for a in range(MISSION_COUNT):
        print(f"Running mission #{a}...")
        # Create missions
        mission = Malmo.MissionSpec(get_mission_xml(), True)
        mission_id = str(uuid.uuid4())

        # Start mission
        for a in range(2):
            start_mission(agent_hosts[a], mission, client_pool, Malmo.MissionRecordSpec(), a, mission_id)

        wait_for_start(agent_hosts)

        hasEnded = False
        temp = 0
        while not hasEnded:
            hasEnded = True

            # Call each agent
            for agent_index in range(2):
                my_name = AGENT_NAMES[agent_index]
                enemy_name = "Puffer" if my_name == "Fish" else "Fish"
                agent_host = agent_hosts[agent_index]
                world_state = agent_host.getWorldState()

                if world_state.is_mission_running:
                    hasEnded = False
                else:
                    continue
                if world_state.number_of_observations_since_last_state <= 0:
                    continue

                msg = world_state.observations[-1].text
                ob = json.loads(msg)

                location = [ob.get(f"{k}Pos", 0) for k in "XYZ"]
                AGENT_LOCATIONS[agent_index] = location
                pitch, yaw = ob.get("Pitch", 0), ob.get("Yaw", 0)

                nearby_blocks = ob.get("blocks", [])
                line_of_sight = ob.get("LineOfSight", None)
                AGENT_HEALTH[agent_index] = ob.get("Life", 20.0)

                basic_agent(agent_host, agent_index, agent_distance(), pitch, yaw, nearby_blocks, line_of_sight)

            for agent_index in range(2):
                # Increase "just attacked" duration
                AGENT_JUST_ATTACKED[agent_index] += 0.05
                # Decrease attack cooldowns
                AGENT_COOLDOWNS[agent_index] = max(0, AGENT_COOLDOWNS[agent_index] - 0.05)
                # Decrease shield cooldowns
                AGENT_SHIELD_COOLDOWNS[agent_index] = max(0, AGENT_SHIELD_COOLDOWNS[agent_index] - 0.05)

            # Sleep for a while, wait for next observation
            time.sleep(0.05)
            temp += 1
'''

