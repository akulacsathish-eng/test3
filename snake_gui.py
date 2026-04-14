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
        self.mode = tk.StringVar(value="student")
        self.canvas = tk.Canvas(root, width=width * CELL, height=height * CELL, bg="#faf7ef")
        self.canvas.pack()
        controls = tk.Frame(root)
        controls.pack(pady=8)
        tk.Radiobutton(
            controls,
            text="Student Trace",
            variable=self.mode,
            value="student",
            command=self.reset_view,
        ).pack(side=tk.LEFT, padx=8)
        tk.Radiobutton(
            controls,
            text="Reference Trace",
            variable=self.mode,
            value="reference",
            command=self.reset_view,
        ).pack(side=tk.LEFT, padx=8)
        self.status = tk.Label(root, font=("Helvetica", 13, "bold"))
        self.status.pack(pady=10)
        self.index = 0
        self.root = root
        self.draw()
        self.root.after(450, self.advance)

    def current_frames(self) -> list[dict]:
        if self.mode.get() == "reference" and self.reference_frames:
            return self.reference_frames
        return self.student_frames

    def reset_view(self) -> None:
        self.index = 0
        self.draw()

    def draw(self) -> None:
        frames = self.current_frames()
        if not frames:
            return
        if self.index >= len(frames):
            self.index = len(frames) - 1
        frame = frames[self.index]
        expected = self.report["expected_state"]
        self.canvas.delete("all")
        for row in range(expected["board_height"]):
            for col in range(expected["board_width"]):
                x0 = col * CELL
                y0 = row * CELL
                x1 = x0 + CELL
                y1 = y0 + CELL
                fill = "#f2eadb" if (row + col) % 2 == 0 else "#e6dcc7"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#d7ccb5")

        final_food_index = frame["score"]
        foods = []
        report_path = Path(__file__).resolve().with_name("mission.json")
        if report_path.exists():
            mission = load_json(report_path)
            foods = list(zip(mission["food_x"], mission["food_y"]))
        for food_idx, (fx, fy) in enumerate(foods):
            if food_idx < final_food_index:
                continue
            x0 = fx * CELL + 14
            y0 = fy * CELL + 14
            x1 = x0 + CELL - 28
            y1 = y0 + CELL - 28
            self.canvas.create_oval(x0, y0, x1, y1, fill="#d35400", outline="")

        snake = frame["snake"]
        for index, (x, y) in enumerate(snake):
            x0 = x * CELL + 6
            y0 = y * CELL + 6
            x1 = x0 + CELL - 12
            y1 = y0 + CELL - 12
            color = "#145a32" if index == 0 else "#27ae60"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#0b3d1f", width=2)

        summary = "MATCH" if self.report["match"] else "MISMATCH"
        source = "Student" if self.mode.get() == "student" else "Reference"
        note = frame.get("note", "")
        self.status.config(
            text=(
                f"{source}  Step {frame['step']}  Move: {frame['move']}  "
                f"Score: {frame['score']}  Alive: {frame['alive']}  {summary}  {note}"
            )
        )

    def advance(self) -> None:
        frames = self.current_frames()
        if self.index < len(frames) - 1:
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
