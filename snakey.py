import tkinter as tk
import random
from collections import deque

CELL = 20
BG = "#111"
BODY = "#2ecc71"
HEAD = "#e74c3c"
APPLE = "#f1c40f"

DIRS = [(1,0), (-1,0), (0,1), (0,-1)]

class SnakeGame:
    def __init__(self):
        self.cols = int(input("Grid width: "))
        self.rows = int(input("Grid height: "))

        self.root = tk.Tk()
        self.root.title("Snake AI")

        self.canvas = tk.Canvas(
            self.root,
            width=self.cols * CELL,
            height=self.rows * CELL,
            bg=BG,
            highlightthickness=0
        )
        self.canvas.pack()

        self.speed = 80
        self.auto = True

        self.root.bind("<Up>", lambda e: self.adjust_speed(-10))
        self.root.bind("<Down>", lambda e: self.adjust_speed(10))
        self.root.bind("a", lambda e: self.toggle_auto())

        self.reset()
        self.loop()
        self.root.mainloop()

    # ================= CORE =================

    def reset(self):
        cx, cy = self.cols // 2, self.rows // 2
        self.snake = deque([(cx, cy)])
        self.spawn_apple()
        self.mode = "greedy"
        self.spiral = []

    def spawn_apple(self):
        free = [(x,y) for x in range(self.cols)
                        for y in range(self.rows)
                        if (x,y) not in self.snake]
        self.apple = random.choice(free)

    def inb(self, p):
        return 0 <= p[0] < self.cols and 0 <= p[1] < self.rows

    # ============ FUTURE-SAFE MOVE CHECK ============

    def legal_move(self, nxt):
        body = list(self.snake)

        # head moves
        body.insert(0, nxt)

        # tail moves unless eating
        if nxt != self.apple:
            body.pop()

        return len(body) == len(set(body))

    # ============ PATHFINDING =======================

    def bfs(self, start, goal):
        q = deque([start])
        prev = {start: None}

        while q:
            u = q.popleft()
            if u == goal:
                break
            for dx,dy in DIRS:
                v = (u[0]+dx, u[1]+dy)
                if (self.inb(v)
                    and v not in prev
                    and (v not in self.snake or v == self.snake[-1])):
                    prev[v] = u
                    q.append(v)

        if goal not in prev:
            return None

        path = []
        cur = goal
        while cur:
            path.append(cur)
            cur = prev[cur]
        return path[::-1]

    # ============ SPIRAL GENERATOR ==================

    def build_spiral(self, cx, cy):
        path = []
        r = 2
        while True:
            ring = []
            for dx in range(-r, r+1, 2):
                ring.append((cx+dx, cy-r))
                ring.append((cx+dx, cy+r))
            for dy in range(-r+2, r-1, 2):
                ring.append((cx-r, cy+dy))
                ring.append((cx+r, cy+dy))

            ring = [p for p in ring if self.inb(p)]
            if not ring:
                break

            path += ring
            r += 2

        return path

    # ============ PANIC MODE ========================

    def panic_move(self):
        head = self.snake[0]
        best = None
        best_area = -1

        for dx,dy in DIRS:
            nxt = (head[0]+dx, head[1]+dy)
            if not self.inb(nxt):
                continue
            if not self.legal_move(nxt):
                continue

            body = list(self.snake)
            body.insert(0, nxt)
            body.pop()

            seen = set(body)
            q = deque([nxt])
            area = 0

            while q:
                u = q.popleft()
                for d in DIRS:
                    v = (u[0]+d[0], u[1]+d[1])
                    if self.inb(v) and v not in seen:
                        seen.add(v)
                        q.append(v)
                        area += 1

            if area > best_area:
                best_area = area
                best = nxt

        return best

    # ============ DECISION ==========================

    def choose_move(self):
        head = self.snake[0]

        # 1️⃣ Greedy apple
        path = self.bfs(head, self.apple)
        if path and len(path) > 1:
            if self.legal_move(path[1]):
                return path[1]

        # 2️⃣ Spiral orbit
        if not self.spiral:
            self.spiral = self.build_spiral(*self.apple)

        if self.spiral:
            nxt = self.spiral[0]
            if self.legal_move(nxt):
                self.spiral.pop(0)
                return nxt
            else:
                self.spiral.clear()

        # 3️⃣ Panic survival
        panic = self.panic_move()
        if panic:
            return panic

        return None

    # ============ GAME LOOP =========================

    def step(self):
        nxt = self.choose_move()
        if not nxt:
            self.reset()
            return

        self.snake.appendleft(nxt)
        if nxt == self.apple:
            self.spawn_apple()
            self.spiral.clear()
        else:
            self.snake.pop()

    def draw(self):
        self.canvas.delete("all")

        ax, ay = self.apple
        self.canvas.create_rectangle(
            ax*CELL, ay*CELL,
            ax*CELL+CELL, ay*CELL+CELL,
            fill=APPLE, outline=""
        )

        for i,(x,y) in enumerate(self.snake):
            self.canvas.create_rectangle(
                x*CELL, y*CELL,
                x*CELL+CELL, y*CELL+CELL,
                fill=HEAD if i==0 else BODY,
                outline=""
            )

    def loop(self):
        if self.auto:
            self.step()
        self.draw()
        self.root.after(self.speed, self.loop)

    def adjust_speed(self, d):
        self.speed = max(10, self.speed + d)

    def toggle_auto(self):
        self.auto = not self.auto


SnakeGame()
