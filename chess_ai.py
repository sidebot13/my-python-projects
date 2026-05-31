"""
Chess AI — pure Python + tkinter only. No external dependencies.
Alpha-beta search with iterative deepening, quiescence search,
transposition table, MVV-LVA move ordering, and PST evaluation.
"""
import tkinter as tk
from tkinter import messagebox
import threading, time

# ═══════════════════════════════════════════════════════════════════════════
# PIECE / COLOR CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
EMPTY  = 0
PAWN,KNIGHT,BISHOP,ROOK,QUEEN,KING = 1,2,3,4,5,6
WHITE, BLACK = 1, -1

PIECE_VAL = {PAWN:100,KNIGHT:320,BISHOP:330,ROOK:500,QUEEN:900,KING:20000}

_PAWN_PST = [
 [ 0, 0, 0, 0, 0, 0, 0, 0],[50,50,50,50,50,50,50,50],
 [10,10,20,30,30,20,10,10],[ 5, 5,10,25,25,10, 5, 5],
 [ 0, 0, 0,20,20, 0, 0, 0],[ 5,-5,-10,0,0,-10,-5,5],
 [ 5,10,10,-20,-20,10,10,5],[ 0, 0, 0, 0, 0, 0, 0, 0],
]
_KNIGHT_PST = [
 [-50,-40,-30,-30,-30,-30,-40,-50],[-40,-20,0,0,0,0,-20,-40],
 [-30,0,10,15,15,10,0,-30],[-30,5,15,20,20,15,5,-30],
 [-30,0,15,20,20,15,0,-30],[-30,5,10,15,15,10,5,-30],
 [-40,-20,0,5,5,0,-20,-40],[-50,-40,-30,-30,-30,-30,-40,-50],
]
_BISHOP_PST = [
 [-20,-10,-10,-10,-10,-10,-10,-20],[-10,0,0,0,0,0,0,-10],
 [-10,0,5,10,10,5,0,-10],[-10,5,5,10,10,5,5,-10],
 [-10,0,10,10,10,10,0,-10],[-10,10,10,10,10,10,10,-10],
 [-10,5,0,0,0,0,5,-10],[-20,-10,-10,-10,-10,-10,-10,-20],
]
_ROOK_PST = [
 [0,0,0,0,0,0,0,0],[5,10,10,10,10,10,10,5],
 [-5,0,0,0,0,0,0,-5],[-5,0,0,0,0,0,0,-5],
 [-5,0,0,0,0,0,0,-5],[-5,0,0,0,0,0,0,-5],
 [-5,0,0,0,0,0,0,-5],[0,0,0,5,5,0,0,0],
]
_QUEEN_PST = [
 [-20,-10,-10,-5,-5,-10,-10,-20],[-10,0,0,0,0,0,0,-10],
 [-10,0,5,5,5,5,0,-10],[-5,0,5,5,5,5,0,-5],
 [0,0,5,5,5,5,0,-5],[-10,5,5,5,5,5,0,-10],
 [-10,0,5,0,0,0,0,-10],[-20,-10,-10,-5,-5,-10,-10,-20],
]
_KING_MID = [
 [-30,-40,-40,-50,-50,-40,-40,-30],[-30,-40,-40,-50,-50,-40,-40,-30],
 [-30,-40,-40,-50,-50,-40,-40,-30],[-30,-40,-40,-50,-50,-40,-40,-30],
 [-20,-30,-30,-40,-40,-30,-30,-20],[-10,-20,-20,-20,-20,-20,-20,-10],
 [20,20,0,0,0,0,20,20],[20,30,10,0,0,10,30,20],
]
_KING_END = [
 [-50,-40,-30,-20,-20,-30,-40,-50],[-30,-20,-10,0,0,-10,-20,-30],
 [-30,-10,20,30,30,20,-10,-30],[-30,-10,30,40,40,30,-10,-30],
 [-30,-10,30,40,40,30,-10,-30],[-30,-10,20,30,30,20,-10,-30],
 [-30,-30,0,0,0,0,-30,-30],[-50,-30,-30,-30,-30,-30,-30,-50],
]
PST = {PAWN:_PAWN_PST,KNIGHT:_KNIGHT_PST,BISHOP:_BISHOP_PST,
       ROOK:_ROOK_PST,QUEEN:_QUEEN_PST,KING:_KING_MID}

KNIGHT_DIRS = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
DIAG_DIRS   = [(-1,-1),(-1,1),(1,-1),(1,1)]
STRA_DIRS   = [(-1,0),(1,0),(0,-1),(0,1)]
ROYAL_DIRS  = DIAG_DIRS + STRA_DIRS

ON_BOARD = lambda r,f: 0<=r<8 and 0<=f<8

# ═══════════════════════════════════════════════════════════════════════════
# BOARD
# ═══════════════════════════════════════════════════════════════════════════
class Board:
    __slots__ = ('grid','turn','castling','ep','halfmove','fullmove','history')

    def __init__(self):
        self.grid     = [[0]*8 for _ in range(8)]
        self.turn     = WHITE
        self.castling = {'wK':True,'wQ':True,'bK':True,'bQ':True}
        self.ep       = None
        self.halfmove = 0
        self.fullmove = 1
        self.history  = []
        self._setup()

    def _setup(self):
        back = [ROOK,KNIGHT,BISHOP,QUEEN,KING,BISHOP,KNIGHT,ROOK]
        for f,pt in enumerate(back):
            self.grid[0][f] =  pt
            self.grid[7][f] = -pt
        for f in range(8):
            self.grid[1][f] =  PAWN
            self.grid[6][f] = -PAWN

    def piece_at(self,r,f): return self.grid[r][f]
    def type_at(self,r,f):  return abs(self.grid[r][f])

    # ── push / pop ────────────────────────────────────────────────────────
    def push(self, move):
        r1,f1,r2,f2,promo = move
        piece    = self.grid[r1][f1]
        captured = self.grid[r2][f2]
        pt       = abs(piece)
        old_cast = self.castling.copy()
        old_ep   = self.ep
        old_half = self.halfmove
        ep_cap   = None
        self.halfmove += 1

        # En-passant capture
        new_ep = None
        if pt == PAWN:
            self.halfmove = 0
            if abs(r2-r1) == 2:
                new_ep = ((r1+r2)//2, f1)
            if self.ep and (r2,f2) == self.ep:
                er = r1
                ep_cap = (er, f2, self.grid[er][f2])
                self.grid[er][f2] = 0
                captured = ep_cap[2]

        if captured != 0:
            self.halfmove = 0

        self.grid[r2][f2] = (self.turn * promo) if promo else piece
        self.grid[r1][f1] = 0

        # Castling: move rook
        if pt == KING:
            row = 0 if self.turn == WHITE else 7
            ck = 'wK' if self.turn==WHITE else 'bK'
            cq = 'wQ' if self.turn==WHITE else 'bQ'
            self.castling[ck] = self.castling[cq] = False
            if f2-f1 == 2:
                self.grid[row][5] = self.grid[row][7]; self.grid[row][7] = 0
            elif f1-f2 == 2:
                self.grid[row][3] = self.grid[row][0]; self.grid[row][0] = 0

        # Update castling rights
        if pt == ROOK:
            if (r1,f1)==(0,0): self.castling['wQ']=False
            if (r1,f1)==(0,7): self.castling['wK']=False
            if (r1,f1)==(7,0): self.castling['bQ']=False
            if (r1,f1)==(7,7): self.castling['bK']=False
        if (r2,f2)==(0,0): self.castling['wQ']=False
        if (r2,f2)==(0,7): self.castling['wK']=False
        if (r2,f2)==(7,0): self.castling['bQ']=False
        if (r2,f2)==(7,7): self.castling['bK']=False

        self.ep = new_ep
        if self.turn == BLACK: self.fullmove += 1
        self.turn = -self.turn
        self.history.append((move, captured, old_cast, old_ep, old_half, ep_cap))

    def pop(self):
        move, captured, old_cast, old_ep, old_half, ep_cap = self.history.pop()
        r1,f1,r2,f2,promo = move
        self.turn = -self.turn
        piece = self.grid[r2][f2]

        self.grid[r1][f1] = self.turn * (PAWN if promo else abs(piece))
        self.grid[r2][f2] = 0 if ep_cap else captured

        if ep_cap:
            er, ef, ev = ep_cap
            self.grid[er][ef] = ev

        # Restore rook for castling
        if abs(self.grid[r1][f1]) == KING:
            row = 0 if self.turn==WHITE else 7
            if f2-f1 == 2:
                self.grid[row][7]=self.grid[row][5]; self.grid[row][5]=0
            elif f1-f2 == 2:
                self.grid[row][0]=self.grid[row][3]; self.grid[row][3]=0

        self.castling = old_cast
        self.ep       = old_ep
        self.halfmove = old_half
        if self.turn == BLACK: self.fullmove -= 1

    # ── Attack detection ──────────────────────────────────────────────────
    def is_attacked(self, r, f, by_color):
        bc = by_color
        pd = 1 if bc==WHITE else -1
        for df in (-1,1):
            nr,nf = r-pd, f+df
            if ON_BOARD(nr,nf) and self.grid[nr][nf]==bc*PAWN: return True
        for dr,df in KNIGHT_DIRS:
            nr,nf = r+dr, f+df
            if ON_BOARD(nr,nf) and self.grid[nr][nf]==bc*KNIGHT: return True
        for dr,df in DIAG_DIRS:
            nr,nf = r+dr, f+df
            while ON_BOARD(nr,nf):
                v=self.grid[nr][nf]
                if v:
                    if v==bc*BISHOP or v==bc*QUEEN: return True
                    break
                nr+=dr; nf+=df
        for dr,df in STRA_DIRS:
            nr,nf = r+dr, f+df
            while ON_BOARD(nr,nf):
                v=self.grid[nr][nf]
                if v:
                    if v==bc*ROOK or v==bc*QUEEN: return True
                    break
                nr+=dr; nf+=df
        for dr,df in ROYAL_DIRS:
            nr,nf = r+dr, f+df
            if ON_BOARD(nr,nf) and self.grid[nr][nf]==bc*KING: return True
        return False

    def king_pos(self, color):
        for r in range(8):
            for f in range(8):
                if self.grid[r][f]==color*KING: return (r,f)
        return None

    def in_check(self, color=None):
        if color is None: color=self.turn
        kp = self.king_pos(color)
        return kp and self.is_attacked(kp[0],kp[1],-color)

    # ── Move generation ───────────────────────────────────────────────────
    def _pseudo(self, color):
        moves = []
        wh = (color==WHITE)
        for r in range(8):
            for f in range(8):
                v = self.grid[r][f]
                if v==0 or (v>0)!=wh: continue
                pt = abs(v)
                if pt==PAWN:
                    d=1 if wh else -1
                    sr=1 if wh else 6
                    pr=7 if wh else 0
                    nr=r+d
                    if ON_BOARD(nr,f) and self.grid[nr][f]==0:
                        if nr==pr:
                            for pp in (QUEEN,ROOK,BISHOP,KNIGHT):
                                moves.append((r,f,nr,f,pp))
                        else:
                            moves.append((r,f,nr,f,0))
                            if r==sr and self.grid[nr+d][f]==0:
                                moves.append((r,f,nr+d,f,0))
                    for df in (-1,1):
                        nf=f+df
                        if not ON_BOARD(nr,nf): continue
                        tv=self.grid[nr][nf]
                        ep_hit = self.ep==(nr,nf)
                        if (tv!=0 and (tv>0)!=wh) or ep_hit:
                            if nr==pr:
                                for pp in (QUEEN,ROOK,BISHOP,KNIGHT):
                                    moves.append((r,f,nr,nf,pp))
                            else:
                                moves.append((r,f,nr,nf,0))
                elif pt==KNIGHT:
                    for dr,df in KNIGHT_DIRS:
                        nr,nf=r+dr,f+df
                        if ON_BOARD(nr,nf):
                            tv=self.grid[nr][nf]
                            if tv==0 or (tv>0)!=wh:
                                moves.append((r,f,nr,nf,0))
                elif pt in (BISHOP,ROOK,QUEEN):
                    dirs=[]
                    if pt in (BISHOP,QUEEN): dirs+=DIAG_DIRS
                    if pt in (ROOK,QUEEN):   dirs+=STRA_DIRS
                    for dr,df in dirs:
                        nr,nf=r+dr,f+df
                        while ON_BOARD(nr,nf):
                            tv=self.grid[nr][nf]
                            if tv!=0 and (tv>0)==wh: break
                            moves.append((r,f,nr,nf,0))
                            if tv!=0: break
                            nr+=dr; nf+=df
                elif pt==KING:
                    for dr,df in ROYAL_DIRS:
                        nr,nf=r+dr,f+df
                        if ON_BOARD(nr,nf):
                            tv=self.grid[nr][nf]
                            if tv==0 or (tv>0)!=wh:
                                moves.append((r,f,nr,nf,0))
                    # castling
                    row=0 if wh else 7
                    opp=-color
                    ck='wK' if wh else 'bK'
                    cq='wQ' if wh else 'bQ'
                    rook_v=ROOK if wh else -ROOK
                    if (self.castling[ck] and r==row and f==4 and
                            self.grid[row][5]==0 and self.grid[row][6]==0 and
                            self.grid[row][7]==rook_v and
                            not self.is_attacked(row,4,opp) and
                            not self.is_attacked(row,5,opp) and
                            not self.is_attacked(row,6,opp)):
                        moves.append((row,4,row,6,0))
                    if (self.castling[cq] and r==row and f==4 and
                            self.grid[row][3]==0 and self.grid[row][2]==0 and self.grid[row][1]==0 and
                            self.grid[row][0]==rook_v and
                            not self.is_attacked(row,4,opp) and
                            not self.is_attacked(row,3,opp) and
                            not self.is_attacked(row,2,opp)):
                        moves.append((row,4,row,2,0))
        return moves

    def legal_moves(self, color=None):
        if color is None: color=self.turn
        legal=[]
        for m in self._pseudo(color):
            self.push(m)
            if not self.in_check(color): legal.append(m)
            self.pop()
        return legal

    def is_checkmate(self):
        return self.in_check() and not self.legal_moves()

    def is_stalemate(self):
        return not self.in_check() and not self.legal_moves()

    def is_insufficient(self):
        pieces=[]
        for r in range(8):
            for f in range(8):
                v=self.grid[r][f]
                if v: pieces.append(abs(v))
        if pieces==[KING,KING]: return True
        if sorted(pieces) in ([BISHOP,KING,KING],[KING,KING,KNIGHT]): return True
        return False

    def is_game_over(self):
        return self.is_checkmate() or self.is_stalemate() or \
               self.is_insufficient() or self.halfmove>=100

# ═══════════════════════════════════════════════════════════════════════════
# EVALUATION
# ═══════════════════════════════════════════════════════════════════════════
def count_queens(board):
    c=0
    for r in range(8):
        for f in range(8):
            if abs(board.grid[r][f])==QUEEN: c+=1
    return c

def evaluate(board):
    if board.is_checkmate(): return -30000
    if board.is_stalemate() or board.is_insufficient(): return 0
    endgame = count_queens(board)==0
    score=0
    for r in range(8):
        for f in range(8):
            v=board.grid[r][f]
            if not v: continue
            color=WHITE if v>0 else BLACK
            pt=abs(v)
            tbl=(_KING_END if endgame else _KING_MID) if pt==KING else PST[pt]
            pr=r if color==WHITE else 7-r
            score += color*(PIECE_VAL[pt]+tbl[pr][f])
    return score*board.turn

# ═══════════════════════════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════════════════════════
TT = {}
EXACT,LOWER,UPPER = 0,1,2
_stop = False

def _hash(board):
    rows=tuple(tuple(row) for row in board.grid)
    return hash((rows, board.turn, tuple(sorted(board.castling.items())), board.ep))

def _mvv_lva(board, move):
    r1,f1,r2,f2,promo=move
    victim  =abs(board.grid[r2][f2])
    attacker=abs(board.grid[r1][f1])
    if victim:   return PIECE_VAL[victim]*10 - PIECE_VAL.get(attacker,0)
    if promo:    return PIECE_VAL[promo]
    return 0

def _order(board, moves, tt_move):
    def sc(m):
        if m==tt_move: return 1_000_000
        return _mvv_lva(board,m)
    return sorted(moves, key=sc, reverse=True)

def quiesce(board, alpha, beta, depth=0):
    stand=evaluate(board)
    if stand>=beta: return beta
    if stand>alpha: alpha=stand
    if depth>5:     return alpha
    caps=[m for m in board.legal_moves() if board.grid[m[2]][m[3]]!=0 or m[4]]
    for m in sorted(caps, key=lambda mv:_mvv_lva(board,mv), reverse=True):
        board.push(m)
        sc=-quiesce(board,-beta,-alpha,depth+1)
        board.pop()
        if sc>=beta: return beta
        if sc>alpha: alpha=sc
    return alpha

def alphabeta(board, depth, alpha, beta):
    global _stop
    if _stop: return 0
    key=_hash(board)
    tt_move=None
    if key in TT:
        td,tf,ts,tm=TT[key]
        tt_move=tm
        if td>=depth:
            if tf==EXACT: return ts
            if tf==LOWER: alpha=max(alpha,ts)
            if tf==UPPER: beta =min(beta,ts)
            if alpha>=beta: return ts
    if board.is_game_over(): return evaluate(board)
    if depth==0: return quiesce(board,alpha,beta)
    moves=board.legal_moves()
    if not moves: return evaluate(board)
    moves=_order(board,moves,tt_move)
    best=-99999; bm=moves[0]; flag=UPPER
    for m in moves:
        board.push(m)
        sc=-alphabeta(board,depth-1,-beta,-alpha)
        board.pop()
        if _stop: return sc
        if sc>best: best=sc; bm=m
        if sc>alpha: alpha=sc; flag=EXACT
        if alpha>=beta: flag=LOWER; break
    TT[key]=(depth,flag,best,bm)
    return best

def find_best_move(board, max_depth=4, time_limit=8.0):
    global _stop
    _stop=False
    best=None
    start=time.time()
    for depth in range(1,max_depth+1):
        if time.time()-start>time_limit: break
        moves=board.legal_moves()
        if not moves: return None
        moves=_order(board,moves,None)
        ibest=moves[0]; ibsc=-99999
        for m in moves:
            if _stop: break
            board.push(m)
            sc=-alphabeta(board,depth-1,-99999,99999)
            board.pop()
            if sc>ibsc: ibsc=sc; ibest=m
        if not _stop: best=ibest
        if ibsc>=29000: break
    return best

# ═══════════════════════════════════════════════════════════════════════════
# UNICODE PIECES
# ═══════════════════════════════════════════════════════════════════════════
UNICODE = {
    (KING,WHITE):'♔',(QUEEN,WHITE):'♕',(ROOK,WHITE):'♖',
    (BISHOP,WHITE):'♗',(KNIGHT,WHITE):'♘',(PAWN,WHITE):'♙',
    (KING,BLACK):'♚',(QUEEN,BLACK):'♛',(ROOK,BLACK):'♜',
    (BISHOP,BLACK):'♝',(KNIGHT,BLACK):'♞',(PAWN,BLACK):'♟',
}

def _san(board, move):
    r1,f1,r2,f2,promo=move
    files='abcdefgh'; ranks='12345678'
    pt=abs(board.grid[r1][f1])
    N={PAWN:'',KNIGHT:'N',BISHOP:'B',ROOK:'R',QUEEN:'Q',KING:'K'}
    cap='x' if board.grid[r2][f2] or (pt==PAWN and board.ep==(r2,f2)) else ''
    src=files[f1] if (pt==PAWN and cap) else ('' if pt==PAWN else N[pt])
    p=('='+N[promo]) if promo else ''
    return f"{src}{cap}{files[f2]}{ranks[r2]}{p}"

# ═══════════════════════════════════════════════════════════════════════════
# GUI
# ═══════════════════════════════════════════════════════════════════════════
SQ  = 72
BSZ = SQ*8
LIGHT_SQ="#F0D9B5"; DARK_SQ="#B58863"; HL_SQ="#F6F669"
DOT_CLR="#CDD16E";  CHECK_CLR="#E25555"
BG="#1A1A2E"; PANEL="#16213E"; ACCENT="#E94560"; FG="#EAEAEA"

class ChessApp:
    def __init__(self, root):
        self.root          = root
        self.root.title("Chess AI")
        self.root.configure(bg=BG)
        self.root.resizable(False,False)
        self.board         = Board()
        self.player_color  = WHITE
        self.flipped       = False
        self.ai_thinking   = False
        self.drag_sq       = None
        self.drag_piece    = None
        self.legal_targets = set()
        self.last_move     = None
        self.history_san   = []
        self._build_ui()
        self._redraw()

    # ── Layout ───────────────────────────────────────────────────────────
    def _build_ui(self):
        lp=tk.Frame(self.root,bg=BG,padx=14,pady=14,width=185)
        lp.pack(side=tk.LEFT,fill=tk.Y); lp.pack_propagate(False)

        tk.Label(lp,text="CHESS AI",font=("Courier",20,"bold"),fg=ACCENT,bg=BG).pack(pady=(8,0))
        tk.Label(lp,text="α-β  Engine",font=("Courier",9),fg="#666",bg=BG).pack()
        tk.Frame(lp,bg="#333",height=1).pack(fill=tk.X,pady=10)

        self.status_var=tk.StringVar(value="Your move")
        tk.Label(lp,textvariable=self.status_var,font=("Courier",11,"bold"),
                 fg=FG,bg=BG,wraplength=160).pack()
        self.think_var=tk.StringVar(value="")
        tk.Label(lp,textvariable=self.think_var,font=("Courier",9),fg=ACCENT,bg=BG).pack()

        tk.Label(lp,text="Eval",font=("Courier",8),fg="#555",bg=BG).pack(pady=(10,1))
        self.eval_c=tk.Canvas(lp,width=152,height=16,bg=PANEL,highlightthickness=0)
        self.eval_c.pack()
        self.eval_var=tk.StringVar(value="0.0")
        tk.Label(lp,textvariable=self.eval_var,font=("Courier",8),fg="#888",bg=BG).pack()

        tk.Frame(lp,bg="#333",height=1).pack(fill=tk.X,pady=10)
        tk.Label(lp,text="Moves",font=("Courier",8),fg="#555",bg=BG).pack()
        hw=tk.Frame(lp,bg=PANEL); hw.pack(fill=tk.BOTH,expand=True,pady=4)
        sb=tk.Scrollbar(hw,bg=PANEL,troughcolor=PANEL); sb.pack(side=tk.RIGHT,fill=tk.Y)
        self.hist_lb=tk.Listbox(hw,font=("Courier",9),bg=PANEL,fg=FG,
                                selectbackground=ACCENT,relief=tk.FLAT,bd=0,
                                yscrollcommand=sb.set,width=16)
        self.hist_lb.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        sb.config(command=self.hist_lb.yview)

        bkw=dict(font=("Courier",9,"bold"),bg=ACCENT,fg="white",
                 activebackground="#c4324e",relief=tk.FLAT,cursor="hand2",pady=5)
        for txt,cmd in [("New Game",self._new_game),("Flip Board",self._flip),("Undo",self._undo)]:
            tk.Button(lp,text=txt,command=cmd,**bkw).pack(fill=tk.X,pady=2)

        tk.Label(lp,text="Depth",font=("Courier",8),fg="#555",bg=BG).pack(pady=(8,1))
        self.depth_var=tk.IntVar(value=4)
        df=tk.Frame(lp,bg=BG); df.pack()
        for d,lbl in [(2,"Easy"),(3,"Med"),(4,"Hard"),(5,"Max")]:
            tk.Radiobutton(df,text=lbl,variable=self.depth_var,value=d,
                           font=("Courier",8),bg=BG,fg=FG,
                           selectcolor=PANEL,activebackground=BG).pack(side=tk.LEFT)

        rp=tk.Frame(self.root,bg=BG); rp.pack(side=tk.LEFT,padx=10,pady=10)
        outer=tk.Frame(rp,bg=BG); outer.pack()

        rl=tk.Frame(outer,bg=BG,width=16); rl.pack(side=tk.LEFT,fill=tk.Y)
        self.rank_lbls=[]
        for i in range(8):
            lb=tk.Label(rl,text="",font=("Courier",8),fg="#777",bg=BG,width=2)
            lb.pack(expand=True,fill=tk.Y); self.rank_lbls.append(lb)

        cvw=tk.Frame(outer,bg=BG); cvw.pack(side=tk.LEFT)
        self.canvas=tk.Canvas(cvw,width=BSZ,height=BSZ,
                              highlightthickness=2,highlightbackground=ACCENT)
        self.canvas.pack()
        fl=tk.Frame(cvw,bg=BG,height=18); fl.pack(fill=tk.X)
        self.file_lbls=[]
        for i in range(8):
            lb=tk.Label(fl,text="",font=("Courier",8),fg="#777",bg=BG)
            lb.pack(side=tk.LEFT,expand=True,fill=tk.X); self.file_lbls.append(lb)

        self._update_coords()
        self.canvas.bind("<ButtonPress-1>",   self._press)
        self.canvas.bind("<B1-Motion>",       self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)

    def _update_coords(self):
        files="abcdefgh" if not self.flipped else "hgfedcba"
        ranks="87654321" if not self.flipped else "12345678"
        for i,lb in enumerate(self.file_lbls): lb.config(text=files[i])
        for i,lb in enumerate(self.rank_lbls): lb.config(text=ranks[i])

    # ── Coords ────────────────────────────────────────────────────────────
    def _sq_xy(self,r,f):
        col=f if not self.flipped else 7-f
        row=(7-r) if not self.flipped else r
        return col*SQ, row*SQ

    def _xy_sq(self,x,y):
        col=x//SQ; row=y//SQ
        if not (0<=col<8 and 0<=row<8): return None
        f=col if not self.flipped else 7-col
        r=(7-row) if not self.flipped else row
        return r,f

    # ── Draw ──────────────────────────────────────────────────────────────
    def _redraw(self):
        self._draw_board(); self._draw_pieces(); self._update_eval()

    def _draw_board(self):
        self.canvas.delete("sq","dot")
        check_sq=None
        if self.board.in_check():
            check_sq=self.board.king_pos(self.board.turn)
        lm=self.last_move
        lm_sqs=((lm[0],lm[1]),(lm[2],lm[3])) if lm else ()
        for r in range(8):
            for f in range(8):
                x,y=self._sq_xy(r,f)
                base=LIGHT_SQ if (r+f)%2==0 else DARK_SQ
                if lm and (r,f) in lm_sqs: color=HL_SQ
                elif (r,f)==check_sq:       color=CHECK_CLR
                else:                       color=base
                self.canvas.create_rectangle(x,y,x+SQ,y+SQ,fill=color,outline="",tags="sq")
        for (r,f) in self.legal_targets:
            x,y=self._sq_xy(r,f); cx,cy=x+SQ//2,y+SQ//2
            if self.board.grid[r][f]!=0:
                self.canvas.create_oval(x+3,y+3,x+SQ-3,y+SQ-3,
                                        outline=DOT_CLR,width=4,fill="",tags="dot")
            else:
                self.canvas.create_oval(cx-9,cy-9,cx+9,cy+9,
                                        fill=DOT_CLR,outline="",tags="dot")

    def _draw_pieces(self):
        self.canvas.delete("piece")
        for r in range(8):
            for f in range(8):
                if self.drag_sq and (r,f)==self.drag_sq: continue
                v=self.board.grid[r][f]
                if not v: continue
                color=WHITE if v>0 else BLACK
                sym=UNICODE[(abs(v),color)]
                x,y=self._sq_xy(r,f); cx,cy=x+SQ//2,y+SQ//2
                self.canvas.create_text(cx+1,cy+2,text=sym,font=("Segoe UI Symbol",34),
                                        fill="#333333",tags="piece")
                fill="#FFFDE7" if color==WHITE else "#1C1C1C"
                self.canvas.create_text(cx,cy,text=sym,font=("Segoe UI Symbol",34),
                                        fill=fill,tags="piece")

    def _draw_float(self,x,y):
        self.canvas.delete("float")
        if not self.drag_piece: return
        pt,color=self.drag_piece
        sym=UNICODE[(pt,color)]
        self.canvas.create_text(x+1,y+2,text=sym,font=("Segoe UI Symbol",40),
                                fill="#222222",tags="float")
        fill="#FFFDE7" if color==WHITE else "#1C1C1C"
        self.canvas.create_text(x,y,text=sym,font=("Segoe UI Symbol",40),
                                fill=fill,tags="float")

    def _update_eval(self):
        raw=evaluate(self.board)*self.board.turn
        clamped=max(-900,min(900,raw))
        w=int(152*(clamped+900)/1800)
        self.eval_c.delete("all")
        self.eval_c.create_rectangle(0,0,w,16,fill="#efefef",outline="")
        self.eval_c.create_rectangle(w,0,152,16,fill="#1a1a1a",outline="")
        sign="+" if raw>0 else ""
        self.eval_var.set(f"{sign}{raw/100:.1f}")

    # ── Mouse ─────────────────────────────────────────────────────────────
    def _press(self,event):
        if self.ai_thinking: return
        if self.board.turn!=self.player_color: return
        sq=self._xy_sq(event.x,event.y)
        if sq is None: return
        r,f=sq; v=self.board.grid[r][f]
        if not v: return
        color=WHITE if v>0 else BLACK
        if color!=self.player_color: return
        self.drag_sq=(r,f); self.drag_piece=(abs(v),color)
        self.legal_targets={(m[2],m[3]) for m in self.board.legal_moves()
                            if (m[0],m[1])==(r,f)}
        self._draw_board(); self._draw_pieces(); self._draw_float(event.x,event.y)

    def _drag(self,event):
        if self.drag_piece:
            self.canvas.delete("float"); self._draw_float(event.x,event.y)

    def _release(self,event):
        if not self.drag_piece: return
        self.canvas.delete("float")
        to=self._xy_sq(event.x,event.y); moved=False
        if to and to in self.legal_targets:
            r1,f1=self.drag_sq; r2,f2=to; promo=0
            pt=abs(self.board.grid[r1][f1])
            pr=7 if self.player_color==WHITE else 0
            if pt==PAWN and r2==pr: promo=self._ask_promo()
            move=(r1,f1,r2,f2,promo)
            if move in self.board.legal_moves():
                self._do_move(move); moved=True
        self.drag_sq=None; self.drag_piece=None; self.legal_targets=set()
        self._redraw()
        if moved and not self.board.is_game_over(): self._start_ai()

    # ── Game ─────────────────────────────────────────────────────────────
    def _do_move(self,move):
        san=_san(self.board,move)
        self.last_move=move; self.board.push(move)
        self.history_san.append(san)
        n=len(self.history_san)
        if n%2==1:
            self.hist_lb.insert(tk.END,f"{(n+1)//2:2}. {san}")
        else:
            last=self.hist_lb.get(tk.END); self.hist_lb.delete(tk.END)
            self.hist_lb.insert(tk.END,f"{last}  {san}")
        self.hist_lb.see(tk.END)
        self._check_over()

    def _check_over(self):
        b=self.board
        if b.is_checkmate():
            winner="Black" if b.turn==WHITE else "White"
            self.status_var.set(f"Checkmate! {winner} wins")
            self._redraw()
            messagebox.showinfo("Game Over",f"Checkmate! {winner} wins!")
        elif b.is_stalemate():
            self.status_var.set("Stalemate — Draw")
            self._redraw(); messagebox.showinfo("Game Over","Stalemate! Draw.")
        elif b.is_insufficient():
            self.status_var.set("Draw — Insufficient material")
        elif b.halfmove>=100:
            self.status_var.set("Draw — 50-move rule")
        elif b.in_check():
            self.status_var.set("Check!")
        else:
            self.status_var.set("Your move" if b.turn==self.player_color else "AI thinking…")

    def _ask_promo(self):
        opts={"Queen":QUEEN,"Rook":ROOK,"Bishop":BISHOP,"Knight":KNIGHT}
        result=[QUEEN]
        dlg=tk.Toplevel(self.root); dlg.title("Promote"); dlg.configure(bg=BG); dlg.grab_set()
        tk.Label(dlg,text="Promote to:",font=("Courier",11),fg=FG,bg=BG).pack(padx=16,pady=8)
        for name,val in opts.items():
            tk.Button(dlg,text=name,font=("Courier",10,"bold"),bg=ACCENT,fg="white",relief=tk.FLAT,
                      command=lambda v=val:[result.__setitem__(0,v),dlg.destroy()]
                      ).pack(fill=tk.X,padx=16,pady=3)
        self.root.wait_window(dlg); return result[0]

    # ── AI ────────────────────────────────────────────────────────────────
    def _start_ai(self):
        self.ai_thinking=True; self.status_var.set("AI thinking…")
        self._anim(0)
        threading.Thread(target=self._ai_thread,daemon=True).start()

    def _anim(self,t):
        if not self.ai_thinking: self.think_var.set(""); return
        self.think_var.set("●"*(t%4+1))
        self.root.after(300,lambda:self._anim(t+1))

    def _ai_thread(self):
        global _stop; _stop=False
        move=find_best_move(self.board,max_depth=self.depth_var.get(),time_limit=8.0)
        self.root.after(0,lambda:self._ai_done(move))

    def _ai_done(self,move):
        self.ai_thinking=False; self.think_var.set("")
        if move and move in self.board.legal_moves():
            self._do_move(move)
        self._redraw()
        if not self.board.is_game_over(): self.status_var.set("Your move")

    # ── Controls ──────────────────────────────────────────────────────────
    def _new_game(self):
        global _stop
        if self.ai_thinking: _stop=True; time.sleep(0.15)
        self.board=Board(); self.last_move=None; self.legal_targets=set()
        self.drag_sq=None; self.drag_piece=None
        self.history_san=[]; self.hist_lb.delete(0,tk.END)
        TT.clear(); self.ai_thinking=False; self.think_var.set("")

        dlg=tk.Toplevel(self.root); dlg.title("Choose side")
        dlg.configure(bg=BG); dlg.grab_set()
        tk.Label(dlg,text="Play as:",font=("Courier",12),fg=FG,bg=BG).pack(padx=20,pady=10)
        for name,c in [("White ♔",WHITE),("Black ♚",BLACK)]:
            tk.Button(dlg,text=name,font=("Courier",11,"bold"),bg=ACCENT,fg="white",relief=tk.FLAT,
                      command=lambda cc=c:[setattr(self,"player_color",cc),dlg.destroy()]
                      ).pack(fill=tk.X,padx=20,pady=4)
        self.root.wait_window(dlg)
        self.flipped=(self.player_color==BLACK)
        self._update_coords(); self.status_var.set("Your move"); self._redraw()
        if self.player_color==BLACK: self._start_ai()

    def _flip(self):
        self.flipped=not self.flipped; self._update_coords(); self._redraw()

    def _undo(self):
        global _stop
        if self.ai_thinking: return
        for _ in range(2):
            if self.board.history: self.board.pop()
            if self.history_san:   self.history_san.pop()
        self.last_move=self.board.history[-1][0] if self.board.history else None
        self.hist_lb.delete(0,tk.END)
        for i in range(0,len(self.history_san),2):
            w=self.history_san[i]
            b=self.history_san[i+1] if i+1<len(self.history_san) else ""
            self.hist_lb.insert(tk.END,f"{i//2+1:2}. {w}  {b}".rstrip())
        self.status_var.set("Your move"); self._redraw()

if __name__=="__main__":
    root=tk.Tk()
    ChessApp(root)
    root.mainloop()
