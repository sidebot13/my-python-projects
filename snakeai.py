import tkinter as tk
from collections import deque
import heapq
import random

# ================= CONFIG =================
CELL = 24
BASE_DELAY = 10
PANIC_THRESHOLD = 0.60
FUTURE_STEPS = 7
DIRS = [(1,0), (-1,0), (0,1), (0,-1)]

# ================= ROOT =================
root = tk.Tk()
root.attributes("-fullscreen", True)
root.update_idletasks()
W = root.winfo_screenwidth() + 22
H = root.winfo_screenheight()
GRID_W = W // CELL
GRID_H = H // CELL
W = GRID_W * CELL
H = GRID_H * CELL

# ================= UTIL =================
def neighbors(p):
    for dx, dy in DIRS:
        yield (p[0] + dx, p[1] + dy)

def manhattan(a,b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

# ================= AI =================
class SnakeAI:
    def __init__(self):
        cx, cy = GRID_W//2, GRID_H//2
        self.snake = deque([(cx,cy),(cx-1,cy),(cx-2,cy)])
        self.food = self.spawn_food()
        self.path = []
        self.heatmap = {}
        self.show_heat = False
        self.delay = BASE_DELAY

    def spawn_food(self):
        while True:
            f = (random.randint(0,GRID_W-1),random.randint(0,GRID_H-1))
            if f not in self.snake:
                return f

    def flood(self,start,body):
        blocked = set(body)
        blocked.remove(body[-1])
        q = deque([start])
        seen = {start}
        while q:
            cur = q.popleft()
            for n in neighbors(cur):
                if 0<=n[0]<GRID_W and 0<=n[1]<GRID_H:
                    if n not in seen and n not in blocked:
                        seen.add(n)
                        q.append(n)
        return len(seen)

    def panic_mode(self,body):
        free = GRID_W*GRID_H - len(body)
        if free<=0: return True
        reachable = self.flood(body[0],body)
        return (reachable/free) < PANIC_THRESHOLD

    # ---------- HEAT MAP ----------
    def compute_heat(self):
        heat = {}
        body = list(self.snake)
        for x in range(GRID_W):
            for y in range(GRID_H):
                d = 0
                # wall pressure
                d += 1 / (min(x, GRID_W-1-x)+1)
                d += 1 / (min(y, GRID_H-1-y)+1)
                # body proximity
                for b in body:
                    dist = manhattan((x,y),b)
                    if dist==0:
                        d += 999
                    else:
                        d += 2/dist
                heat[(x,y)] = d
        self.heatmap = heat

    # ---------- A* ----------
    def astar(self,start,goal):
        hard = set(self.snake)
        hard.remove(self.snake[-1])
        pq = [(0,start)]
        came = {}
        cost = {start:0}
        while pq:
            _,cur = heapq.heappop(pq)
            if cur==goal: break
            for n in neighbors(cur):
                if not (0<=n[0]<GRID_W and 0<=n[1]<GRID_H): continue
                if n in hard: continue
                new = cost[cur]+1
                if n not in cost or new<cost[n]:
                    cost[n]=new
                    heapq.heappush(pq,(new+manhattan(n,goal),n))
                    came[n]=cur
        if goal not in came: return None
        path = [goal]
        while path[-1]!=start:
            path.append(came[path[-1]])
        return path[::-1]

    # ---------- FUTURE SAFE ----------
    def future_safe(self,move):
        sim = deque(self.snake)
        sim.appendleft(move)
        if move!=self.food:
            sim.pop()
        for _ in range(FUTURE_STEPS):
            head = sim[0]
            blocked = set(sim)
            blocked.remove(sim[-1])
            opts=[]
            for n in neighbors(head):
                if 0<=n[0]<GRID_W and 0<=n[1]<GRID_H:
                    if n not in blocked:
                        opts.append(n)
            if not opts: return False
            sim.appendleft(random.choice(opts))
            sim.pop()
        return not self.panic_mode(sim)

    # ---------- STEP ----------
    def step(self):
        self.compute_heat()
        head = self.snake[0]
        self.path = self.astar(head,self.food)
        if self.path and len(self.path)>1:
            nxt=self.path[1]
            if nxt not in self.snake and self.future_safe(nxt):
                self.move(nxt)
                return
        # fallback: pick best score (space - danger)
        best=None
        best_score=-1e9
        for n in neighbors(head):
            if not (0<=n[0]<GRID_W and 0<=n[1]<GRID_H): continue
            if n in self.snake: continue
            temp=deque(self.snake)
            temp.appendleft(n)
            temp.pop()
            space = self.flood(n,temp)
            danger = self.heatmap.get(n,0)
            score = space*2 - danger*10
            if score>best_score:
                best_score=score
                best=n
        if best:
            self.move(best)

    def move(self,n):
        self.snake.appendleft(n)
        if n==self.food:
            self.food=self.spawn_food()
        else:
            self.snake.pop()

# ================= GAME =================
class Game:
    def __init__(self):
        self.canvas = tk.Canvas(root,width=W,height=H,bg="black")
        self.canvas.pack()
        self.ai=SnakeAI()
        root.bind("<h>",self.toggle_heat)
        root.bind("<w>",self.speed_up)
        root.bind("<s>",self.speed_down)
        self.loop()

    def toggle_heat(self,e=None):
        self.ai.show_heat=not self.ai.show_heat

    def speed_up(self,e=None):
        self.ai.delay=max(1,self.ai.delay-1)

    def speed_down(self,e=None):
        self.ai.delay+=1

    # ---------- DRAW ----------
    def draw(self):
        self.canvas.delete("all")

        # Heat map numbers
        if self.ai.show_heat:
            for (x,y),v in self.ai.heatmap.items():
                # map value to 0-255 brightness
                brightness = min(255,int(v*15))
                color = f"#{brightness:02x}{brightness:02x}{brightness:02x}"  # white shades
                self.canvas.create_text(
                    x*CELL + CELL//2,
                    y*CELL + CELL//2,
                    text=str(int(v)),
                    fill=color,
                    font=("Consolas",10)
                )

        # path (dark green)
        if self.ai.path:
            for p in self.ai.path[1:]:
                if p!=self.ai.food and p!=self.ai.snake[0]:
                    self.canvas.create_rectangle(
                        p[0]*CELL,p[1]*CELL,
                        (p[0]+1)*CELL,(p[1]+1)*CELL,
                        fill="#0f4f16"
                    )

        # snake body
        for s in list(self.ai.snake)[1:]:
            self.canvas.create_rectangle(
                s[0]*CELL,s[1]*CELL,
                (s[0]+1)*CELL,(s[1]+1)*CELL,
                fill="lime"
            )

        # head
        hx,hy=self.ai.snake[0]
        self.canvas.create_rectangle(
            hx*CELL,hy*CELL,
            (hx+1)*CELL,(hy+1)*CELL,
            fill="green"
        )

        # food
        fx,fy=self.ai.food
        self.canvas.create_oval(
            fx*CELL+5,fy*CELL+5,
            (fx+1)*CELL-5,(fy+1)*CELL-5,
            fill="yellow"
        )

    def loop(self):
        self.ai.step()
        self.draw()
        root.after(self.ai.delay,self.loop)

# ================= RUN =================
Game()
root.mainloop()
