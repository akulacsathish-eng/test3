#!/usr/bin/env python3
"""Tkinter replay viewer for the Snake Control Firmware mission."""

from __future__ import annotations

from pathlib import Path
import json
import tkinter as tk


CELL = 48


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class SnakeReplay:
    def __init__(self, root: tk.Tk, report: dict) -> None:
        self.report = report
        self.student_frames = report.get("student_frames", report.get("frames", []))
        self.reference_frames = report.get("reference_frames", [])
        width = report["expected_state"]["board_width"]
        height = report["expected_state"]["board_height"]
        self.canvas = tk.Canvas(root, width=width * CELL, height=height * CELL, bg="#faf7ef")
        self.canvas.pack()
        legend = tk.Label(
            root,
            text="Green = student path   Blue = reference path   Gold = goal",
            font=("Helvetica", 11),
        )
        legend.pack(pady=8)
        self.status = tk.Label(root, font=("Helvetica", 13, "bold"))
        self.status.pack(pady=10)
        self.index = 0
        self.root = root
        self.mission = self.load_mission()
        self.goal = self.reference_frames[-1]["snake"][0] if self.reference_frames else None
        self.first_mismatch = self.find_first_mismatch()
        self.draw()
        self.root.after(450, self.advance)

    def load_mission(self) -> dict | None:
        mission_path = Path(self.report.get("mission_file", ""))
        if mission_path.exists():
            return load_json(mission_path)

        fallback = Path(__file__).resolve().with_name("mission.json")
        if fallback.exists():
            return load_json(fallback)
        return None

    def frame_at(self, frames: list[dict], index: int | None = None) -> dict | None:
        if not frames:
            return None
        frame_index = self.index if index is None else index
        frame_index = min(frame_index, len(frames) - 1)
        return frames[frame_index]

    def head_path(self, frames: list[dict]) -> list[tuple[int, int]]:
        if not frames:
            return []
        stop = min(self.index + 1, len(frames))
        return [tuple(frame["snake"][0]) for frame in frames[:stop] if frame.get("snake")]

    def find_first_mismatch(self) -> int | None:
        count = max(len(self.student_frames), len(self.reference_frames))
        for index in range(count):
            student = self.frame_at(self.student_frames, index)
            reference = self.frame_at(self.reference_frames, index)
            if student is None or reference is None:
                continue
            if (
                student.get("snake") != reference.get("snake")
                or student.get("score") != reference.get("score")
                or student.get("alive") != reference.get("alive")
            ):
                return index
        return None

    def draw_goal(self) -> None:
        if self.goal is None:
            return
        gx, gy = self.goal
        x0 = gx * CELL + 8
        y0 = gy * CELL + 8
        x1 = x0 + CELL - 16
        y1 = y0 + CELL - 16
        self.canvas.create_oval(x0, y0, x1, y1, fill="#f4d03f", outline="#9c640c", width=3)
        self.canvas.create_text(
            gx * CELL + CELL / 2,
            gy * CELL + CELL / 2,
            text="GOAL",
            fill="#7d6608",
            font=("Helvetica", 10, "bold"),
        )

    def draw_foods(self, reference_frame: dict | None) -> None:
        if self.mission is None:
            return
        foods = list(zip(self.mission.get("food_x", []), self.mission.get("food_y", [])))
        eaten = reference_frame["score"] if reference_frame is not None else 0
        for food_idx, (fx, fy) in enumerate(foods):
            fill = "#d35400" if food_idx >= eaten else "#f5cba7"
            x0 = fx * CELL + 14
            y0 = fy * CELL + 14
            x1 = x0 + CELL - 28
            y1 = y0 + CELL - 28
            self.canvas.create_oval(x0, y0, x1, y1, fill=fill, outline="")

    def draw_path(self, points: list[tuple[int, int]], color: str, width: int, dash: tuple[int, int] | None = None) -> None:
        if not points:
            return
        coords: list[float] = []
        for x, y in points:
            coords.extend([x * CELL + CELL / 2, y * CELL + CELL / 2])
        if len(coords) >= 4:
            self.canvas.create_line(*coords, fill=color, width=width, dash=dash, capstyle=tk.ROUND)
        for x, y in points:
            cx = x * CELL + CELL / 2
            cy = y * CELL + CELL / 2
            self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=color, outline="")

    def draw_snake(self, snake: list[list[int]], head_fill: str, body_fill: str, outline: str, filled: bool) -> None:
        for index, (x, y) in enumerate(snake):
            x0 = x * CELL + 8
            y0 = y * CELL + 8
            x1 = x0 + CELL - 16
            y1 = y0 + CELL - 16
            fill = head_fill if index == 0 else body_fill
            if filled:
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=2)
            else:
                self.canvas.create_rectangle(x0, y0, x1, y1, fill="", outline=outline, width=3)

    def draw_mismatch(self, student_frame: dict | None, reference_frame: dict | None) -> None:
        if student_frame is None or reference_frame is None:
            return
        student_head = tuple(student_frame["snake"][0])
        reference_head = tuple(reference_frame["snake"][0])
        if student_head == reference_head:
            return

        for x, y, color in (
            (student_head[0], student_head[1], "#c0392b"),
            (reference_head[0], reference_head[1], "#1f618d"),
        ):
            x0 = x * CELL + 3
            y0 = y * CELL + 3
            x1 = x0 + CELL - 6
            y1 = y0 + CELL - 6
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=3)

    def draw(self) -> None:
        if not self.student_frames and not self.reference_frames:
            return
        expected = self.report["expected_state"]
        student_frame = self.frame_at(self.student_frames)
        reference_frame = self.frame_at(self.reference_frames)
        self.canvas.delete("all")
        for row in range(expected["board_height"]):
            for col in range(expected["board_width"]):
                x0 = col * CELL
                y0 = row * CELL
                x1 = x0 + CELL
                y1 = y0 + CELL
                fill = "#f2eadb" if (row + col) % 2 == 0 else "#e6dcc7"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#d7ccb5")

        self.draw_goal()
        self.draw_foods(reference_frame)
        self.draw_path(self.head_path(self.reference_frames), "#5dade2", 4, dash=(6, 4))
        self.draw_path(self.head_path(self.student_frames), "#27ae60", 6)

        if reference_frame is not None:
            self.draw_snake(reference_frame["snake"], "#5dade2", "#aed6f1", "#1f618d", filled=False)
        if student_frame is not None:
            self.draw_snake(student_frame["snake"], "#145a32", "#27ae60", "#0b3d1f", filled=True)

        self.draw_mismatch(student_frame, reference_frame)

        summary = "MATCH" if self.report["match"] else "MISMATCH"
        note = student_frame.get("note", "") if student_frame is not None else ""
        student_move = student_frame["move"] if student_frame is not None else "-"
        reference_move = reference_frame["move"] if reference_frame is not None else "-"
        student_score = student_frame["score"] if student_frame is not None else "-"
        reference_score = reference_frame["score"] if reference_frame is not None else "-"
        student_alive = student_frame["alive"] if student_frame is not None else "-"
        reference_alive = reference_frame["alive"] if reference_frame is not None else "-"
        mismatch_note = ""
        if self.first_mismatch is not None:
            mismatch_note = f"  First mismatch step: {self.first_mismatch}"
        self.status.config(
            text=(
                f"Step {self.index}  Student move: {student_move}  Expected move: {reference_move}  "
                f"Student score/alive: {student_score}/{student_alive}  "
                f"Expected score/alive: {reference_score}/{reference_alive}  "
                f"{summary}{mismatch_note}  {note}"
            )
        )

    def advance(self) -> None:
        max_frames = max(len(self.student_frames), len(self.reference_frames))
        if self.index < max_frames - 1:
            self.index += 1
            self.draw()
            self.root.after(450, self.advance)


def main() -> None:
    part2_dir = Path(__file__).resolve().parent
    report = load_json(part2_dir / "output.json")
    root = tk.Tk()
    root.title("Snake Control Firmware Replay")
    SnakeReplay(root, report)
    root.mainloop()


if __name__ == "__main__":
    main()
