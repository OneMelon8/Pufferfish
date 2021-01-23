# Imports
import math
import json
import time
import uuid
import functools
from past.utils import old_div
from collections import namedtuple

import MalmoPython as Malmo

# Global configurations
TIME_OUT_MS = 60_000

# File path to the arena map folder
# Add your path into one of these, commenting/uncommenting might be easier
ABSOLUTE_PATH_TO_MAP = "C:/One/UCI/Classes/CS175/Arena"  # neo
# ABSOLUTE_PATH_TO_MAP = "" # eric
# ABSOLUTE_PATH_TO_MAP = "" # tianshu

# Mission configurations
MISSION_COUNT = 5

EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

# Agent configurations
AGENT_COUNT = 2
AGENT_NAMES = ["Puffer", "Fish"]
# AGENT_SPAWNS = ["<Placement x=\"0.5\" y=\"64\" z=\"-26.5\" yaw=\"0\"/>", "<Placement x=\"0.5\" y=\"64\" z=\"27.5\" yaw=\"180\"/>"]
AGENT_SPAWNS = ["<Placement x=\"0.5\" y=\"64\" z=\"-26.5\" yaw=\"0\"/>", "<Placement x=\"6.5\" y=\"65\" z=\"-5.5\" yaw=\"180\"/>"]
AGENT_EQUIPMENTS = [(3, 1), (3, 1)]  # (weapon, armor)


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
                <FileWorldGenerator src="{ABSOLUTE_PATH_TO_MAP}"/>
                <ServerQuitFromTimeUp timeLimitMs="{TIME_OUT_MS}"/>
                <ServerQuitWhenAnyAgentFinishes/>
            </ServerHandlers>
        </ServerSection>
    """

    for a in range(AGENT_COUNT):
        xml += f"""
        <AgentSection mode="Adventure">
            <Name>{AGENT_NAMES[a]}</Name>
            <AgentStart>
                {AGENT_SPAWNS[a]}
                {create_inventory(*AGENT_EQUIPMENTS[a])}
            </AgentStart>
            <AgentHandlers>
                <ContinuousMovementCommands turnSpeedDegs="360"/>
                <ChatCommands/>
                <MissionQuitCommands/>
                <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="60" yrange="5" zrange="60"/>
                </ObservationFromNearbyEntities>
                <ObservationFromRay/>
                <ObservationFromFullStats/>
            </AgentHandlers>
        </AgentSection>
        """

    xml += "</Mission>"
    return xml


def create_inventory(weapon_tier: int = 0, armor_tier: int = 0):
    """
    Generates an inventory XML segment based on requirements

    @param weapon_tier: (int) 0 - wooden; 1 - gold; 2 - stone; 3 - iron; 4 - diamond
    @param armor_tier: (int) 0 - none; 1 - leather; 2 - gold; 3 - chain; 4 - iron; 5 - diamond
    """
    assert 0 <= weapon_tier <= 4, f"Expected weapon tier (0-4), got \"{weapon_tier}\""
    assert 0 <= armor_tier <= 5, f"Expected armor tier (0-5), got \"{armor_tier}\""

    weapon_tiers = ["wooden", "golden", "stone", "iron", "diamond"]
    armor_tiers = ["", "leather", "golden", "chainmail", "iron", "diamond"]

    # Set weapons
    xml = f"""<Inventory>
    <InventoryObject type="{weapon_tiers[weapon_tier]}_sword" slot="0"/>
    <InventoryObject type="{weapon_tiers[weapon_tier]}_axe" slot="1"/>
    <InventoryObject type="shield" slot="8"/>
    """

    # Set armor
    if armor_tier > 0:
        for i, armor_type in enumerate(["helmet", "chestplate", "leggings", "boots"]):
            xml += f"<InventoryObject type=\"{armor_tiers[armor_tier]}_{armor_type}\" slot=\"{39 - i}\"/>"

    xml += "</Inventory>"
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
    start_flags = [False for _ in range(AGENT_COUNT)]
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


##
def calcTurnValue(us, them, current_yaw):
    """ Calc turn speed required to steer "us" towards "them" """
    dx = them[0] - us[0]
    dz = them[1] - us[1]
    yaw = -180 * math.atan2(dx, dz) / math.pi
    difference = yaw - current_yaw
    while difference < -180:
        difference += 360
    while difference > 180:
        difference -= 360
    difference /= 180.0
    return difference


def getVelocity(my_name, entities, current_yaw, current_pos):
    """ Calculate a good velocity to head in, according to the entities around us """
    if my_name == "Puffer" or any(_ is None for _ in [my_name, entities, current_yaw, current_pos]):
        return 0, 0

    # Get all the points of interest (every entity apart from the robots)
    # poi = [ent for ent in entities if not ent.name.startswith("Robot")]
    enemy = None
    for ent in entities:
        if my_name == "Fish" and ent.name == "Puffer":
            enemy = ent
            break
    if enemy is None:
        return 0, 0
    print(enemy)

    # Turn value to head towards it:
    turn = calcTurnValue(current_pos, (enemy.x, enemy.z), current_yaw)
    # Calculate a speed to use - helps to avoid orbiting:
    dx = enemy.x - current_pos[0]
    dz = enemy.z - current_pos[1]
    speed = 1.0 - (old_div(1.0, (1.0 + abs(old_div(dx, 3.0)) + abs(old_div(dz, 3.0)))))
    if abs(dx) + abs(dz) < 1.5:
        speed = 0
    return turn, speed * 2


if __name__ == "__main__":
    # Flush immediately
    print = functools.partial(print, flush=True)

    # Create agent host
    agent_hosts = [Malmo.AgentHost() for _ in range(AGENT_COUNT)]

    # Create client pool
    client_pool = Malmo.ClientPool()
    for a in range(AGENT_COUNT):
        client_pool.add(Malmo.ClientInfo("127.0.0.1", 10000 + a))

    for a in range(MISSION_COUNT):
        print(f"Running mission #{a}...")
        # Create missions
        mission = Malmo.MissionSpec(get_mission_xml(), True)
        mission_id = str(uuid.uuid4())

        # Start mission
        for a in range(AGENT_COUNT):
            start_mission(agent_hosts[a], mission, client_pool, Malmo.MissionRecordSpec(), a, mission_id)

        wait_for_start(agent_hosts)

        hasEnded = False
        while not hasEnded:
            hasEnded = True
            # In mission
            for b in range(AGENT_COUNT):
                if AGENT_NAMES[b] == "Puffer":
                    continue
                agent_host = agent_hosts[b]
                world_state = agent_host.getWorldState()
                
                if world_state.is_mission_running:
                    hasEnded = False  # all not good
                if world_state.is_mission_running and world_state.number_of_observations_since_last_state > 0:
                    msg = world_state.observations[-1].text
                    ob = json.loads(msg)

                    if "Yaw" in ob:
                        yaw = ob[u'Yaw']
                    if "XPos" in ob and "ZPos" in ob:
                        position = (ob[u'XPos'], ob[u'ZPos'])
                    if "entities" in ob:
                        entities = [EntityInfo(k["x"], k["y"], k["z"], k["name"]) for k in ob["entities"]]
                        turn, speed = getVelocity(AGENT_NAMES[b], entities, yaw, position)
                        agent_host.sendCommand("move " + str(speed))
                        agent_host.sendCommand("turn " + str(turn))
                    if u'LineOfSight' in ob:
                        los = ob[u'LineOfSight']
                        if los[u'hitType'] == "entity" and los[u'inRange'] and los[u'type'] == "Puffer":
                            agent_host.sendCommand("attack 1")
                            agent_host.sendCommand("attack 0")

            time.sleep(0.1)
