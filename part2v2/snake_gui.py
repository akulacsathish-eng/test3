#!/usr/bin/env python3


from __future__ import annotations

from pathlib import Path
import json
import tkinter as tk


CELL = 48
FRAME_DELAY_MS = 900
MISMATCH_PAUSE_MS = 1800

WINDOW_BG = "#0d1b14"
PANEL_BG = "#173226"
PANEL_ALT = "#204234"
TEXT_MAIN = "#eef7ef"
TEXT_MUTED = "#b7d3bc"
ACCENT_GOLD = "#f4d03f"
ACCENT_GREEN = "#2ecc71"
ACCENT_GREEN_DARK = "#145a32"
ACCENT_BLUE = "#5dade2"
ACCENT_BLUE_DARK = "#1f618d"
ACCENT_RED = "#e74c3c"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class SnakeReplay:
    def __init__(self, root: tk.Tk, report: dict) -> None:
        self.report = report
        self.student_frames = report.get("student_frames", report.get("frames", []))
        self.reference_frames = report.get("reference_frames", [])
        self.root = root
        self.root.configure(bg=WINDOW_BG)

        width = report["expected_state"]["board_width"]
        height = report["expected_state"]["board_height"]

        shell = tk.Frame(root, bg=WINDOW_BG, padx=20, pady=18)
        shell.pack()

        header = tk.Frame(shell, bg=WINDOW_BG)
        header.pack(fill=tk.X, pady=(0, 14))
        tk.Label(
            header,
            text="Snake Control Firmware",
            font=("Helvetica", 22, "bold"),
            fg=ACCENT_GOLD,
            bg=WINDOW_BG,
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Compare your snake to the ghost route and watch for the first wrong move.",
            font=("Helvetica", 11),
            fg=TEXT_MUTED,
            bg=WINDOW_BG,
        ).pack(anchor="w", pady=(4, 0))

        content = tk.Frame(shell, bg=WINDOW_BG)
        content.pack()

        board_card = tk.Frame(
            content,
            bg=PANEL_BG,
            padx=14,
            pady=14,
            highlightbackground="#2d5746",
            highlightthickness=2,
        )
        board_card.pack(side=tk.LEFT, padx=(0, 16))
        self.canvas = tk.Canvas(
            board_card,
            width=width * CELL,
            height=height * CELL,
            bg="#10271f",
            bd=0,
            highlightthickness=0,
        )
        self.canvas.pack()

        hud = tk.Frame(
            content,
            bg=PANEL_BG,
            width=290,
            padx=16,
            pady=16,
            highlightbackground="#2d5746",
            highlightthickness=2,
        )
        hud.pack(side=tk.LEFT, fill=tk.Y)
        hud.pack_propagate(False)

        self.status_badge = tk.Label(
            hud,
            text="ON TRACK",
            font=("Helvetica", 18, "bold"),
            fg=WINDOW_BG,
            bg=ACCENT_GREEN,
            padx=12,
            pady=8,
        )
        self.status_badge.pack(fill=tk.X)

        legend = tk.Frame(hud, bg=PANEL_BG, pady=12)
        legend.pack(fill=tk.X)
        self.legend_item(legend, ACCENT_GREEN, "Your snake")
        self.legend_item(legend, ACCENT_BLUE, "Ghost snake")
        self.legend_item(legend, ACCENT_GOLD, "Goal")

        stats = tk.Frame(hud, bg=PANEL_BG)
        stats.pack(fill=tk.X, pady=(6, 10))
        self.step_value = self.make_stat(stats, "Step")
        self.score_value = self.make_stat(stats, "Score")
        self.alive_value = self.make_stat(stats, "Alive")
        self.goal_value = self.make_stat(stats, "Goal")

        message_card = tk.Frame(hud, bg=PANEL_ALT, padx=12, pady=12)
        message_card.pack(fill=tk.X, pady=(6, 10))
        self.hint_title = tk.Label(
            message_card,
            text="Run Status",
            font=("Helvetica", 12, "bold"),
            fg=TEXT_MAIN,
            bg=PANEL_ALT,
        )
        self.hint_title.pack(anchor="w")
        self.hint_text = tk.Label(
            message_card,
            text="",
            justify=tk.LEFT,
            wraplength=230,
            font=("Helvetica", 11),
            fg=TEXT_MUTED,
            bg=PANEL_ALT,
        )
        self.hint_text.pack(anchor="w", pady=(8, 0))

        self.status = tk.Label(
            hud,
            text="",
            justify=tk.LEFT,
            wraplength=250,
            font=("Courier New", 10, "bold"),
            fg=TEXT_MUTED,
            bg=PANEL_BG,
        )
        self.status.pack(fill=tk.X, pady=(8, 0))

        self.index = 0
        self.mission = self.load_mission()
        self.goal = self.reference_frames[-1]["snake"][0] if self.reference_frames else None
        self.first_mismatch = self.find_first_mismatch()
        self.mismatch_pause_used = False
        self.draw()
        self.root.after(FRAME_DELAY_MS, self.advance)

    def legend_item(self, parent: tk.Widget, color: str, text: str) -> None:
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(anchor="w", pady=2)
        swatch = tk.Canvas(row, width=14, height=14, bg=PANEL_BG, bd=0, highlightthickness=0)
        swatch.pack(side=tk.LEFT, padx=(0, 8))
        swatch.create_oval(2, 2, 12, 12, fill=color, outline="")
        tk.Label(row, text=text, font=("Helvetica", 10), fg=TEXT_MUTED, bg=PANEL_BG).pack(side=tk.LEFT)

    def make_stat(self, parent: tk.Widget, label: str) -> tk.Label:
        card = tk.Frame(parent, bg=PANEL_ALT, padx=10, pady=8)
        card.pack(fill=tk.X, pady=4)
        tk.Label(card, text=label, font=("Helvetica", 9, "bold"), fg=TEXT_MUTED, bg=PANEL_ALT).pack(anchor="w")
        value = tk.Label(card, text="", font=("Helvetica", 15, "bold"), fg=TEXT_MAIN, bg=PANEL_ALT)
        value.pack(anchor="w")
        return value

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
        self.canvas.create_oval(x0, y0, x1, y1, fill=ACCENT_GOLD, outline="#9c640c", width=3)
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
            fill = "#d35400" if food_idx >= eaten else "#7f5539"
            x0 = fx * CELL + 14
            y0 = fy * CELL + 14
            x1 = x0 + CELL - 28
            y1 = y0 + CELL - 28
            self.canvas.create_oval(x0, y0, x1, y1, fill=fill, outline="")

    def draw_path(
        self,
        points: list[tuple[int, int]],
        color: str,
        width: int,
        dash: tuple[int, int] | None = None,
        glow: str | None = None,
    ) -> None:
        if not points:
            return
        coords: list[float] = []
        for x, y in points:
            coords.extend([x * CELL + CELL / 2, y * CELL + CELL / 2])
        if len(coords) >= 4:
            if glow is not None:
                self.canvas.create_line(*coords, fill=glow, width=width + 4, dash=dash, capstyle=tk.ROUND)
            self.canvas.create_line(*coords, fill=color, width=width, dash=dash, capstyle=tk.ROUND)
        for x, y in points:
            cx = x * CELL + CELL / 2
            cy = y * CELL + CELL / 2
            if glow is not None:
                self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=glow, outline="")
            self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=color, outline="")

    def draw_snake(
        self,
        snake: list[list[int]],
        head_fill: str,
        body_fill: str,
        outline: str,
        inset: int,
        width: int,
    ) -> None:
        for index, (x, y) in enumerate(snake):
            x0 = x * CELL + inset
            y0 = y * CELL + inset
            x1 = x0 + CELL - (2 * inset)
            y1 = y0 + CELL - (2 * inset)
            fill = head_fill if index == 0 else body_fill
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width)

    def draw_mismatch(self, student_frame: dict | None, reference_frame: dict | None) -> None:
        if student_frame is None or reference_frame is None:
            return
        student_head = tuple(student_frame["snake"][0])
        reference_head = tuple(reference_frame["snake"][0])
        if student_head == reference_head:
            return

        for x, y, color in (
            (student_head[0], student_head[1], ACCENT_RED),
            (reference_head[0], reference_head[1], ACCENT_BLUE_DARK),
        ):
            x0 = x * CELL + 3
            y0 = y * CELL + 3
            x1 = x0 + CELL - 6
            y1 = y0 + CELL - 6
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=3)

    def update_hud(self, student_frame: dict | None, reference_frame: dict | None) -> None:
        final_index = max(len(self.student_frames), len(self.reference_frames)) - 1
        target_score = self.mission.get("target_score", "-") if self.mission is not None else "-"
        goal_text = f"{tuple(self.goal)}" if self.goal is not None else "-"
        student_score = student_frame["score"] if student_frame is not None else "-"
        student_alive = "Yes" if student_frame is not None and student_frame["alive"] else "No"

        self.step_value.config(text=f"{self.index} / {final_index}")
        self.score_value.config(text=f"{student_score} / {target_score}")
        self.alive_value.config(text=student_alive)
        self.goal_value.config(text=goal_text)

        badge_text = "ON TRACK"
        badge_fg = WINDOW_BG
        badge_bg = ACCENT_GREEN
        hint_title = "Run Status"
        hint_text = "Your snake is matching the expected route."
        status_lines = [f"Move: {student_frame['move'] if student_frame is not None else '-'}"]

        if student_frame is not None and reference_frame is not None:
            student_head = tuple(student_frame["snake"][0])
            reference_head = tuple(reference_frame["snake"][0])
            if student_head != reference_head:
                badge_text = "OFF COURSE HERE" if self.index == self.first_mismatch else "OFF COURSE"
                badge_fg = TEXT_MAIN
                badge_bg = ACCENT_RED
                hint_title = "Head Check"
                hint_text = (
                    f"Your head is at {student_head}.\n"
                    f"The expected head is {reference_head}."
                )
                status_lines = [
                    f"Your move: {student_frame['move']}",
                    f"Expected move: {reference_frame['move']}",
                    f"Score: {student_frame['score']} / {reference_frame['score']}",
                ]
            elif self.index >= final_index and self.report.get("mission_success"):
                badge_text = "MISSION COMPLETE"
                badge_fg = WINDOW_BG
                badge_bg = ACCENT_GOLD
                hint_title = "Goal Reached"
                hint_text = "Your snake stayed on route and reached the goal."
                status_lines = [
                    f"Final score: {student_frame['score']} / {target_score}",
                    f"Goal cell: {goal_text}",
                ]
            elif self.index >= final_index:
                badge_text = "RUN FINISHED"
                badge_fg = TEXT_MAIN
                badge_bg = ACCENT_BLUE_DARK
                hint_title = "Final Check"
                hint_text = "The replay ended. Compare the board state with the ghost snake."

        self.status_badge.config(text=badge_text, fg=badge_fg, bg=badge_bg)
        self.hint_title.config(text=hint_title)
        self.hint_text.config(text=hint_text)
        self.status.config(text="\n".join(status_lines))

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
                fill = "#163428" if (row + col) % 2 == 0 else "#1d3d2f"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#2b5843")

        self.draw_goal()
        self.draw_foods(reference_frame)
        self.draw_path(self.head_path(self.reference_frames), "#7fd3ff", 5, glow="#245a7a")
        self.draw_path(self.head_path(self.student_frames), ACCENT_GREEN, 6)

        if reference_frame is not None:
            self.draw_snake(reference_frame["snake"], "#8ecdf3", "#3d7ea6", ACCENT_BLUE_DARK, inset=4, width=2)
        if student_frame is not None:
            self.draw_snake(student_frame["snake"], ACCENT_GREEN_DARK, ACCENT_GREEN, "#0b3d1f", inset=10, width=2)

        self.draw_mismatch(student_frame, reference_frame)
        self.update_hud(student_frame, reference_frame)

    def advance(self) -> None:
        max_frames = max(len(self.student_frames), len(self.reference_frames))
        if self.index < max_frames - 1:
            self.index += 1
            self.draw()
            delay = FRAME_DELAY_MS
            if (
                self.first_mismatch is not None
                and self.index == self.first_mismatch
                and not self.mismatch_pause_used
            ):
                delay = MISMATCH_PAUSE_MS
                self.mismatch_pause_used = True
            self.root.after(delay, self.advance)


def main() -> None:
    part2_dir = Path(__file__).resolve().parent
    report = load_json(part2_dir / "output.json")
    root = tk.Tk()
    root.title("Snake Control Firmware Replay")
    SnakeReplay(root, report)
    root.mainloop()


if __name__ == "__main__":
    main()
