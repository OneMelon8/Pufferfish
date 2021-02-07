# Imports
import math
import json
import time
import uuid
import functools

import MalmoPython as Malmo


def calc_movement(my_location, target_location, my_pitch, my_yaw, nearby_blocks):
    """
    Calculate movement information towards the target location

    Args:
        my_location (Tuple(float, float)): a tuple representing my location (x, z)
        target_location (Tuple(float, float)): a tuple representing target location (x, z)
        my_pitch (float): my pitch
        my_yaw (float): my yaw
        nearby_blocks (List[str]): 5x1x5 observation grid with player at the center
    Returns:
        Tuple[float, float]: tuple containing (turn speed, move speed)
    """
    dx, dy, dz = [target_location[a] - my_location[a] for a in range(3)]

    # Calculate turn value
    angle_degrees = -180 * math.atan2(dx, dz) / math.pi
    yaw_speed = angle_degrees - my_yaw
    while yaw_speed < -180:
        yaw_speed += 360
    while yaw_speed > 180:
        yaw_speed -= 360
    yaw_speed /= 180

    # Calculate pitch value
    target_pitch = math.atan(-dy / math.sqrt(dx ** 2 + dz ** 2)) / math.pi * 180
    pitch_speed = (target_pitch - my_pitch) / 90

    # Calculate movement speed
    move_speed = 1.0 - (1.0 / (1.0 + abs(dx / 3.0) + abs(dz / 3.0)))
    if abs(dx) + abs(dz) < 1.5:
        move_speed = 0

    # Calculate strafe speed
    # ==================================
    # Nearby blocks indices:
    # - [x] [00] [01] [02] [03] [04]
    # - [0]  00   01   02   03   04
    # - [1]  05   06   07   08   09
    # - [2]  10   11  [12]  13   14
    # - [3]  15   16   17   18   19
    # - [4]  20   21   22   23   24
    # ==================================
    # Strafing policy (player facing):
    # - u u u u u => 2 blocks away (u's), strafe at 1/4 speed
    # -   v v v   => 1 block away (v's), strafe at 1/2 speed
    # -   w   w   => 0 blocks away (w's), strafe at full speed
    # ==================================
    # Player facing data:
    # - Yaw = [-45, 45]   => south => facing +Z
    # - Yaw = [45, 135]   => west  => facing -X
    # - Yaw = [135, -135] => north => facing -Z [original array]
    # - Yaw = [-135, -45] => east  => facing +X
    strafe_speed = 0
    nearby_blocks = rotate_array(nearby_blocks, my_yaw)

    # Check w's
    if nearby_blocks[11] != "air" or nearby_blocks[13] != "air":
        strafe_speed = 1 if nearby_blocks[11] != "air" else -1
    # Check v's
    elif any(block != "air" for block in nearby_blocks[6:8 + 1]):
        strafe_speed = 0.5 if nearby_blocks[6] != "air" else -0.5
    # Check u's
    elif any(block != "air" for block in nearby_blocks[0:4 + 1]):
        count_left = len([block for block in nearby_blocks[0:2 + 1] if block == "air"])
        count_right = len([block for block in nearby_blocks[2:4 + 1] if block == "air"])
        strafe_speed = 0.25 if count_left > count_right else -0.25

    return yaw_speed, pitch_speed, move_speed, strafe_speed


def rotate_array(matrix, yaw):
    rotated = [0] * len(matrix)
    for a in range(len(matrix)):
        rotated[a] = matrix[transform_index(a, yaw)]
    return rotated


def transform_index(index, yaw):
    # North: no change
    if 135 <= yaw <= 180 or -180 <= yaw <= -135:
        return index
    x, z = index % 5, index // 5
    # South: flip array
    if -45 <= yaw <= 45:
        x, z = 4 - x, 4 - z
    # East: rotate 90° clockwise
    elif -135 <= yaw <= -45:
        x, z = z, 4 - x
    # West: rotate 90° clockwise then flip
    elif 45 <= yaw <= 135:
        x, z = z, 4 - x
        x, z = 4 - x, 4 - z
    return z * 5 + x


if __name__ == "__main__":
    a = ["00", "01", "02", "03", "04",
         "10", "11", "12", "13", "14",
         "20", "21", "22", "23", "24",
         "30", "31", "32", "33", "34",
         "40", "41", "42", "43", "44"]

    rotated = rotate_array(a, 46)
    for z in range(5):
        for x in range(5):
            print(f"{rotated[z * 5 + x]} ", end="")
        print()
