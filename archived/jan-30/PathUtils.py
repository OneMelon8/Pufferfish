# Imports
import math
import json
import time
import uuid
import functools

import MalmoPython as Malmo


def find_path(my_location, enemy_location, grid):
    """
    Find a path towards the enemy

    Args:
        my_location (Tuple(float, float)): a tuple representing my location (x, z)
        enemy_location (Tuple(float, float)): a tuple representing enemy's location (x, z)
        grid ():

    Returns:
        List[Location]: list of "waypoints"
    """


def calc_movement(my_location, target_location, my_yaw):
    """
    Calculate movement information towards the target location

    Args:
        my_location (Tuple(float, float)): a tuple representing my location (x, z)
        target_location (Tuple(float, float)): a tuple representing target location (x, z)
        my_yaw (float): my yaw

    Returns:
        Tuple[float, float]: tuple containing (turn speed, move speed)
    """
    dx, dy, dz = [target_location[a] - my_location[a] for a in range(3)]

    # Calculate turn value
    angle_degrees = -180 * math.atan2(dx, dz) / math.pi
    difference = angle_degrees - my_yaw
    while difference < -180:
        difference += 360
    while difference > 180:
        difference -= 360
    difference /= 180

    # Calculate movement speed
    speed = 1.0 - (1.0 / (1.0 + abs(dx / 3.0) + abs(dz / 3.0)))
    if abs(dx) + abs(dz) < 1.5:
        speed = 0

    return difference, speed
