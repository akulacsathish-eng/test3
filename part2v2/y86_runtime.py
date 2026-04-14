#!/usr/bin/env python3
"""Minimal Y86-64 interpreter for the Snake firmware project."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import re

from part2_support import (
    ALIVE_FLAG_ADDR,
    BOARD_HEIGHT_ADDR,
    BOARD_WIDTH_ADDR,
    FOOD_INDEX_ADDR,
    FOOD_X_BASE_ADDR,
    FOOD_X_PTR_ADDR,
    FOOD_Y_BASE_ADDR,
    FOOD_Y_PTR_ADDR,
    GROW_FLAG_ADDR,
    MOVES_BASE_ADDR,
    MOVES_PTR_ADDR,
    NEXT_HEAD_X_ADDR,
    NEXT_HEAD_Y_ADDR,
    NUM_MOVES_ADDR,
    RESULT_FLAG_ADDR,
    SCORE_ADDR,
    SNAKE_LENGTH_ADDR,
    SNAKE_X_BASE_ADDR,
    SNAKE_X_PTR_ADDR,
    SNAKE_Y_BASE_ADDR,
    SNAKE_Y_PTR_ADDR,
    STACK_TOP_ADDR,
    STOP_REASON_ADDR,
    TARGET_SCORE_ADDR,
    MOVE_NAMES,
)


REGISTERS = [
    "rax",
    "rbx",
    "rcx",
    "rdx",
    "rsi",
    "rdi",
    "rsp",
    "rbp",
    "r8",
    "r9",
    "r10",
    "r11",
    "r12",
    "r13",
    "r14",
]


@dataclass
class Instruction:
    op: str
    args: Tuple[object, ...]


@dataclass
class Program:
    instructions: Dict[int, Instruction] = field(default_factory=dict)
    labels: Dict[str, int] = field(default_factory=dict)
    mem_inits: Dict[int, int] = field(default_factory=dict)


class Y86Parser:
    def __init__(self, text: str) -> None:
        self.text = text

    def parse(self) -> Program:
        program = Program()
        lines = self.text.splitlines()
        loc = 0
        for raw in lines:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if ":" in line:
                label, _, rest = line.partition(":")
                if label.strip():
                    program.labels[label.strip()] = loc
                line = rest.strip()
                if not line:
                    continue
            if line.startswith(".pos"):
                loc = self._parse_imm(line.split()[1], program.labels)
                continue
            if line.startswith(".quad"):
                loc += 8
                continue
            loc += 1

        loc = 0
        for raw in lines:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if ":" in line:
                _, _, rest = line.partition(":")
                line = rest.strip()
                if not line:
                    continue
            if line.startswith(".pos"):
                loc = self._parse_imm(line.split()[1], program.labels)
                continue
            if line.startswith(".quad"):
                value = self._parse_imm(line.split(None, 1)[1], program.labels)
                program.mem_inits[loc] = value
                loc += 8
                continue
            op, *rest = line.split(None, 1)
            args = ()
            if rest:
                args = self._parse_args(op, rest[0], program.labels)
            program.instructions[loc] = Instruction(op=op, args=args)
            loc += 1
        return program

    def _parse_imm(self, token: str, labels: Dict[str, int]) -> int:
        token = token.strip()
        if token.startswith("$"):
            token = token[1:]
        if token.startswith("0x") or token.startswith("0X"):
            return int(token, 16)
        if re.fullmatch(r"-?\d+", token):
            return int(token)
        if token in labels:
            return labels[token]
        raise ValueError(f"Unknown immediate or label: {token}")

    def _parse_register(self, token: str) -> str:
        token = token.strip()
        if not token.startswith("%"):
            raise ValueError(f"Expected register, got {token}")
        reg = token[1:]
        if reg not in REGISTERS:
            raise ValueError(f"Unknown register {token}")
        return reg

    def _split_args(self, arg_string: str) -> List[str]:
        parts: List[str] = []
        current: List[str] = []
        depth = 0
        for ch in arg_string:
            if ch == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            current.append(ch)
        if current:
            parts.append("".join(current).strip())
        return parts

    def _parse_mem(self, token: str, labels: Dict[str, int]) -> Tuple[int, str]:
        match = re.fullmatch(r"([^()]*)\((%[a-z0-9]+)\)", token.strip())
        if not match:
            raise ValueError(f"Invalid memory operand {token}")
        disp_str, base_reg = match.groups()
        disp = 0 if disp_str == "" else self._parse_imm(disp_str, labels)
        return disp, self._parse_register(base_reg)

    def _parse_args(self, op: str, arg_string: str, labels: Dict[str, int]) -> Tuple[object, ...]:
        args = self._split_args(arg_string)
        if op == "irmovq":
            return (self._parse_imm(args[0], labels), self._parse_register(args[1]))
        if op in {"rrmovq", "addq", "subq", "andq", "xorq", "cmove", "cmovne", "cmovg", "cmovge", "cmovl", "cmovle"}:
            return (self._parse_register(args[0]), self._parse_register(args[1]))
        if op == "mrmovq":
            disp, base = self._parse_mem(args[0], labels)
            return (disp, base, self._parse_register(args[1]))
        if op == "rmmovq":
            reg = self._parse_register(args[0])
            disp, base = self._parse_mem(args[1], labels)
            return (reg, disp, base)
        if op in {"jmp", "je", "jne", "jg", "jge", "jl", "jle"}:
            return (self._parse_imm(args[0], labels),)
        if op in {"halt", "ret"}:
            return ()
        raise ValueError(f"Unsupported operation {op}")


class Y86Machine:
    def __init__(self, program: Program, mission: Dict[str, object]) -> None:
        self.program = program
        self.mission = mission
        self.memory: Dict[int, int] = dict(program.mem_inits)
        self.registers = {reg: 0 for reg in REGISTERS}
        self.pc = 0
        self.ZF = 0
        self.SF = 0
        self.OF = 0
        self.halted = False
        self._load_mission(mission)

    def _wrap(self, value: int) -> int:
        value &= 0xFFFFFFFFFFFFFFFF
        if value & (1 << 63):
            value -= 1 << 64
        return value

    def _load_mission(self, mission: Dict[str, object]) -> None:
        self.memory[BOARD_WIDTH_ADDR] = int(mission["board_width"])
        self.memory[BOARD_HEIGHT_ADDR] = int(mission["board_height"])
        self.memory[SNAKE_LENGTH_ADDR] = int(mission["initial_length"])
        self.memory[ALIVE_FLAG_ADDR] = 1
        self.memory[SCORE_ADDR] = 0
        self.memory[FOOD_INDEX_ADDR] = 0
        self.memory[NUM_MOVES_ADDR] = len(mission["moves"])
        self.memory[RESULT_FLAG_ADDR] = 0
        self.memory[TARGET_SCORE_ADDR] = int(mission["target_score"])
        self.memory[MOVES_PTR_ADDR] = MOVES_BASE_ADDR
        self.memory[SNAKE_X_PTR_ADDR] = SNAKE_X_BASE_ADDR
        self.memory[SNAKE_Y_PTR_ADDR] = SNAKE_Y_BASE_ADDR
        self.memory[FOOD_X_PTR_ADDR] = FOOD_X_BASE_ADDR
        self.memory[FOOD_Y_PTR_ADDR] = FOOD_Y_BASE_ADDR
        self.memory[NEXT_HEAD_X_ADDR] = 0
        self.memory[NEXT_HEAD_Y_ADDR] = 0
        self.memory[GROW_FLAG_ADDR] = 0
        self.memory[STOP_REASON_ADDR] = 0

        for index, move in enumerate(mission["moves"]):
            self.memory[MOVES_BASE_ADDR + index * 8] = int(move)
        for index, value in enumerate(mission["initial_snake_x"]):
            self.memory[SNAKE_X_BASE_ADDR + index * 8] = int(value)
        for index, value in enumerate(mission["initial_snake_y"]):
            self.memory[SNAKE_Y_BASE_ADDR + index * 8] = int(value)
        for index, value in enumerate(mission["food_x"]):
            self.memory[FOOD_X_BASE_ADDR + index * 8] = int(value)
        for index, value in enumerate(mission["food_y"]):
            self.memory[FOOD_Y_BASE_ADDR + index * 8] = int(value)

        self.registers["rsp"] = STACK_TOP_ADDR
        self.memory[STACK_TOP_ADDR] = -1

    def _read(self, addr: int) -> int:
        return self.memory.get(addr, 0)

    def _write(self, addr: int, value: int) -> None:
        self.memory[addr] = self._wrap(value)

    def _set_reg(self, reg: str, value: int) -> None:
        self.registers[reg] = self._wrap(value)

    def _get_reg(self, reg: str) -> int:
        return self.registers[reg]

    def _set_cc(self, result: int, a: int, b: int, op: str) -> None:
        result = self._wrap(result)
        self.ZF = 1 if result == 0 else 0
        self.SF = 1 if result < 0 else 0
        a_neg = 1 if a < 0 else 0
        b_neg = 1 if b < 0 else 0
        r_neg = 1 if result < 0 else 0
        if op == "add":
            self.OF = 1 if a_neg == b_neg and r_neg != a_neg else 0
        elif op == "sub":
            self.OF = 1 if a_neg != b_neg and r_neg != b_neg else 0
        else:
            self.OF = 0

    def _condition(self, op: str) -> bool:
        if op in {"jmp"}:
            return True
        if op in {"je", "cmove"}:
            return self.ZF == 1
        if op in {"jne", "cmovne"}:
            return self.ZF == 0
        if op in {"jg", "cmovg"}:
            return self.ZF == 0 and self.SF == self.OF
        if op in {"jge", "cmovge"}:
            return self.SF == self.OF
        if op in {"jl", "cmovl"}:
            return self.SF != self.OF
        if op in {"jle", "cmovle"}:
            return self.ZF == 1 or self.SF != self.OF
        raise ValueError(f"Unknown condition op {op}")

    def _instruction_text(self, instr: Instruction) -> str:
        if not instr.args:
            return instr.op
        parts: List[str] = []
        for arg in instr.args:
            parts.append(str(arg))
        return f"{instr.op} " + ", ".join(parts)

    def _capture_frame(self, step: int, move: str, note: str) -> Dict[str, object]:
        state = self.extract_state()
        display_length = max(int(self.mission["initial_length"]) + int(state["score"]), int(state["snake_length"]))
        snake = [
            (
                self._read(SNAKE_X_BASE_ADDR + index * 8),
                self._read(SNAKE_Y_BASE_ADDR + index * 8),
            )
            for index in range(display_length)
        ]
        return {
            "step": step,
            "move": move,
            "snake": snake,
            "score": state["score"],
            "alive": state["alive"],
            "pc": self.pc,
            "note": note,
        }

    def _state_signature(self) -> Tuple[object, ...]:
        state = self.extract_state()
        return (
            tuple(state["snake_x"]),
            tuple(state["snake_y"]),
            state["snake_length"],
            state["alive"],
            state["score"],
            state["food_index"],
            state["result"],
            state["stop_reason"],
        )

    def step(self) -> Dict[str, object]:
        if self.pc not in self.program.instructions:
            self.halted = True
            return {"pc": self.pc, "op": "halt", "text": "halt", "next_pc": self.pc}

        current_pc = self.pc
        instr = self.program.instructions[self.pc]
        op = instr.op
        args = instr.args

        if op == "irmovq":
            value, reg = args
            self._set_reg(reg, int(value))
            self.pc += 1
        elif op == "rrmovq":
            src, dst = args
            self._set_reg(dst, self._get_reg(src))
            self.pc += 1
        elif op == "mrmovq":
            disp, base, dst = args
            addr = self._get_reg(base) + int(disp)
            self._set_reg(dst, self._read(addr))
            self.pc += 1
        elif op == "rmmovq":
            src, disp, base = args
            addr = self._get_reg(base) + int(disp)
            self._write(addr, self._get_reg(src))
            self.pc += 1
        elif op in {"addq", "subq", "andq", "xorq"}:
            src, dst = args
            a = self._get_reg(src)
            b = self._get_reg(dst)
            if op == "addq":
                result = b + a
                self._set_reg(dst, result)
                self._set_cc(result, a, b, "add")
            elif op == "subq":
                result = b - a
                self._set_reg(dst, result)
                self._set_cc(result, a, b, "sub")
            elif op == "andq":
                result = b & a
                self._set_reg(dst, result)
                self.ZF = 1 if result == 0 else 0
                self.SF = 1 if result < 0 else 0
                self.OF = 0
            else:
                result = b ^ a
                self._set_reg(dst, result)
                self.ZF = 1 if result == 0 else 0
                self.SF = 1 if result < 0 else 0
                self.OF = 0
            self.pc += 1
        elif op in {"cmove", "cmovne", "cmovg", "cmovge", "cmovl", "cmovle"}:
            src, dst = args
            if self._condition(op):
                self._set_reg(dst, self._get_reg(src))
            self.pc += 1
        elif op in {"jmp", "je", "jne", "jg", "jge", "jl", "jle"}:
            (dest,) = args
            if self._condition(op):
                self.pc = int(dest)
            else:
                self.pc += 1
        elif op == "ret":
            ret_addr = self._read(self._get_reg("rsp"))
            if ret_addr < 0:
                self.halted = True
            else:
                self._set_reg("rsp", self._get_reg("rsp") + 8)
                self.pc = ret_addr
        elif op == "halt":
            self.halted = True
        else:
            raise RuntimeError(f"Unsupported instruction {op}")

        return {
            "pc": current_pc,
            "op": op,
            "text": self._instruction_text(instr),
            "next_pc": self.pc,
        }

    def run(self, max_steps: int = 200000) -> None:
        steps = 0
        while not self.halted and steps < max_steps:
            self.step()
            steps += 1
        if steps >= max_steps:
            raise RuntimeError("Execution exceeded the instruction limit.")

    def run_with_trace(self, max_steps: int = 200000) -> List[Dict[str, object]]:
        frames: List[Dict[str, object]] = [self._capture_frame(0, "START", "Initial state")]
        last_signature = self._state_signature()
        move_loop_pc = self.program.labels.get("move_loop")
        steps = 0
        completed_moves = 0

        while not self.halted and steps < max_steps:
            info = self.step()
            steps += 1
            current_signature = self._state_signature()

            if move_loop_pc is not None:
                if self.pc == move_loop_pc and current_signature != last_signature:
                    move_code = 0
                    if completed_moves < len(self.mission["moves"]):
                        move_code = int(self.mission["moves"][completed_moves])
                    move_name = MOVE_NAMES.get(move_code, "END")
                    frames.append(
                        self._capture_frame(
                            completed_moves + 1,
                            move_name,
                            f"Student state after move {completed_moves + 1}",
                        )
                    )
                    completed_moves += 1
                    last_signature = current_signature
            elif current_signature != last_signature:
                frames.append(
                    self._capture_frame(
                        len(frames),
                        "TRACE",
                        f"Student state change after {info['text']}",
                    )
                )
                last_signature = current_signature

        if steps >= max_steps:
            raise RuntimeError("Execution exceeded the instruction limit.")

        final_signature = self._state_signature()
        if final_signature != last_signature or len(frames) == 1:
            move_code = 0
            if completed_moves < len(self.mission["moves"]):
                move_code = int(self.mission["moves"][completed_moves])
            move_name = MOVE_NAMES.get(move_code, "END")
            frames.append(
                self._capture_frame(
                    completed_moves + 1,
                    move_name,
                    "Final student state",
                )
            )
        return frames

    def extract_state(self) -> Dict[str, object]:
        length = self._read(SNAKE_LENGTH_ADDR)
        snake_x = [self._read(SNAKE_X_BASE_ADDR + i * 8) for i in range(length)]
        snake_y = [self._read(SNAKE_Y_BASE_ADDR + i * 8) for i in range(length)]
        return {
            "board_width": self._read(BOARD_WIDTH_ADDR),
            "board_height": self._read(BOARD_HEIGHT_ADDR),
            "snake_x": snake_x,
            "snake_y": snake_y,
            "snake_length": length,
            "alive": self._read(ALIVE_FLAG_ADDR),
            "score": self._read(SCORE_ADDR),
            "food_index": self._read(FOOD_INDEX_ADDR),
            "result": self._read(RESULT_FLAG_ADDR),
            "stop_reason": self._read(STOP_REASON_ADDR),
        }
