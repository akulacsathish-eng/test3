# Part 2: Snake Control Firmware

Part 2 picks up right after the memory-vault work from Part 1. Once you recover the Part 1 password, you will use it to unlock your Snake mission for this student ID.

The Python files handle mission generation, checking, and replay. Your real job is the Y86-64 logic inside `starter_part2.ys`.

## The Part 1 to Part 2 link

1. Finish Part 1 and run the `vault` program.
2. Copy the password it prints.
3. Run `unlock_part2.py` with your student ID and that password.
4. The script verifies the password and writes `mission.json` for your Part 2 run.

That means the mission is still tied to the same deterministic story as Part 1, but the assembly work remains the center of the assignment.

## What is already provided

The starter already includes:

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

Each TODO includes:

- a short C-style comment block showing the logic
- suggested registers for that block
- a list of scratch registers that are safe to use there

You may use different registers if you preserve the values the surrounding code still needs.

## Files

- `starter_part2.ys`: the file you complete
- `unlock_part2.py`: verifies your Part 1 password and creates `mission.json`
- `run_part2.py`: runs your Y86 program and writes `output.json`
- `run_part2.sh`: small Ubuntu wrapper around `run_part2.py`
- `snake_gui.py`: replays the mission visually
- `memory_layout.txt`: exact memory map used by the runner
- `part2_support.py`: shared mission and reference helpers
- `y86_runtime.py`: the Y86 interpreter used by the runner

## How to work on it

1. Finish Part 1 and note the recovered password.
2. From the `part2` folder, unlock the mission:

```bash
python3 unlock_part2.py U0000015860 PASSWORD
```

3. Read `memory_layout.txt`.
4. Open `starter_part2.ys`.
5. Translate the four commented C snippets into Y86.
6. Use the register notes in each TODO to plan your code.
7. Run your program:

```bash
python3 run_part2.py
```

8. Replay what happened:

```bash
python3 snake_gui.py
```

The GUI overlays your snake path and the reference path on the same board.

- Green shows the student path and current snake state.
- Blue shows the reference path and expected snake state.
- Gold marks the final goal cell from the correct mission replay.

That makes it much easier to see exactly where your logic starts to drift.

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
python3 unlock_part2.py U0000015860 PASSWORD
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
