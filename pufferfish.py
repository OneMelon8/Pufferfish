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
# ABSOLUTE_PATH_TO_MAP = "" # eric
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
