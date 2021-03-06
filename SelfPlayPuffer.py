# Imports
import requests
from abc import ABC
from collections import namedtuple
from threading import Thread

import MalmoPython as Malmo
import gym
import numpy as np
import matplotlib.pyplot as plt
import ray
from gym.spaces import Discrete, Box
from ray.rllib.agents import ppo

from Pufferfish.MissionXmlUtils import *
from Pufferfish.PathUtils import *

# File path to the arena map folder
ABSOLUTE_PATH_TO_MAP = "C:/One/UCI/Classes/CS175/Arena"  # one
# ABSOLUTE_PATH_TO_MAP = "C:/Users/ericn/OneDrive/Desktop/UCI/CS175 project in ai/Arena"  # eric
# ABSOLUTE_PATH_TO_MAP = "C:/Users/Tianshu Wang/Desktop/Arena" # tianshu

EntityInfo = namedtuple('EntityInfo', 'x, y, z, name')

MESSAGE_BASIC = "/tellraw @a [\"\",{\"text\":\"[\",\"color\":\"gray\"},{\"text\":\"Puffer\",\"color\":\"red\"},{\"text\":\"Fish\",\"color\":\"gold\"}," \
                "{\"text\":\"]\",\"color\":\"gray\"},{\"text\":\" Using \",\"color\":\"yellow\"},{\"text\":\"basic\",\"color\":\"aqua\"},{\"text\":\" agent\",\"color\":\"yellow\"}]"
MESSAGE_SELF_PLAY = "/tellraw @a [\"\",{\"text\":\"[\",\"color\":\"gray\"},{\"text\":\"Puffer\",\"color\":\"red\"},{\"text\":\"Fish\",\"color\":\"gold\"}," \
                    "{\"text\":\"]\",\"color\":\"gray\"},{\"text\":\" Using \",\"color\":\"yellow\"},{\"text\":\"self-play\",\"color\":\"green\"},{\"text\":\" agent\",\"color\":\"yellow\"}]"

# Agent configurations
AGENT_NAMES = ["Puffer", "Fish"]
AGENT_SPAWNS = ["<Placement x=\"0.5\" y=\"64\" z=\"-26.5\" yaw=\"0\"/>", "<Placement x=\"0.5\" y=\"64\" z=\"27.5\" yaw=\"180\"/>"]
AGENT_EQUIPMENTS = [(3, 2), (3, 2)]  # (weapon, armor)
AGENT_GAPPLE_INITIAL_AMOUNT = [2, 2]

# Attack cooldown map
ATTACK_COOLDOWNS = {
    "SWORD": 0.6,
    "AXE": 1,
    "OTHER": 0.25
}

# Hotbar observation map
HOTBAR_OBSERVATION = {
    0: 0.75,
    1: 1,
    7: 0.25,
    8: 0
}

# Action name map (debug)
ACTION_DEBUG_MAP = {
    0: "ATTACK",
    1: "SWITCH SWORD",
    2: "SWITCH AXE",
    3: "GAPPLE",
    4: "SHIELD",
    5: "IDLE"
}

# Agent dynamic stats
AGENT_LOCATIONS = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
AGENT_COOLDOWNS = [0.0, 0.0]
AGENT_JUST_ATTACKED = [0.0, 0.0]
AGENT_SHIELD_COOLDOWNS = [0.0, 0.0]
AGENT_WEAPONS = ["SWORD", "SWORD"]
AGENT_IS_BUSY = [False, False]
AGENT_HOTBAR = [0, 0]
AGENT_GAPPLE_COUNT = AGENT_GAPPLE_INITIAL_AMOUNT[:]
AGENT_GAPPLE_COOLDOWN = [0.0, 0.0]
AGENT_HEALTH = [20.0, 20.0]
PREV_AGENT_HEALTH = [AGENT_HEALTH[:], AGENT_HEALTH[:]]
AGENT_KILLS = [0, 0]
RL_AGENT_WINS = 0
RL_AGENT_LOSS = 0
USE_BASIC_AGENT = 0.2
AGENT_IDENTIFIED = False


# Debug
# prev_action = None


# Mission methods
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
                <ServerQuitFromTimeUp description="" timeLimitMs="120000"/>
            </ServerHandlers>
        </ServerSection>
    """

    for a in range(2):
        xml += f"""
        <AgentSection mode="Adventure">
            <Name>{AGENT_NAMES[a]}</Name>
            <AgentStart>
                {AGENT_SPAWNS[a]}
                {create_inventory(*AGENT_EQUIPMENTS[a], AGENT_GAPPLE_INITIAL_AMOUNT[a])}
            </AgentStart>
            <AgentHandlers>
                <ContinuousMovementCommands turnSpeedDegs="360"/>
                <InventoryCommands/>
                <ChatCommands/>
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


def start_mission(agent_host, mission, client_pool, mission_record, index, mission_id):
    # print(f"[Malmo] Attempting to start mission #{index} with ID = {mission_id}...")
    wait_time = 0
    while True:
        try:
            agent_host.startMission(mission, client_pool, mission_record, index, mission_id)
            break
        except Malmo.MissionException as ex:
            error_code = ex.details.errorCode
            if error_code == Malmo.MissionErrorCode.MISSION_SERVER_WARMING_UP:
                # print(f"[Malmo] Server not quite ready yet - waiting; wait time = {wait_time}")
                time.sleep(2)
                wait_time += 2
            elif error_code == Malmo.MissionErrorCode.MISSION_INSUFFICIENT_CLIENTS_AVAILABLE:
                # print("[Malmo] Not enough available Minecraft instances running.")
                # print(f"[Malmo] Will wait in case they are starting up; wait time = {wait_time}")
                time.sleep(2)
                wait_time += 2
            elif error_code == Malmo.MissionErrorCode.MISSION_SERVER_NOT_FOUND:
                # print("[Malmo] Server not found - has the mission with role 0 been started yet?")
                # print(f"[Malmo] Will wait and retry; wait time = {wait_time}")
                time.sleep(2)
                wait_time += 2
            else:
                print(f"[Malmo] Unknown error: {ex.message}, exiting system")
                exit(1)


def wait_for_start(agent_hosts):
    start_flags = [False for _ in range(2)]
    start_time = time.time()

    # Wait for at most 2 minutes
    while not all(start_flags) and time.time() - start_time < 120:
        start_flags = [agent.peekWorldState().has_mission_begun for agent in agent_hosts]
        time.sleep(0.1)

    # Timed out
    if time.time() - start_time >= 120:
        print("[Malmo] Timed out while waiting for mission to start, exiting system")
        exit(1)

    # Ready!
    print(f"[Malmo] All agents ready, mission start!")


# HTTP methods
def get_current_checkpoint():
    r = requests.get("http://localhost:5000/checkpoint")
    return r.json()


def increment_current_checkpoint():
    r = requests.post("http://localhost:5000/checkpoint")
    return r.json()


def reset_current_checkpoint():
    r = requests.post("http://localhost:5000/reset")
    return r.json()


def set_current_checkpoint(checkpoint_index):
    r = requests.post(f"http://localhost:5000/set?index={checkpoint_index}")
    return r.json()


# Agent methods
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
    AGENT_IS_BUSY[index] = True

    def release_shield_later():
        shield_broken = False
        for _ in range(100):
            if AGENT_JUST_ATTACKED[enemy_index] <= 0.1 and AGENT_WEAPONS[enemy_index] == "AXE":
                shield_broken = True
                break
            time.sleep(duration / 100)
        agent.sendCommand(f"use 0")
        AGENT_IS_BUSY[index] = False
        AGENT_SHIELD_COOLDOWNS[index] = 5 if shield_broken else 2

    thread = Thread(target=release_shield_later)
    thread.start()


def use_gapple(agent, index: int):
    """
    Agent eats a golden apple

    Args:
        agent (agent): Malmo agent
        index (int): agent index
    """
    # Check if there's any gapples left
    if AGENT_GAPPLE_COUNT[index] <= 0:
        return

    # Select golden apple slot
    select_hotbar_slot(agent, index, 7)
    agent.sendCommand(f"use 1")
    AGENT_IS_BUSY[index] = True

    def finished_eating():
        time.sleep(2.1)
        agent.sendCommand(f"use 0")
        AGENT_IS_BUSY[index] = False
        AGENT_GAPPLE_COUNT[index] -= 1
        AGENT_GAPPLE_COOLDOWN[index] = 6

    thread = Thread(target=finished_eating)
    thread.start()


def move(agent, agent_index, pitch, yaw, nearby_blocks):
    enemy_index = 1 if agent_index == 0 else 0
    turn_speed, pitch_speed, move_speed, strafe_speed = calc_movement(AGENT_LOCATIONS[agent_index], AGENT_LOCATIONS[enemy_index], pitch, yaw, nearby_blocks)
    agent.sendCommand(f"turn {turn_speed}")
    agent.sendCommand(f"pitch {pitch_speed}")
    agent.sendCommand(f"move {move_speed * random.random() * 2}")
    agent.sendCommand(f"strafe {strafe_speed}")


def agent_distance():
    return math.sqrt((AGENT_LOCATIONS[0][0] - AGENT_LOCATIONS[1][0]) ** 2 +
                     (AGENT_LOCATIONS[0][1] - AGENT_LOCATIONS[1][1]) ** 2 +
                     (AGENT_LOCATIONS[0][2] - AGENT_LOCATIONS[1][2]) ** 2)


def basic_agent(agent, agent_index, distance, pitch, yaw, nearby_blocks, line_of_sight):
    global ATTACK_COOLDOWNS, AGENT_COOLDOWNS, AGENT_IDENTIFIED
    if not AGENT_IDENTIFIED:
        # Identify agent type
        agent.sendCommand(f"chat {MESSAGE_BASIC}")
        # Select first hotbar slot
        select_hotbar_slot(agent, agent_index, 0)

        AGENT_IDENTIFIED = True
        return

    enemy_index = 1 if agent_index == 0 else 0
    move(agent, agent_index, pitch, yaw, nearby_blocks)

    # Weapon policy:
    # - In general, use sword when enemy is using axe or fists
    # - When enemy is shielding, switch to axe and break shield
    # - When enemy is using sword, use sword/shield combo
    # - When low HP or enemy low HP, switch to axe for more damage
    best_weapon = "AXE" if AGENT_HEALTH[enemy_index] < 5 or AGENT_HEALTH[agent_index] < 7.5 or AGENT_HOTBAR[enemy_index] == 8 else "SWORD"
    if not AGENT_IS_BUSY[agent_index] and AGENT_WEAPONS[agent_index] != best_weapon:
        select_hotbar_slot(agent, agent_index, 1 if best_weapon == "AXE" else 0)

    # Shield policy:
    # - In general, don't hold shield against axe, can hold against other weapons
    # - When low HP, hold shield at all cost, bait attack, counter attack or run
    allow_shield = AGENT_WEAPONS[enemy_index] != "AXE" or AGENT_HEALTH[agent_index] < 5

    # Heal policy:
    # - When enemy is wielding axe, heal when HP < 10
    # - When enemy is wielding sword, heal when HP < 7.5
    allow_heal = False
    if (AGENT_WEAPONS[enemy_index] == "AXE" and AGENT_HEALTH[agent_index] < 10) or (AGENT_WEAPONS[enemy_index] != "AXE" and AGENT_HEALTH[agent_index] < 6):
        allow_heal = True

    # Action: heal
    if not AGENT_IS_BUSY[agent_index] and AGENT_GAPPLE_COOLDOWN[agent_index] <= 0 and allow_heal:
        use_gapple(agent, agent_index)
    # Action: shield
    elif not AGENT_IS_BUSY[agent_index] and distance <= 4 and AGENT_SHIELD_COOLDOWNS[agent_index] <= 0 and allow_shield and AGENT_COOLDOWNS[enemy_index] <= 0.5:
        # Raise shield for 0-3 seconds
        use_shield(agent, agent_index, enemy_index, random.random() * 2)
    # Action: attack
    elif not AGENT_IS_BUSY[agent_index] and line_of_sight is not None and line_of_sight["hitType"] == "entity" and line_of_sight["inRange"] and line_of_sight["type"] == AGENT_NAMES[enemy_index] \
            and AGENT_COOLDOWNS[agent_index] <= 0:
        agent.sendCommand("attack 1")
        agent.sendCommand("attack 0")

        AGENT_JUST_ATTACKED[agent_index] = 0
        AGENT_COOLDOWNS[agent_index] = ATTACK_COOLDOWNS[AGENT_WEAPONS[agent_index]]


def self_play_agent(agent, policy, enemy_index, agent_index, line_of_sight):
    global AGENT_NAMES, AGENT_HEALTH, HOTBAR_OBSERVATION, AGENT_HOTBAR, AGENT_IS_BUSY, AGENT_COOLDOWNS, ATTACK_COOLDOWNS, AGENT_GAPPLE_COOLDOWN, AGENT_JUST_ATTACKED, AGENT_GAPPLE_COUNT, AGENT_SHIELD_COOLDOWNS, AGENT_IDENTIFIED
    if not AGENT_IDENTIFIED:
        # Identify agent type
        agent.sendCommand(f"chat {MESSAGE_SELF_PLAY}")
        # Select first hotbar slot
        select_hotbar_slot(agent, agent_index, 0)

        AGENT_IDENTIFIED = True
        return

    # CONTINUOUS OBSERVATION SPACE:
    # - enemy in range: true=1, false=0
    # - my health normalized: [0, 1]
    # - enemy health normalized: [0, 1]
    # - enemy weapon: axe=1, sword=0.75, gapple=0.25, shield=0 (offensive to defensive scale)

    observations = [0, 0, 0, 0]
    observations[0] = int(line_of_sight is not None and line_of_sight["hitType"] == "entity" and line_of_sight["inRange"] and line_of_sight["type"] == AGENT_NAMES[enemy_index])
    observations[1] = AGENT_HEALTH[agent_index] / 20
    observations[2] = AGENT_HEALTH[enemy_index] / 20
    observations[3] = HOTBAR_OBSERVATION[AGENT_HOTBAR[enemy_index]]

    # GET all the observations then send to
    # global prev_action

    action = policy.compute_actions([observations])[0][0]
    # if action != prev_action:
    #     print(f"[Fish] Action: {ACTION_DEBUG_MAP[action]}")
    #     prev_action = action

    # Apply action
    if line_of_sight is not None and line_of_sight["hitType"] == "entity" and line_of_sight["inRange"] and line_of_sight["type"] == AGENT_NAMES[enemy_index]:
        # Attack
        if not AGENT_IS_BUSY[agent_index] and AGENT_COOLDOWNS[agent_index] <= 0 and action == 0:
            agent.sendCommand("attack 1")
            agent.sendCommand("attack 0")
            AGENT_JUST_ATTACKED[agent_index] = 0
            AGENT_COOLDOWNS[agent_index] = ATTACK_COOLDOWNS[AGENT_WEAPONS[agent_index]]
        # Switch to sword
        elif not AGENT_IS_BUSY[agent_index] and AGENT_COOLDOWNS[agent_index] <= 0 and action == 1:
            select_hotbar_slot(agent, agent_index, 0)
        # Switch to axe
        elif not AGENT_IS_BUSY[agent_index] and AGENT_COOLDOWNS[agent_index] <= 0 and action == 2:
            select_hotbar_slot(agent, agent_index, 1)
        # Use gapple
        elif not AGENT_IS_BUSY[agent_index] and AGENT_GAPPLE_COOLDOWN[agent_index] <= 0 and AGENT_GAPPLE_COUNT[agent_index] > 0 and action == 3:
            use_gapple(agent, agent_index)
        # Use shield
        elif not AGENT_IS_BUSY[agent_index] and AGENT_SHIELD_COOLDOWNS[agent_index] <= 0 and action == 4:
            use_shield(agent, agent_index, enemy_index, 1)
        # Idle
        else:
            pass


def load_trained_agent(new_checkpoint):
    # Previous trainer
    prev_trainer = ppo.PPOTrainer(env=DummyTrainer, config={
        "env_config": {},
        "framework": "torch",
        "num_gpus": 0,
        "num_workers": 0,
        "explore": False
    })

    # restore an older model for the previous trainer
    prev_checkpoint_index = new_checkpoint
    try:
        prev_trainer.restore(f"models/checkpoint_{prev_checkpoint_index}/checkpoint-{prev_checkpoint_index}")
    except FileNotFoundError:
        return None

    return prev_trainer.workers.local_worker().get_policy()


class DummyTrainer(gym.Env, ABC):
    def __init__(self, _):
        self.action_space = Discrete(6)
        self.observation_space = Box(0, 1, shape=(4,), dtype=np.float32)

    def step(self, action):
        return np.array([0, 0, 0, 0]), 0, False, dict()

    def reset(self):
        return np.zeros((4,))


class Trainer(gym.Env, ABC):
    def __init__(self, _):
        # Graphing the returns
        self.step_rewards = []

        # DISCRETE ACTION SPACE [0, 5]:
        # - action 0 = attack
        # - action 1 = switch to sword
        # - action 2 = switch to axe
        # - action 3 = use gapple
        # - action 4 = use shield (1 second)
        # - action 5 = idle
        self.action_space = Discrete(6)

        # CONTINUOUS OBSERVATION SPACE:
        # - enemy in range: true=1, false=0
        # - my health normalized: [0, 1]
        # - enemy health normalized: [0, 1]
        # - enemy weapon: axe=1, sword=0.75, gapple=0.25, shield=0 (offensive to defensive scale)
        self.observation_space = Box(0, 1, shape=(4,), dtype=np.float32)

        ###################################
        # Malmo parameters
        self.agent_hosts = [Malmo.AgentHost() for _ in range(2)]
        # Create client pool
        self.client_pool = Malmo.ClientPool()
        self.client_pool.add(Malmo.ClientInfo("127.0.0.1", 10000))
        self.client_pool.add(Malmo.ClientInfo("127.0.0.1", 10001))
        self.mission_index = 0
        self.old_checkpoint = -1

        ###################################
        # self-play parameters
        self.opponent_policy = load_trained_agent(get_current_checkpoint())
        self.use_self_play = False
        self.last_load = 0
        self.first_reset = True

    def step(self, action):
        # Reinforcement learning agent
        global AGENT_KILLS, RL_AGENT_LOSS, RL_AGENT_WINS, AGENT_IDENTIFIED
        rl_agents_killed = AGENT_KILLS[0]
        ai_agents_killed = AGENT_KILLS[1]

        action = int(action)
        # Take action
        done = True
        observations = [0, 0, 0, 0]
        reward = 0
        penalty = 0
        for agent_index in range(2):
            # my_name = AGENT_NAMES[agent_index]
            # enemy_name = "Puffer" if my_name == "Fish" else "Fish"
            agent_host = self.agent_hosts[agent_index]
            world_state = agent_host.getWorldState()
            enemy_index = 1 if agent_index == 0 else 0

            done = not world_state.is_mission_running
            if done or world_state.number_of_observations_since_last_state <= 0:
                continue

            msg = world_state.observations[-1].text
            ob = json.loads(msg)

            location = [ob.get(f"{k}Pos", 0) for k in "XYZ"]
            AGENT_LOCATIONS[agent_index] = location
            pitch, yaw = ob.get("Pitch", 0), ob.get("Yaw", 0)

            nearby_blocks = ob.get("blocks", [])
            line_of_sight = ob.get("LineOfSight", None)
            AGENT_HEALTH[agent_index] = ob.get("Life", 20.0)

            # ===========================
            # # Self-play / Basic Agent #
            # ===========================
            if agent_index != 0:
                move(agent_host, agent_index, pitch, yaw, nearby_blocks)
                AGENT_KILLS[1] = ob.get("PlayersKilled")
                if ai_agents_killed < AGENT_KILLS[1]:
                    RL_AGENT_LOSS += 1
                if self.use_self_play:
                    self_play_agent(agent_host, self.opponent_policy, enemy_index, agent_index, line_of_sight)
                else:
                    basic_agent(agent_host, agent_index, agent_distance(), pitch, yaw, nearby_blocks, line_of_sight)
                continue

            # ================================
            # # Reinforcement Learning Agent #
            # ================================
            else:
                AGENT_KILLS[0] = ob.get("PlayersKilled")
                move(agent_host, agent_index, pitch, yaw, nearby_blocks)
                invalid_action = False
                # Attack (action 0)
                if action == 0:
                    if AGENT_IS_BUSY[agent_index] or AGENT_COOLDOWNS[agent_index] > 0:
                        invalid_action = True
                    else:
                        agent_host.sendCommand("attack 1")
                        agent_host.sendCommand("attack 0")
                        AGENT_JUST_ATTACKED[agent_index] = 0
                        AGENT_COOLDOWNS[agent_index] = ATTACK_COOLDOWNS[AGENT_WEAPONS[agent_index]]
                # Switch to sword (action 1)
                elif action == 1:
                    if AGENT_IS_BUSY[agent_index] or AGENT_COOLDOWNS[agent_index] > 0:
                        invalid_action = True
                    else:
                        select_hotbar_slot(agent_host, agent_index, 0)
                # Switch to axe (action 2)
                elif action == 2:
                    if AGENT_IS_BUSY[agent_index] or AGENT_COOLDOWNS[agent_index] > 0:
                        invalid_action = True
                    else:
                        select_hotbar_slot(agent_host, agent_index, 1)
                # Use gapple (action 3)
                elif action == 3:
                    if AGENT_IS_BUSY[agent_index] or AGENT_GAPPLE_COOLDOWN[agent_index] > 0 or AGENT_GAPPLE_COUNT[agent_index] <= 0:
                        invalid_action = True
                    else:
                        use_gapple(agent_host, agent_index)
                # Use shield (action 4)
                elif action == 4:
                    if AGENT_IS_BUSY[agent_index] or AGENT_SHIELD_COOLDOWNS[agent_index] > 0:
                        invalid_action = True
                    else:
                        use_shield(agent_host, agent_index, enemy_index, 1)
                # Idle (action 5)
                else:
                    pass

                # Calculate invalid action penalty
                if invalid_action:
                    penalty += 0.5

            # Calculate observations
            # - enemy in range: true=1, false=0
            # - my health normalized: [0, 1]
            # - enemy health normalized: [0, 1]
            # - enemy weapon: axe=1, sword=0.75, gapple=0.25, shield=0 (offensive to defensive scale)
            observations = [0, 0, 0, 0]
            observations[0] = int(line_of_sight is not None and line_of_sight["hitType"] == "entity" and line_of_sight["inRange"] and line_of_sight["type"] == AGENT_NAMES[enemy_index])
            observations[1] = AGENT_HEALTH[agent_index] / 20
            observations[2] = AGENT_HEALTH[enemy_index] / 20
            observations[3] = HOTBAR_OBSERVATION[AGENT_HOTBAR[enemy_index]]

            # Calculate reward
            # Reward = delta "my health" - delta "enemy health"
            # Calculate delta "my health"
            delta_health = AGENT_HEALTH[agent_index] - PREV_AGENT_HEALTH[0][agent_index]
            # Calculate delta "enemy health"
            delta_enemy_health = AGENT_HEALTH[enemy_index] - PREV_AGENT_HEALTH[0][enemy_index]
            reward = delta_health - delta_enemy_health
            # Calculate enemy killed reward
            if rl_agents_killed < AGENT_KILLS[0]:
                RL_AGENT_WINS += 1
                reward += 20
            # Calculate penalties
            reward -= penalty
        # =============================================

        # Decrement cooldowns
        for agent_index in range(2):
            # Increase "just attacked" duration
            AGENT_JUST_ATTACKED[agent_index] += 0.05
            # Decrease attack cooldowns
            AGENT_COOLDOWNS[agent_index] = max(0.0, AGENT_COOLDOWNS[agent_index] - 0.05)
            # Decrease shield cooldowns
            AGENT_SHIELD_COOLDOWNS[agent_index] = max(0.0, AGENT_SHIELD_COOLDOWNS[agent_index] - 0.05)
            # Decrease gapple cooldowns
            AGENT_GAPPLE_COOLDOWN[agent_index] = max(0.0, AGENT_GAPPLE_COOLDOWN[agent_index] - 0.05)

        del PREV_AGENT_HEALTH[0]
        PREV_AGENT_HEALTH.append(AGENT_HEALTH[:])

        # Add reward into steps
        self.step_rewards.append(reward)

        # Debug current reward
        # print(f"[Puffer] Action: {ACTION_DEBUG_MAP[action]} / Reward: {reward}")

        # Sleep for a while, wait for next observation
        time.sleep(0.05)
        return np.array(observations), reward, done, dict()

    def reset(self):
        global AGENT_LOCATIONS, AGENT_COOLDOWNS, AGENT_JUST_ATTACKED, AGENT_SHIELD_COOLDOWNS, AGENT_WEAPONS, AGENT_IS_BUSY, AGENT_HOTBAR, AGENT_GAPPLE_COUNT, AGENT_GAPPLE_COOLDOWN, AGENT_HEALTH, PREV_AGENT_HEALTH, \
            AGENT_KILLS, AGENT_IDENTIFIED
        # Graph and reset step rewards
        # _, ax = plt.subplots(1, 1, figsize=(10, 3))
        # ax.plot(np.arange(len(self.step_rewards)), self.step_rewards, "r-")
        # plt.show()

        # Reset Malmo
        self.reset_malmo()

        # Reset global variables
        AGENT_LOCATIONS = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        AGENT_COOLDOWNS = [0.0, 0.0]
        AGENT_JUST_ATTACKED = [0.0, 0.0]
        AGENT_SHIELD_COOLDOWNS = [0.0, 0.0]
        AGENT_WEAPONS = ["SWORD", "SWORD"]
        AGENT_IS_BUSY = [False, False]
        AGENT_HOTBAR = [0, 0]
        AGENT_GAPPLE_COUNT = AGENT_GAPPLE_INITIAL_AMOUNT[:]
        AGENT_GAPPLE_COOLDOWN = [0.0, 0.0]
        AGENT_HEALTH = [20.0, 20.0]
        PREV_AGENT_HEALTH = [AGENT_HEALTH[:], AGENT_HEALTH[:]]
        AGENT_KILLS = [0, 0]
        AGENT_IDENTIFIED = False

        curr_checkpoint = get_current_checkpoint()
        
        # Update the self-play agent model every 10 steps
        if (curr_checkpoint % 5 == 0 and self.last_load != curr_checkpoint) or self.first_reset:
            # Self-play agent is 10 steps behind current agent
            self.old_checkpoint = curr_checkpoint - 10
            print(f"[System] Loading new self-play agent at checkpoint {self.old_checkpoint}...", end=" ")
            self.opponent_policy = load_trained_agent(self.old_checkpoint)
            print("FAILED" if self.opponent_policy is None else "OK")
            self.last_load = curr_checkpoint

        self.use_self_play = random.random() > USE_BASIC_AGENT
        if self.opponent_policy is None:
            self.use_self_play = False

        # First reset tag
        if self.first_reset:
            self.first_reset = False

        print(f"[Malmo] Running mission #{self.mission_index}: #{curr_checkpoint} vs " + (f"#{self.old_checkpoint}" if self.use_self_play else "Basic Agent"))
        return np.zeros((4,))

    def reset_malmo(self):
        self.mission_index += 1
        # Create missions
        mission = Malmo.MissionSpec(get_mission_xml(), True)
        mission_id = str(uuid.uuid4())

        # Start mission
        for a in range(2):
            start_mission(self.agent_hosts[a], mission, self.client_pool, Malmo.MissionRecordSpec(), a, mission_id)

        wait_for_start(self.agent_hosts)


if __name__ == "__main__":
    checkpoint = 0
    if checkpoint == 0:
        print(f"[System] Creating a new model, setting checkpoint index to {checkpoint}")
    else:
        print(f"[System] Initializing model at checkpoint {checkpoint}...")
    set_current_checkpoint(checkpoint)
    # Flush immediately
    print = functools.partial(print, flush=True)
    # Init libraries
    ray.init()

    # Create agent
    trainer = ppo.PPOTrainer(env=Trainer, config={
        "env_config": {},
        "framework": "torch",
        "num_gpus": 0,
        "num_workers": 0
    })

    # Set to 0 to create a new agent
    checkpoint = get_current_checkpoint()
    if checkpoint > 0:
        trainer.restore(f"models/checkpoint_{checkpoint}/checkpoint-{checkpoint}")

    while True:
        trainer.train()
        trainer.save(f"models")
        print(f"[System] Saving checkpoint #{increment_current_checkpoint()}")
