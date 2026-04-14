#!/usr/bin/env python3
"""Unlock Part 2 by validating the recovered Part 1 password."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from part2_support import generate_mission, save_json


def main() -> int:
    part2_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Unlock the Part 2 Snake mission.")
    parser.add_argument("student_id")
    parser.add_argument("password", help="Password recovered from Part 1")
    parser.add_argument("--output", default=str(part2_dir / "mission.json"))
    args = parser.parse_args()

    try:
        mission = generate_mission(args.student_id, args.password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output_path = Path(args.output)
    save_json(output_path, mission)
    print(f"Mission unlocked: {output_path}")
    print(f"Board: {mission['board_width']}x{mission['board_height']}")
    print(f"Initial length: {mission['initial_length']}")
    print(f"Foods: {len(mission['food_x'])}")
    print(f"Moves: {len(mission['moves'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
