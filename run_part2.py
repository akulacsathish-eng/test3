#!/usr/bin/env python3
"""Run a student Y86 Snake firmware program."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from part2_support import load_json, save_json, simulate_reference_mission
from y86_runtime import Y86Machine, Y86Parser


def compare_states(student: dict, expected: dict) -> list[str]:
    mismatches: list[str] = []
    keys = ["snake_x", "snake_y", "snake_length", "alive", "score", "food_index", "result", "stop_reason"]
    for key in keys:
        if student.get(key) != expected.get(key):
            mismatches.append(key)
    return mismatches


def main() -> int:
    part2_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Run the Part 2 Snake firmware.")
    parser.add_argument("assembly", nargs="?", default=str(part2_dir / "starter_part2.ys"))
    parser.add_argument("mission", nargs="?", default=str(part2_dir / "mission.json"))
    parser.add_argument("--output", default=str(part2_dir / "output.json"))
    args = parser.parse_args()

    assembly_path = Path(args.assembly)
    mission_path = Path(args.mission)
    if not mission_path.exists():
        print("Mission file not found. Make sure mission.json is in the Part 2 folder.", file=sys.stderr)
        return 1

    mission = load_json(mission_path)
    program_text = assembly_path.read_text(encoding="utf-8")
    parser_obj = Y86Parser(program_text)
    program = parser_obj.parse()
    machine = Y86Machine(program, mission)
    student_frames = machine.run_with_trace()
    student_state = machine.extract_state()
    expected_state, reference_frames = simulate_reference_mission(mission)
    mismatches = compare_states(student_state, expected_state)

    report = {
        "mission_file": str(mission_path),
        "assembly_file": str(assembly_path),
        "student_state": student_state,
        "expected_state": expected_state,
        "match": not mismatches,
        "mismatches": mismatches,
        "mission_success": not mismatches and expected_state["result"] == 1,
        "frames": student_frames,
        "student_frames": student_frames,
        "reference_frames": reference_frames,
    }
    save_json(Path(args.output), report)

    print("Snake Control Firmware Report")
    print(f"Student state matches reference: {report['match']}")
    print(f"Score: {student_state['score']} / {expected_state['score']}")
    print(f"Alive: {student_state['alive']}")
    print(f"Result flag: {student_state['result']}")
    print(f"Student replay frames: {len(student_frames)}")
    if mismatches:
        print("Mismatches: " + ", ".join(mismatches))
    else:
        print("Mission verified. Your firmware produced the expected final state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
