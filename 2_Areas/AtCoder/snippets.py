"""AtCoder コピペ用スニペット集（Python / PyPy）

使い方: 本番でこのファイルを開き、必要な部分をコピーして提出コードに貼る。
AtCoderは事前準備コードの持ち込み・コピペOK（他人との共有だけNG）。
解説は各スニペットのコメントと、対応する [[アルゴリズム]] ノートを参照。

────────────────────────────────────────────────────────
目次
  1. 高速入出力テンプレ
  2. Union-Find（DSU）      → 実装済み
  3. グラフ探索 BFS/DFS      → 実装済み
  4. 二分探索（めぐる式）    → 実装済み
  5. 累積和 / 尺取り         → 実装済み
  --- ここから下は「学んだら追記」---
  6. ダイクストラ（最短経路）  → 未（[[最短経路]]を学んだら）
  7. セグメント木 / BIT       → 未（[[データ構造]]を学んだら）
  8. 数学（nCr mod・素数篩）  → 一部
────────────────────────────────────────────────────────
"""

# ══════════════════════════════════════════════════════
# 1. 高速入出力テンプレ（毎回これを先頭に）
# ══════════════════════════════════════════════════════
import sys
input = sys.stdin.readline
# 大量入力なら: data = sys.stdin.buffer.read().split()
# 大量出力なら: print('\n'.join(map(str, ans)))
# 再帰DFSを使うなら必ず: sys.setrecursionlimit(10**6)


# ══════════════════════════════════════════════════════
# 2. Union-Find（DSU）   関連: [[Union-Find]]
#    union(a,b): a,bを同じグループに / same(a,b): 同じ? / get_size(x): 人数
#    ※ 頂点は 0-indexed。1-indexedの入力は a-1 して渡す
# ══════════════════════════════════════════════════════
class UnionFind:
    def __init__(self, n):
        self.par = list(range(n))   # par[x]=xの親。par[x]==x なら x が代表(根)
        self.size = [1] * n         # size[x]=グループの人数（代表xのときだけ有効）

    def find(self, x):              # xのグループの代表(根)を返す
        while self.par[x] != x:
            self.par[x] = self.par[self.par[x]]   # 経路圧縮
            x = self.par[x]
        return x

    def union(self, x, y):          # xとyのグループを合体
        x, y = self.find(x), self.find(y)
        if x == y:
            return
        if self.size[x] < self.size[y]:
            x, y = y, x             # 大きい方に小さい方をぶら下げる
        self.par[y] = x
        self.size[x] += self.size[y]

    def same(self, x, y):
        return self.find(x) == self.find(y)

    def get_size(self, x):
        return self.size[self.find(x)]

# 使用例（ABC177 D: 一番大きい友達グループの人数）
# uf = UnionFind(N)
# for _ in range(M):
#     a, b = map(int, input().split())
#     uf.union(a-1, b-1)
# print(max(uf.get_size(i) for i in range(N)))


# ══════════════════════════════════════════════════════
# 3. グラフ探索 BFS / DFS   関連: [[グラフ探索BFS_DFS]]
# ══════════════════════════════════════════════════════
from collections import deque, defaultdict

# --- 隣接リストの作り方 ---
# 頂点番号が小さいとき: g = [[] for _ in range(N)]
# 頂点番号が巨大(10^9等): g = defaultdict(list)  ← ABC277_C
#   g[a].append(b); g[b].append(a)   # 無向なら両方向

# --- BFS（最短手数・重みなし）---
def bfs(g, start, N):
    dist = [-1] * N            # -1=未訪問。最短距離を記録
    dist[start] = 0
    q = deque([start])
    while q:
        v = q.popleft()        # 先頭から取る＝近い順
        for nv in g[v]:
            if dist[nv] == -1:
                dist[nv] = dist[v] + 1
                q.append(nv)
    return dist

# --- 到達可能性だけ（距離不要）: seen で。ABC204_C ---
def reachable(g, start, N):
    seen = [False] * N
    seen[start] = True
    q = deque([start])
    while q:
        v = q.popleft()
        for nv in g[v]:
            if not seen[nv]:
                seen[nv] = True     # push時にマーク（pop時だとキューが膨れる）
                q.append(nv)
    return seen                     # sum(seen) で到達数

# --- グリッド（迷路）BFS ---
def grid_bfs(grid, H, W, sy, sx):
    dist = [[-1] * W for _ in range(H)]
    dist[sy][sx] = 0
    q = deque([(sy, sx)])
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            # ①盤面内 ②壁でない ③未訪問
            if 0 <= ny < H and 0 <= nx < W and grid[ny][nx] != '#' and dist[ny][nx] == -1:
                dist[ny][nx] = dist[y][x] + 1
                q.append((ny, nx))
    return dist


# ══════════════════════════════════════════════════════
# 4. 二分探索   関連: [[二分探索]]
# ══════════════════════════════════════════════════════
from bisect import bisect_left, bisect_right
# ソート済みA: bisect_left(A,x)=x以上の最小位置, bisect_right(A,x)=x以下の個数

# --- 答えで二分探索（めぐる式）---
def meguru(is_ok, ng, ok):
    # is_ok(x): 条件を満たすか。ng:満たさない側, ok:満たす側（両端は範囲外に取る）
    while abs(ok - ng) > 1:
        mid = (ok + ng) // 2
        if is_ok(mid):
            ok = mid
        else:
            ng = mid
    return ok


# ══════════════════════════════════════════════════════
# 5. 累積和 / 尺取り   関連: [[累積和とimos法]] / [[データ構造]]
# ══════════════════════════════════════════════════════
from itertools import accumulate
# S = list(accumulate(A, initial=0))   # S[i]=先頭i個の和。区間[l,r)= S[r]-S[l]


# ══════════════════════════════════════════════════════
# 6. ダイクストラ（最短経路・重みあり）   関連: [[最短経路]]
#    → [[最短経路]]を学び、実戦でACしたらここに実装を貼る
# ══════════════════════════════════════════════════════
# import heapq
# （未実装）


# ══════════════════════════════════════════════════════
# 7. セグメント木 / BIT   関連: [[データ構造]]
#    → [[データ構造]]を学び、実戦でACしたらここに実装を貼る
# ══════════════════════════════════════════════════════
# （未実装）


# ══════════════════════════════════════════════════════
# 8. 数学   関連: [[数学・整数論]]
# ══════════════════════════════════════════════════════
import math
# gcd: math.gcd(a,b) / lcm: math.lcm(a,b) / nCr: math.comb(n,r)
# べき乗mod: pow(a, b, MOD)  ← 繰り返し二乗法（組み込み・爆速）
# 切り捨ては整数演算で: a * 8 // 100  （floatは誤差の危険）

def sieve(n):
    """エラトステネスの篩: n以下の素数判定リスト"""
    if n < 2:
        return [False] * (n + 1)   # n=0,1 のとき is_p[1] 参照で落ちるのを防ぐ
    is_p = [True] * (n + 1)
    is_p[0] = is_p[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        if is_p[i]:
            for j in range(i * i, n + 1, i):
                is_p[j] = False
    return is_p
