# Part 2: Snake Control Firmware

Part 2 picks up right after the memory-vault work from Part 1. The Python files handle the mission setup, checking, and replay. Your job is the Y86-64 logic inside `starter_part2.ys`.

## What changed in this starter

This version is scaffolded on purpose. You are not expected to write the whole Snake engine from a blank file.

The starter already gives you:

- register setup
- move-loop structure
- move decoding
- self-collision scan
- body shifting
- final write-back setup

You finish the four core TODO blocks that make the mission work.

## What you need to implement

In `starter_part2.ys`, complete these pieces:

1. wall collision
2. food detection
3. score and food-pointer updates after a growth move
4. mission-success logic for `result_flag`

Each TODO includes a short C-style comment block that shows the same logic in a friendlier form. That C is only a guide; you still need to write the Y86 version yourself.

## Files

- `starter_part2.ys`: the file you complete
- `mission.json`: mission data for this project
- `run_part2.py`: runs your Y86 program and writes `output.json`
- `run_part2.sh`: small Ubuntu wrapper around `run_part2.py`
- `snake_gui.py`: replays the mission visually
- `memory_layout.txt`: exact memory map used by the runner
- `part2_support.py`: shared mission and reference helpers
- `y86_runtime.py`: the Y86 interpreter used by the runner

## How to work on it

1. Read `memory_layout.txt`.
2. Open `starter_part2.ys`.
3. Translate the four commented C snippets into Y86.
4. Run your program:

```bash
python3 run_part2.py
```

5. Replay what happened:

```bash
python3 snake_gui.py
```

The GUI lets you switch between:

- `Student Trace`: what your assembly actually produced
- `Reference Trace`: the correct mission replay

That makes it much easier to see where your logic starts to drift.

## Move encoding

- `1` = up
- `2` = down
- `3` = left
- `4` = right
- `0` = end of sequence

## What gets checked

- final snake body
- final length
- score
- alive/dead flag
- food index
- result flag

If those are right, the mission is right.

## Ubuntu notes

From the `part2` folder:

```bash
python3 run_part2.py
python3 snake_gui.py
```

or:

```bash
./run_part2.sh
```

If needed:

```bash
chmod +x run_part2.sh
```
