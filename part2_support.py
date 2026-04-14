#!/usr/bin/env python3
"""Shared support code for Part 2 of the Memory Vault System."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
import json


BOARD_WIDTH_ADDR = 0x300
BOARD_HEIGHT_ADDR = 0x308
SNAKE_LENGTH_ADDR = 0x310
ALIVE_FLAG_ADDR = 0x318
SCORE_ADDR = 0x320
FOOD_INDEX_ADDR = 0x328
NUM_MOVES_ADDR = 0x330
RESULT_FLAG_ADDR = 0x338
TARGET_SCORE_ADDR = 0x340
MOVES_PTR_ADDR = 0x348
SNAKE_X_PTR_ADDR = 0x350
SNAKE_Y_PTR_ADDR = 0x358
FOOD_X_PTR_ADDR = 0x360
FOOD_Y_PTR_ADDR = 0x368
NEXT_HEAD_X_ADDR = 0x370
NEXT_HEAD_Y_ADDR = 0x378
GROW_FLAG_ADDR = 0x380
STOP_REASON_ADDR = 0x388

MOVES_BASE_ADDR = 0x500
SNAKE_X_BASE_ADDR = 0x700
SNAKE_Y_BASE_ADDR = 0x900
FOOD_X_BASE_ADDR = 0xB00
FOOD_Y_BASE_ADDR = 0xD00
STACK_TOP_ADDR = 0x1FF8

STOP_MOVE_END = 0
STOP_WALL = 1
STOP_SELF = 2
STOP_COMPLETED = 3

MOVE_UP = 1
MOVE_DOWN = 2
MOVE_LEFT = 3
MOVE_RIGHT = 4

MOVE_NAMES = {
    MOVE_UP: "UP",
    MOVE_DOWN: "DOWN",
    MOVE_LEFT: "LEFT",
    MOVE_RIGHT: "RIGHT",
}


@dataclass
class Node:
    valid: int
    contributes: int
    position: int
    row_index: int
    col_disp: int
    noise: int
    col_val: int


@dataclass
class SnakeState:
    width: int
    height: int
    snake_x: List[int]
    snake_y: List[int]
    score: int
    food_index: int
    alive: int
    result: int
    stop_reason: int

    @property
    def length(self) -> int:
        return len(self.snake_x)


def compute_seed(student_id: str) -> int:
    digits = "".join(ch for ch in student_id if ch.isdigit())
    if not digits:
        return 0
    return (int(digits) * 1664525 + 1013904223) & 0x7FFFFFFF


def lcg_next(state: int) -> int:
    return (state * 1664525 + 1013904223) & 0x7FFFFFFF


def generate_part1_vault(seed: int) -> List[List[str]]:
    state = seed
    vault = [["?" for _ in range(12)] for _ in range(8)]
    for row in range(8):
        for col in range(12):
            state = lcg_next(state)
            vault[row][col] = chr(ord("A") + (state % 26))
    return vault


def generate_part1_nodes(seed: int) -> List[Node]:
    state = seed
    state = lcg_next(state)
    length = 6 + (state % 5)
    nodes: List[Node] = []
    for index in range(length):
        state = lcg_next(state)
        row_index = state % 8
        state = lcg_next(state)
        col_val = state % 12
        state = lcg_next(state)
        low = state
        state = lcg_next(state)
        high = state
        noise = (high << 32) | low
        nodes.append(
            Node(
                valid=1,
                contributes=1,
                position=index,
                row_index=row_index,
                col_disp=24,
                noise=noise,
                col_val=col_val,
            )
        )
    return nodes


def recover_part1_password(student_id: str) -> str:
    seed = compute_seed(student_id)
    vault = generate_part1_vault(seed)
    nodes = generate_part1_nodes(seed)
    out = ["?"] * len(nodes)
    for node in nodes:
        if node.valid and node.contributes:
            out[node.position] = vault[node.row_index][node.col_val]
    return "".join(out)


def derive_mission_seed(student_id: str, password: str) -> int:
    state = compute_seed(student_id)
    for ch in password:
        state = (state ^ ord(ch)) & 0x7FFFFFFF
        state = lcg_next(state)
    return state


def _reference_step(
    snake_x: List[int],
    snake_y: List[int],
    move: int,
    food: Tuple[int, int] | None,
    width: int,
    height: int,
) -> Tuple[List[int], List[int], bool, bool]:
    dx = 0
    dy = 0
    if move == MOVE_UP:
        dy = -1
    elif move == MOVE_DOWN:
        dy = 1
    elif move == MOVE_LEFT:
        dx = -1
    elif move == MOVE_RIGHT:
        dx = 1

    new_x = snake_x[0] + dx
    new_y = snake_y[0] + dy
    if new_x < 0 or new_x >= width or new_y < 0 or new_y >= height:
        return snake_x[:], snake_y[:], False, False

    grow = food is not None and (new_x, new_y) == food
    body_limit = len(snake_x) if grow else len(snake_x) - 1
    for index in range(body_limit):
        if snake_x[index] == new_x and snake_y[index] == new_y:
            return snake_x[:], snake_y[:], False, grow

    next_x = snake_x[:]
    next_y = snake_y[:]
    if grow:
        next_x.append(next_x[-1])
        next_y.append(next_y[-1])
    for index in range(len(next_x) - 1, 0, -1):
        next_x[index] = next_x[index - 1]
        next_y[index] = next_y[index - 1]
    next_x[0] = new_x
    next_y[0] = new_y
    return next_x, next_y, True, grow


def generate_mission(student_id: str) -> Dict[str, object]:
    password = recover_part1_password(student_id)
    width = 8
    height = 8
    state = derive_mission_seed(student_id, password)
    snake_x = [2, 1, 0]
    snake_y = [4, 4, 4]
    planned_x = snake_x[:]
    planned_y = snake_y[:]

    food_steps = [3, 7, 11]
    foods_x: List[int] = []
    foods_y: List[int] = []
    moves: List[int] = []
    step_number = 0
    food_cursor = 0

    while step_number < 16:
        candidates = [MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT]
        ranked: List[Tuple[int, int, List[int], List[int], bool]] = []
        for move in candidates:
            food = None
            will_be_food = food_cursor < len(food_steps) and step_number in food_steps
            next_x, next_y, alive, _ = _reference_step(
                planned_x,
                planned_y,
                move,
                (0, 0) if will_be_food else None,
                width,
                height,
            )
            if not alive:
                continue
            trial_food = (next_x[0], next_y[0]) if will_be_food else None
            next_x, next_y, alive, grow = _reference_step(
                planned_x,
                planned_y,
                move,
                trial_food,
                width,
                height,
            )
            if alive:
                state = lcg_next(state)
                ranked.append((state, move, next_x, next_y, grow))

        if not ranked:
            break

        ranked.sort(key=lambda item: item[0])
        choice = ranked[state % len(ranked)]
        _, move, planned_x, planned_y, grow = choice
        moves.append(move)
        if food_cursor < len(food_steps) and step_number == food_steps[food_cursor]:
            foods_x.append(planned_x[0])
            foods_y.append(planned_y[0])
            food_cursor += 1
        step_number += 1

    moves.append(0)
    mission = {
        "student_id": student_id,
        "story": "This Snake mission continues the same deterministic vault story from Part 1.",
        "board_width": width,
        "board_height": height,
        "initial_length": len(snake_x),
        "initial_snake_x": snake_x,
        "initial_snake_y": snake_y,
        "food_x": foods_x,
        "food_y": foods_y,
        "moves": moves,
        "target_score": len(foods_x),
    }
    expected_state, frames = simulate_reference_mission(mission)
    mission["preview_terminal_head"] = [expected_state["snake_x"][0], expected_state["snake_y"][0]]
    mission["reference_steps"] = len(frames) - 1
    return mission


def simulate_reference_mission(mission: Dict[str, object]) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    width = int(mission["board_width"])
    height = int(mission["board_height"])
    snake_x = list(mission["initial_snake_x"])
    snake_y = list(mission["initial_snake_y"])
    food_x = list(mission["food_x"])
    food_y = list(mission["food_y"])
    moves = list(mission["moves"])
    score = 0
    food_index = 0
    alive = 1
    stop_reason = STOP_MOVE_END
    frames: List[Dict[str, object]] = [
        {
            "step": 0,
            "move": "START",
            "snake": list(zip(snake_x, snake_y)),
            "score": score,
            "alive": alive,
        }
    ]

    for step, move in enumerate(moves, start=1):
        if move == 0:
            stop_reason = STOP_MOVE_END
            break

        food = None
        if food_index < len(food_x):
            food = (food_x[food_index], food_y[food_index])

        next_x, next_y, alive_now, grow = _reference_step(
            snake_x,
            snake_y,
            move,
            food,
            width,
            height,
        )
        if not alive_now:
            alive = 0
            stop_reason = STOP_SELF
            trial_head_x = snake_x[0]
            trial_head_y = snake_y[0]
            if move == MOVE_UP:
                trial_head_y -= 1
            elif move == MOVE_DOWN:
                trial_head_y += 1
            elif move == MOVE_LEFT:
                trial_head_x -= 1
            elif move == MOVE_RIGHT:
                trial_head_x += 1
            if trial_head_x < 0 or trial_head_x >= width or trial_head_y < 0 or trial_head_y >= height:
                stop_reason = STOP_WALL
            frames.append(
                {
                    "step": step,
                    "move": MOVE_NAMES[move],
                    "snake": list(zip(snake_x, snake_y)),
                    "score": score,
                    "alive": alive,
                }
            )
            break

        snake_x = next_x
        snake_y = next_y
        if grow:
            score += 1
            food_index += 1
        frames.append(
            {
                "step": step,
                "move": MOVE_NAMES[move],
                "snake": list(zip(snake_x, snake_y)),
                "score": score,
                "alive": alive,
            }
        )
    else:
        stop_reason = STOP_MOVE_END

    if alive and score == int(mission["target_score"]):
        stop_reason = STOP_COMPLETED if stop_reason == STOP_MOVE_END else stop_reason

    result = 1 if alive and score == int(mission["target_score"]) else 0
    final_state = {
        "board_width": width,
        "board_height": height,
        "snake_x": snake_x,
        "snake_y": snake_y,
        "snake_length": len(snake_x),
        "alive": alive,
        "score": score,
        "food_index": food_index,
        "result": result,
        "stop_reason": stop_reason,
    }
    return final_state, frames


def save_json(path: Path, data: Dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
