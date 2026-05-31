#!/usr/bin/env python3
"""
████████╗███████╗████████╗██████╗ ██╗███████╗
╚══██╔══╝██╔════╝╚══██╔══╝██╔══██╗██║██╔════╝
    ██║    █████╗       ██║    ██████╔╝██║███████╗
    ██║    ██╔══╝       ██║    ██╔══██╗██║╚════██║
    ██║    ███████╗    ██║    ██║  ██║██║███████║
    ╚═╝    ╚══════╝    ╚═╝    ╚═╝  ╚═╝╚═╝╚══════╝
  A full retro Tetris game with AI — Python 3.12 + Pygame
"""

import pygame
import random
import sys
import math
import struct

# ═══════════════════════════════════════════════════════════════
#  INITIALIZATION
# ═══════════════════════════════════════════════════════════════
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# ═══════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════
CELL = 30
COLS = 10
ROWS = 20
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
SIDEBAR_W = 190
PAD = 12
BORDER_W = 4

SCREEN_W = PAD + BORDER_W + BOARD_W + BORDER_W + PAD + SIDEBAR_W + PAD
SCREEN_H = PAD + BORDER_W + BOARD_H + BORDER_W + PAD

BOARD_X = PAD + BORDER_W
BOARD_Y = PAD + BORDER_W
SIDEBAR_X = BOARD_X + BOARD_W + BORDER_W + PAD

FPS = 30

# ═══════════════════════════════════════════════════════════════
#  COLORS
# ═══════════════════════════════════════════════════════════════
BG = (8, 8, 24)
BOARD_BG = (12, 12, 32)
GRID_CLR = (28, 28, 52)
BORDER_CLR = (70, 70, 120)
BORDER_HI = (110, 110, 170)
TEXT_CLR = (210, 210, 230)
TEXT_DIM = (100, 100, 140)
FLASH = (255, 255, 255)
GRAY_BLOCK = (70, 70, 70)

PIECE_CLR = {
    "I": (0, 235, 235),
    "O": (235, 235, 0),
    "T": (170, 0, 235),
    "S": (0, 235, 0),
    "Z": (235, 0, 0),
    "J": (30, 30, 235),
    "L": (235, 145, 0),
}


def darken(c, f=0.4):
    return tuple(max(0, int(v * f)) for v in c)


def lighten(c, f=1.5):
    return tuple(min(255, int(v * f)) for v in c)


# ═══════════════════════════════════════════════════════════════
#  SHAPE DEFINITIONS & ROTATION
# ═══════════════════════════════════════════════════════════════
SHAPE_GRID = {
    "I": [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1], [0, 0, 0]],
    "S": [[0, 1, 1], [1, 1, 0], [0, 0, 0]],
    "Z": [[1, 1, 0], [0, 1, 1], [0, 0, 0]],
    "J": [[1, 0, 0], [1, 1, 1], [0, 0, 0]],
    "L": [[0, 0, 1], [1, 1, 1], [0, 0, 0]],
}


def _rot_cw(g):
    n, m = len(g), len(g[0])
    return [[g[n - 1 - r][c] for r in range(n)] for c in range(m)]


ROT = {}
for _pt, _g in SHAPE_GRID.items():
    _rs = [_g]
    for _ in range(3):
        _rs.append(_rot_cw(_rs[-1]))
    ROT[_pt] = _rs

# ═══════════════════════════════════════════════════════════════
#  SRS WALL-KICK DATA (x+ right, y+ down)
# ═══════════════════════════════════════════════════════════════
WK_JLSTZ = {
    (0, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (1, 0): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (1, 2): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (2, 1): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (2, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (3, 2): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (3, 0): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (0, 3): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
}

WK_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, -1), (-1, 2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, 2), (-2, -1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, -2), (2, 1)],
}

# ═══════════════════════════════════════════════════════════════
#  SOUND GENERATION
# ═══════════════════════════════════════════════════════════════
SOUND_ON = False
SND = {}


def _gen_snd(freq, dur=0.1, vol=0.25, wave="square"):
    sr = 44100
    n = int(sr * dur)
    buf = bytearray(n * 2)
    for i in range(n):
        t = i / sr
        if wave == "square":
            v = vol * 32767 * (1 if math.sin(2 * math.pi * freq * t) > 0 else -1)
        else:
            v = vol * 32767 * math.sin(2 * math.pi * freq * t)
        att = min(1.0, i / max(1, sr * 0.005))
        rel = min(1.0, (n - i) / max(1, sr * 0.02))
        v = int(v * att * rel)
        struct.pack_into("<h", buf, i * 2, max(-32768, min(32767, v)))
    return pygame.mixer.Sound(buffer=bytes(buf))


try:
    SND["move"] = _gen_snd(220, 0.04, 0.15)
    SND["rotate"] = _gen_snd(330, 0.05, 0.15)
    SND["drop"] = _gen_snd(110, 0.12, 0.25)
    SND["clear"] = _gen_snd(500, 0.18, 0.25, "sine")
    SND["tetris"] = _gen_snd(700, 0.30, 0.25, "sine")
    SND["hold"] = _gen_snd(275, 0.04, 0.15)
    SND["over"] = _gen_snd(90, 0.6, 0.25)
    SND["level"] = _gen_snd(440, 0.08, 0.2, "sine")
    SOUND_ON = True
except Exception:
    pass


def play(name):
    if SOUND_ON and name in SND:
        SND[name].play()


# ═══════════════════════════════════════════════════════════════
#  DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("RETRO TETRIS + AI")

_scanlines = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
for _y in range(0, SCREEN_H, 3):
    pygame.draw.line(_scanlines, (0, 0, 0, 35), (0, _y), (SCREEN_W, _y))


def draw_block(surf, x, y, sz, color, ghost=False):
    if ghost:
        r = pygame.Rect(x + 1, y + 1, sz - 2, sz - 2)
        pygame.draw.rect(surf, color, r, 2)
        return
    rect = pygame.Rect(x, y, sz, sz)
    pygame.draw.rect(surf, color, rect)
    hi = lighten(color, 1.6)
    sh = darken(color, 0.35)
    pygame.draw.line(surf, hi, (x, y), (x + sz - 1, y), 2)
    pygame.draw.line(surf, hi, (x, y), (x, y + sz - 1), 2)
    pygame.draw.line(surf, sh, (x + sz - 1, y + 1), (x + sz - 1, y + sz - 1), 2)
    pygame.draw.line(surf, sh, (x + 1, y + sz - 1), (x + sz - 1, y + sz - 1), 2)
    inner = lighten(color, 1.2)
    ir = pygame.Rect(x + 4, y + 4, sz - 8, sz - 8)
    if ir.w > 0 and ir.h > 0:
        pygame.draw.rect(surf, inner, ir, 1)


def draw_text(surf, text, font, x, y, color, shadow=True, center=False):
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        sr = s.get_rect(center=(x + 2, y + 2)) if center else s.get_rect(topleft=(x + 2, y + 2))
        surf.blit(s, sr)
    t = font.render(text, True, color)
    tr = t.get_rect(center=(x, y)) if center else t.get_rect(topleft=(x, y))
    surf.blit(t, tr)


# ═══════════════════════════════════════════════════════════════
#  PIECE CLASS
# ═══════════════════════════════════════════════════════════════
class Piece:
    def __init__(self, pt, x=None, y=None):
        self.type = pt
        self.rot = 0
        grid = ROT[pt][0]
        self.x = x if x is not None else COLS // 2 - len(grid[0]) // 2
        self.y = y if y is not None else self._spawn_y()
        self.color = PIECE_CLR[pt]

    def _spawn_y(self):
        g = ROT[self.type][0]
        for r, row in enumerate(g):
            if any(row):
                return -r
        return 0

    def cells(self, rot=None, dx=0, dy=0):
        if rot is None:
            rot = self.rot
        g = ROT[self.type][rot]
        out = []
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v:
                    out.append((self.x + c + dx, self.y + r + dy))
        return out


# ═══════════════════════════════════════════════════════════════
#  GAME CLASS
# ═══════════════════════════════════════════════════════════════
class Game:
    GRAVITY = [
        800, 720, 630, 550, 470, 380, 300, 220, 150, 100,
        80, 70, 60, 50, 40, 30, 20, 15, 10, 5,
    ]
    LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}
    CLEAR_DUR = 400

    def __init__(self):
        self.f_big = pygame.font.Font(None, 52)
        self.f_med = pygame.font.Font(None, 30)
        self.f_sm = pygame.font.Font(None, 22)
        self.f_xs = pygame.font.Font(None, 17)
        self.high_score = 0
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.nxt = []
        for _ in range(3):
            self.nxt.append(self._pull())
        self.cur = self._spawn()
        self.held = None
        self.can_hold = True
        self.score = 0
        self.lines = 0
        self.level = 0
        self.gravity_ms = self.GRAVITY[0]
        self.grav_t = 0
        self.lock_t = 0
        self.locking = False
        self.lock_moves = 0
        self.soft = False
        self.das_dir = 0
        self.das_t = 0
        self.das_on = False
        self.clearing = []
        self.clear_t = 0
        self.clear_flash = 0
        self.msg = ""
        self.msg_t = 0
        self.state = "play"
        self.particles = []
        self.go_row = 0
        self.go_t = 0
        self.stats = {p: 0 for p in "IOTZSLJ"}

        # AI State
        self.ai_mode = False
        self.ai_target = None
        self.ai_phase = 0
        self.ai_timer = 0
        self.ai_stuck_counter = 0

    # ── bag randomiser ──────────────────────────────────────
    def _pull(self):
        if not self.bag:
            self.bag = list("IOTZSLJ")
            random.shuffle(self.bag)
        return self.bag.pop()

    def _spawn(self):
        pt = self.nxt.pop(0)
        self.nxt.append(self._pull())
        return Piece(pt)

    # ── collision ───────────────────────────────────────────
    def _valid(self, piece, dx=0, dy=0, rot=None, board=None):
        if board is None:
            board = self.board
        for cx, cy in piece.cells(rot, dx, dy):
            if cx < 0 or cx >= COLS or cy >= ROWS:
                return False
            if cy >= 0 and board[cy][cx] is not None:
                return False
        return True

    # ── rotation with SRS kicks ─────────────────────────────
    def _try_rot(self, d):
        old = self.cur.rot
        new = (old + d) % 4
        pt = self.cur.type
        if pt == "O":
            kicks = [(0, 0)]
        elif pt == "I":
            kicks = WK_I.get((old, new), [(0, 0)])
        else:
            kicks = WK_JLSTZ.get((old, new), [(0, 0)])
        for dx, dy in kicks:
            if self._valid(self.cur, dx, dy, new):
                self.cur.x += dx
                self.cur.y += dy
                self.cur.rot = new
                self._touch_lock()
                play("rotate")
                return True
        return False

    # ── movement ────────────────────────────────────────────
    def _move(self, dx, dy):
        if self._valid(self.cur, dx, dy):
            self.cur.x += dx
            self.cur.y += dy
            if dx != 0:
                self._touch_lock()
            return True
        return False

    def _touch_lock(self):
        if self.locking and self.lock_moves < 15:
            self.lock_t = 0
            self.lock_moves += 1

    # ── ghost Y ─────────────────────────────────────────────
    def _ghost_y(self):
        gy = self.cur.y
        while self._valid(self.cur, dy=gy - self.cur.y + 1):
            gy += 1
        return gy

    # ── hard drop ───────────────────────────────────────────
    def _hard_drop(self):
        d = 0
        while self._valid(self.cur, dy=1):
            self.cur.y += 1
            d += 1
        self.score += d * 2
        self._lock()
        play("drop")

    # ── lock piece ──────────────────────────────────────────
    def _lock(self):
        for cx, cy in self.cur.cells():
            if 0 <= cy < ROWS and 0 <= cx < COLS:
                self.board[cy][cx] = self.cur.type
        self.stats[self.cur.type] = self.stats.get(self.cur.type, 0) + 1

        full = [r for r in range(ROWS) if all(self.board[r][c] is not None for c in range(COLS))]
        if full:
            self.clearing = full
            self.clear_t = 0
            self.clear_flash = 0
            for r in full:
                for c in range(COLS):
                    clr = PIECE_CLR.get(self.board[r][c], FLASH)
                    for _ in range(4):
                        self.particles.append({
                            "x": BOARD_X + c * CELL + CELL // 2,
                            "y": BOARD_Y + r * CELL + CELL // 2,
                            "vx": random.uniform(-4, 4),
                            "vy": random.uniform(-6, -1),
                            "life": random.randint(20, 45),
                            "ml": 45,
                            "c": lighten(clr, 1.3),
                            "s": random.randint(2, 5),
                        })
            n = len(full)
            self.score += self.LINE_SCORES.get(n, 0) * (self.level + 1)
            self.lines += n
            nl = self.lines // 10
            if nl > self.level:
                self.level = nl
                self.gravity_ms = self.GRAVITY[min(self.level, len(self.GRAVITY) - 1)]
                play("level")
            msgs = {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE", 4: "TETRIS!"}
            self.msg = msgs.get(n, "")
            self.msg_t = 1200
            play("tetris" if n == 4 else "clear")
        else:
            self._next_piece()

    def _next_piece(self):
        self.cur = self._spawn()
        self.can_hold = True
        self.locking = False
        self.lock_t = 0
        self.lock_moves = 0
        self.ai_target = None
        if not self._valid(self.cur):
            self._game_over()

    # ── hold ────────────────────────────────────────────────
    def _hold(self):
        if not self.can_hold:
            return
        self.can_hold = False
        ct = self.cur.type
        if self.held is None:
            self.held = ct
            self._next_piece()
        else:
            old = self.held
            self.held = ct
            self.cur = Piece(old)
        self.locking = False
        self.lock_t = 0
        self.lock_moves = 0
        self.ai_target = None
        play("hold")

    # ── finish line clear ───────────────────────────────────
    def _finish_clear(self):
        for r in sorted(self.clearing, reverse=True):
            del self.board[r]
        for _ in range(len(self.clearing)):
            self.board.insert(0, [None] * COLS)
        self.clearing = []
        self._next_piece()

    # ── game over ───────────────────────────────────────────
    def _game_over(self):
        self.state = "over"
        self.go_row = ROWS - 1
        self.go_t = 0
        self.ai_mode = False
        if self.score > self.high_score:
            self.high_score = self.score
        play("over")

    # ══════════════════════════════════════════════════════════
    #  AI LOGIC
    # ══════════════════════════════════════════════════════════
    def evaluate_board(self, board, lines_cleared):
        heights = [0] * COLS
        for c in range(COLS):
            for r in range(ROWS):
                if board[r][c] is not None:
                    heights[c] = ROWS - r
                    break

        agg_height = sum(heights)

        holes = 0
        for c in range(COLS):
            block_found = False
            for r in range(ROWS):
                if board[r][c] is not None:
                    block_found = True
                elif block_found:
                    holes += 1

        bumpiness = 0
        for c in range(COLS - 1):
            bumpiness += abs(heights[c] - heights[c + 1])

        wells = 0
        for c in range(COLS):
            left_h = heights[c - 1] if c > 0 else ROWS
            right_h = heights[c + 1] if c < COLS - 1 else ROWS
            well_depth = min(left_h, right_h) - heights[c]
            if well_depth > 0:
                wells += well_depth

        return (-0.510066 * agg_height +
                 0.760666 * lines_cleared +
                -0.35663  * holes +
                -0.184483 * bumpiness +
                -0.15     * wells)

    def ai_find_best_move(self):
        best_score = -float('inf')
        best_move = None

        pieces_to_eval = [(self.cur.type, False)]
        if self.can_hold:
            if self.held is None:
                pieces_to_eval.append((self.nxt[0], True))
            else:
                pieces_to_eval.append((self.held, True))

        for piece_type, is_hold in pieces_to_eval:
            for rot in range(4):
                for x in range(-3, COLS + 3):
                    board_copy = [row[:] for row in self.board]
                    p = Piece(piece_type, x=x, y=0)
                    p.rot = rot

                    if not self._valid(p, board=board_copy):
                        continue

                    while self._valid(p, dy=1, board=board_copy):
                        p.y += 1

                    valid_place = True
                    for cx, cy in p.cells():
                        if 0 <= cy < ROWS and 0 <= cx < COLS:
                            board_copy[cy][cx] = piece_type
                        elif cy < 0:
                            valid_place = False
                            break

                    if not valid_place:
                        continue

                    lines_cleared = 0
                    for r in range(ROWS - 1, -1, -1):
                        if all(board_copy[r][c] is not None for c in range(COLS)):
                            del board_copy[r]
                            board_copy.insert(0, [None] * COLS)
                            lines_cleared += 1

                    score = self.evaluate_board(board_copy, lines_cleared)
                    if score > best_score:
                        best_score = score
                        best_move = (is_hold, rot, x)

        return best_move

    def update_ai(self, dt):
        if not self.ai_mode or self.state != "play" or self.clearing:
            return

        if self.ai_target is None:
            self.ai_target = self.ai_find_best_move()
            self.ai_phase = 0
            self.ai_timer = 0
            self.ai_stuck_counter = 0
            return

        self.ai_timer += dt
        if self.ai_timer < 35:
            return
        self.ai_timer = 0

        is_hold, target_rot, target_x = self.ai_target

        if self.ai_phase == 0:
            if is_hold:
                self._hold()
            self.ai_phase = 1
            return

        if self.ai_phase == 1:
            if self.cur.rot != target_rot:
                diff = (target_rot - self.cur.rot) % 4
                if diff == 3:
                    self._try_rot(-1)
                else:
                    self._try_rot(1)
                return
            self.ai_phase = 2
            return

        if self.ai_phase == 2:
            if self.cur.x < target_x:
                if not self._move(1, 0):
                    self.ai_stuck_counter += 1
            elif self.cur.x > target_x:
                if not self._move(-1, 0):
                    self.ai_stuck_counter += 1
            else:
                self.ai_phase = 3

            if self.ai_stuck_counter > 4:
                self.ai_phase = 3
            return

        if self.ai_phase == 3:
            self._hard_drop()
            self.ai_target = None

    # ══════════════════════════════════════════════════════════
    #  UPDATE
    # ══════════════════════════════════════════════════════════
    def update(self, dt):
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.15
            p["life"] -= 1
        self.particles = [p for p in self.particles if p["life"] > 0]

        if self.msg_t > 0:
            self.msg_t -= dt

        if self.state == "over":
            self.go_t += dt
            if self.go_t > 40 and self.go_row >= 0:
                self.go_t = 0
                for c in range(COLS):
                    self.board[self.go_row][c] = "X"
                self.go_row -= 1
            return

        if self.state != "play":
            return

        if self.clearing:
            self.clear_t += dt
            self.clear_flash += dt
            if self.clear_t >= self.CLEAR_DUR:
                self._finish_clear()
            return

        self.update_ai(dt)

        if self.ai_mode:
            return

        if self.das_dir:
            self.das_t += dt
            if not self.das_on:
                if self.das_t >= 170:
                    self.das_on = True
                    self.das_t = 0
                    if self._move(self.das_dir, 0):
                        play("move")
            else:
                if self.das_t >= 50:
                    self.das_t = 0
                    if self._move(self.das_dir, 0):
                        play("move")

        spd = self.gravity_ms
        if self.soft:
            spd = min(spd, 50)
        self.grav_t += dt
        if self.grav_t >= spd:
            self.grav_t = 0
            if self._move(0, 1):
                if self.soft:
                    self.score += 1
                self.locking = False
                self.lock_t = 0
            else:
                if not self.locking:
                    self.locking = True
                    self.lock_t = 0
                    self.lock_moves = 0

        if self.locking:
            if self._valid(self.cur, dy=1):
                self.locking = False
                self.lock_t = 0
            else:
                self.lock_t += dt
                if self.lock_t >= 500 or self.lock_moves >= 15:
                    self._lock()

    # ══════════════════════════════════════════════════════════
    #  INPUT
    # ══════════════════════════════════════════════════════════
    def key_down(self, key):
        global SOUND_ON  # Needed to modify the global sound variable

        if self.state == "over":
            if key == pygame.K_RETURN:
                self.reset()
            return

        if key == pygame.K_a:
            self.ai_mode = not self.ai_mode
            self.ai_target = None
            return

        if key == pygame.K_s:
            SOUND_ON = not SOUND_ON
            return

        if key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = "pause" if self.state == "play" else "play"
            return

        if self.state != "play" or self.clearing or self.ai_mode:
            return

        if key == pygame.K_LEFT:
            self.das_dir = -1
            self.das_t = 0
            self.das_on = False
            if self._move(-1, 0):
                play("move")
        elif key == pygame.K_RIGHT:
            self.das_dir = 1
            self.das_t = 0
            self.das_on = False
            if self._move(1, 0):
                play("move")
        elif key == pygame.K_DOWN:
            self.soft = True
        elif key in (pygame.K_UP, pygame.K_x):
            self._try_rot(1)
        elif key in (pygame.K_z, pygame.K_LCTRL):
            self._try_rot(-1)
        elif key == pygame.K_SPACE:
            self._hard_drop()
        elif key in (pygame.K_c, pygame.K_LSHIFT):
            self._hold()

    def key_up(self, key):
        if key == pygame.K_LEFT and self.das_dir == -1:
            self.das_dir = 0
        elif key == pygame.K_RIGHT and self.das_dir == 1:
            self.das_dir = 0
        elif key == pygame.K_DOWN:
            self.soft = False

    # ══════════════════════════════════════════════════════════
    #  DRAW
    # ══════════════════════════════════════════════════════════
    def draw(self):
        screen.fill(BG)

        pygame.draw.rect(screen, BOARD_BG, (BOARD_X, BOARD_Y, BOARD_W, BOARD_H))

        for r in range(ROWS + 1):
            y = BOARD_Y + r * CELL
            pygame.draw.line(screen, GRID_CLR, (BOARD_X, y), (BOARD_X + BOARD_W, y))
        for c in range(COLS + 1):
            x = BOARD_X + c * CELL
            pygame.draw.line(screen, GRID_CLR, (x, BOARD_Y), (x, BOARD_Y + BOARD_H))

        for r in range(ROWS):
            for c in range(COLS):
                v = self.board[r][c]
                if v:
                    clr = GRAY_BLOCK if v == "X" else PIECE_CLR.get(v, (200, 200, 200))
                    draw_block(screen, BOARD_X + c * CELL, BOARD_Y + r * CELL, CELL, clr)

        if self.state == "play" and self.cur and not self.clearing:
            gy = self._ghost_y()
            if gy != self.cur.y:
                gc = darken(self.cur.color, 0.5)
                for cx, cy in self.cur.cells():
                    adj_y = cy - self.cur.y + gy
                    if 0 <= adj_y < ROWS and 0 <= cx < COLS:
                        draw_block(screen, BOARD_X + cx * CELL,
                                   BOARD_Y + adj_y * CELL, CELL, gc, ghost=True)

        if self.state == "play" and self.cur and not self.clearing:
            for cx, cy in self.cur.cells():
                if 0 <= cy < ROWS and 0 <= cx < COLS:
                    draw_block(screen, BOARD_X + cx * CELL,
                               BOARD_Y + cy * CELL, CELL, self.cur.color)

        if self.clearing:
            on = (int(self.clear_flash) // 80) % 2 == 0
            for r in self.clearing:
                if on:
                    pygame.draw.rect(screen, FLASH,
                                     (BOARD_X, BOARD_Y + r * CELL, BOARD_W, CELL))
                else:
                    for c in range(COLS):
                        v = self.board[r][c]
                        if v:
                            clr = lighten(PIECE_CLR.get(v, (200, 200, 200)), 1.8)
                            draw_block(screen, BOARD_X + c * CELL,
                                       BOARD_Y + r * CELL, CELL, clr)

        for p in self.particles:
            a = max(0, min(255, int(255 * p["life"] / p["ml"])))
            ps = pygame.Surface((p["s"] * 2, p["s"] * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*p["c"], a), (p["s"], p["s"]), p["s"])
            screen.blit(ps, (int(p["x"]) - p["s"], int(p["y"]) - p["s"]))

        br = pygame.Rect(PAD, PAD, BOARD_W + 2 * BORDER_W, BOARD_H + 2 * BORDER_W)
        pygame.draw.rect(screen, BORDER_CLR, br, BORDER_W)
        pygame.draw.line(screen, BORDER_HI, (br.left, br.top), (br.right, br.top), 1)
        pygame.draw.line(screen, BORDER_HI, (br.left, br.top), (br.left, br.bottom), 1)

        # ── sidebar ─────────────────────────────────────────
        sx = SIDEBAR_X
        sy = BOARD_Y

        ai_txt = "AI: ON" if self.ai_mode else "AI: OFF"
        ai_clr = (0, 255, 100) if self.ai_mode else (255, 80, 80)
        draw_text(screen, ai_txt, self.f_sm, sx, sy, ai_clr)

        snd_txt = "SND: ON" if SOUND_ON else "SND: OFF"
        snd_clr = (0, 255, 100) if SOUND_ON else (255, 80, 80)
        draw_text(screen, snd_txt, self.f_sm, sx + 90, sy, snd_clr)

        draw_text(screen, "HOLD", self.f_sm, sx, sy + 25, TEXT_DIM)
        hr = pygame.Rect(sx, sy + 47, 80, 60)
        pygame.draw.rect(screen, BOARD_BG, hr)
        pygame.draw.rect(screen, BORDER_CLR, hr, 2)
        if self.held:
            self._draw_preview(self.held, sx + 40, sy + 77, 18)

        ny = sy + 120
        draw_text(screen, "NEXT", self.f_sm, sx, ny, TEXT_DIM)
        for i, pt in enumerate(self.nxt):
            nr = pygame.Rect(sx, ny + 22 + i * 58, 80, 52)
            pygame.draw.rect(screen, BOARD_BG, nr)
            pygame.draw.rect(screen, BORDER_CLR, nr, 2)
            self._draw_preview(pt, sx + 40, ny + 48 + i * 58, 16)

        sry = ny + 200
        draw_text(screen, "SCORE", self.f_sm, sx, sry, TEXT_DIM)
        draw_text(screen, f"{self.score:,}", self.f_med, sx, sry + 20, TEXT_CLR)

        draw_text(screen, "BEST", self.f_sm, sx, sry + 55, TEXT_DIM)
        draw_text(screen, f"{self.high_score:,}", self.f_med, sx, sry + 75, TEXT_CLR)

        draw_text(screen, "LEVEL", self.f_sm, sx, sry + 110, TEXT_DIM)
        draw_text(screen, str(self.level), self.f_med, sx, sry + 130, TEXT_CLR)

        draw_text(screen, "LINES", self.f_sm, sx, sry + 165, TEXT_DIM)
        draw_text(screen, str(self.lines), self.f_med, sx, sry + 185, TEXT_CLR)

        if self.msg_t > 0 and self.msg:
            mx = BOARD_X + BOARD_W // 2
            my = BOARD_Y + BOARD_H // 2 - 20
            scale = 1.0 + 0.15 * math.sin(self.msg_t * 0.008)
            mf = pygame.font.Font(None, int(44 * scale))
            if self.msg == "TETRIS!":
                mc = (255, 255, 0)
            elif self.msg == "TRIPLE":
                mc = (0, 255, 200)
            elif self.msg == "DOUBLE":
                mc = (0, 200, 255)
            else:
                mc = (200, 200, 255)
            draw_text(screen, self.msg, mf, mx, my, mc, center=True)

        if self.state == "pause":
            ov = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            screen.blit(ov, (BOARD_X, BOARD_Y))
            cx = BOARD_X + BOARD_W // 2
            cy = BOARD_Y + BOARD_H // 2
            draw_text(screen, "PAUSED", self.f_big, cx, cy - 20, FLASH, center=True)
            draw_text(screen, "Press P to resume", self.f_sm, cx, cy + 25, TEXT_DIM, center=True)

        if self.state == "over":
            ov = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 120))
            screen.blit(ov, (BOARD_X, BOARD_Y))
            cx = BOARD_X + BOARD_W // 2
            cy = BOARD_Y + BOARD_H // 2
            draw_text(screen, "GAME OVER", self.f_big, cx, cy - 30, (255, 50, 50), center=True)
            draw_text(screen, f"Score: {self.score:,}", self.f_med, cx, cy + 15, TEXT_CLR, center=True)
            draw_text(screen, "ENTER to restart", self.f_sm, cx, cy + 45, TEXT_DIM, center=True)

        screen.blit(_scanlines, (0, 0))

    def _draw_preview(self, pt, cx, cy, sz):
        g = ROT[pt][0]
        clr = PIECE_CLR[pt]
        h = len(g)
        w = len(g[0])
        min_r, max_r = h, 0
        min_c, max_c = w, 0
        for r in range(h):
            for c in range(w):
                if g[r][c]:
                    min_r = min(min_r, r)
                    max_r = max(max_r, r)
                    min_c = min(min_c, c)
                    max_c = max(max_c, c)
        pw = (max_c - min_c + 1) * sz
        ph = (max_r - min_r + 1) * sz
        ox = cx - pw // 2
        oy = cy - ph // 2
        for r in range(h):
            for c in range(w):
                if g[r][c]:
                    draw_block(screen, ox + (c - min_c) * sz,
                               oy + (r - min_r) * sz, sz, clr)


# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════
def main():
    clock = pygame.time.Clock()
    game = Game()

    while True:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    game.reset()
                else:
                    game.key_down(event.key)
            elif event.type == pygame.KEYUP:
                game.key_up(event.key)

        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()