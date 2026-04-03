"""
Side-by-Side Viewer — Team 8+9 vs Team 6+7
============================================
Shows both teams playing the same layout simultaneously,
one grid on the left and one on the right.

Requires:
  - teams_side_by_side.json  (same folder as this script)
  - pygame

Install:  pip install pygame

Controls:
  SPACE          — play / pause
  R              — reset to start
  UP / DOWN      — step one frame
  LEFT / RIGHT   — previous / next layout
  ESC            — quit
"""

import json, os, sys
import pygame

# ── Config ────────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, 'teams_side_by_side.json')
FPS       = 12
COOK_TIME = 20

LAYOUT_ORDER = [
    'cramped_room',
    'asymmetric_advantages',
    'coordination_ring',
    'random3',
    'random0',
]

LAYOUT_LABELS = {
    'cramped_room':          'Cramped room',
    'asymmetric_advantages': 'Asymmetric advantages',
    'coordination_ring':     'Coordination ring',
    'random3':               'Random3',
    'random0':               'Random0',
}

COORD_TYPE = {
    'cramped_room': 'optional', 'asymmetric_advantages': 'optional',
    'coordination_ring': 'optional', 'random3': 'optional', 'random0': 'required',
}

TILE_COLORS = {
    'X': (92,  64,  51),
    ' ': (44,  62,  80),
    'O': (230, 126,  34),
    'T': (231,  76,  60),
    'D': (149, 165, 166),
    'S': (231,  76,  60),
    'P': (155,  89, 182),
    '1': (44,   62,  80),
    '2': (44,   62,  80),
}
TILE_LABELS   = {'O':'ONI','T':'TOM','D':'DSH','S':'SRV','P':'POT'}
PLAYER_COLORS = [(52, 152, 219), (46, 204, 113)]
HELD_COLORS   = {'onion':(230,126,34),'tomato':(231,76,60),
                 'dish':(200,200,200),'soup':(241,196,15)}
SHARED_CTR    = (80, 120, 160)

BG    = (15,  20,  40)
WHITE = (240, 240, 240)
MUTED = (120, 130, 160)
GOLD  = (241, 196,  15)
GREEN = (46,  204, 113)
RED   = (231,  76,  60)
BLUE  = (52,  152, 219)

TEAM_COLORS = {
    '8+9': (52,  152, 219),
    '6+7': (46,  204, 113),
}


# ── Metric tracker ────────────────────────────────────────────────────────────
class MetricTracker:
    def __init__(self, coord_type):
        self.coord_type     = coord_type
        self.ant_yes        = 0
        self.ant_tot        = 0
        self.prev_ready     = False
        self.gap_history    = []
        self._onion_adds    = []
        self._dish_collects = []
        self._prev_soups    = {}
        self._prev_frame    = None
        self._counter_items = {}
        self.deliveries_so_far = 0

    def reset(self):
        self.__init__(self.coord_type)

    def update(self, frame_idx, frame):
        objects = frame['objects']
        players = frame['players']

        if frame['reward'] > 0:
            self.deliveries_so_far += 1

        # Anticipation
        ready = any(o['name']=='soup' and o.get('is_ready') for o in objects)
        if ready and not self.prev_ready:
            self.ant_tot += 1
            p0h = players[0].get('held_object')
            p1h = players[1].get('held_object')
            if (p0h and p0h['name']=='dish') or (p1h and p1h['name']=='dish'):
                self.ant_yes += 1
        self.prev_ready = ready

        # Coordination
        if self.coord_type == 'optional':
            curr_soups = {str(o['position']): o for o in objects if o['name']=='soup'}
            for key, cs in curr_soups.items():
                ps = self._prev_soups.get(key)
                if ps:
                    pi = len(ps.get('_ingredients',[]))
                    ci = len(cs.get('_ingredients',[]))
                    if ci > pi:
                        self._onion_adds.append({'step': frame_idx, 'count': ci})
            if self._prev_frame:
                for p_idx in [0,1]:
                    ph = self._prev_frame['players'][p_idx].get('held_object')
                    ch = players[p_idx].get('held_object')
                    if ph and ph['name']=='dish' and ch and ch['name']=='soup':
                        self._dish_collects.append({'step': frame_idx})
            self._prev_soups = curr_soups
            for e in list(self._onion_adds):
                if e['count'] == 3:
                    ready_at = e['step'] + COOK_TIME
                    if frame_idx >= ready_at:
                        nxt = next((d for d in self._dish_collects
                                    if d['step'] >= ready_at - 5), None)
                        if nxt:
                            self.gap_history.append(nxt['step'] - ready_at)
                            self._dish_collects.remove(nxt)
                        self._onion_adds.remove(e)
        else:
            curr_ctr = {}
            for o in objects:
                if o['position'][0] == 2 and o['name'] in ('onion','dish'):
                    curr_ctr[str(o['position'])] = o['name']
            for key in curr_ctr:
                if key not in self._counter_items:
                    self._counter_items[key] = frame_idx
            for key in list(self._counter_items.keys()):
                if key not in curr_ctr:
                    wait = frame_idx - self._counter_items[key]
                    if wait >= 1:
                        self.gap_history.append(wait)
                    del self._counter_items[key]

        self._prev_frame = frame

    @property
    def ant_rate(self):
        return self.ant_yes / max(self.ant_tot, 1)

    @property
    def avg_gap(self):
        return sum(self.gap_history) / len(self.gap_history) if self.gap_history else 0.0


# ── Drawing ───────────────────────────────────────────────────────────────────
def draw_grid(surface, layout, ox, oy, tile, font_sm, shared_cols=None):
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            col = TILE_COLORS.get(ch, (44,62,80))
            if shared_cols and ch == 'X' and c in shared_cols:
                col = SHARED_CTR
            rect = pygame.Rect(ox + c*tile, oy + r*tile, tile-2, tile-2)
            pygame.draw.rect(surface, col, rect, border_radius=4)
            if ch in TILE_LABELS:
                t = font_sm.render(TILE_LABELS[ch], True, WHITE)
                surface.blit(t, (ox + c*tile + 3, oy + r*tile + 3))

def draw_objects(surface, objects, ox, oy, tile, font_sm):
    for obj in objects:
        if obj['name'] == 'soup':
            cx = ox + obj['position'][0]*tile + tile//2
            cy = oy + obj['position'][1]*tile + tile//2
            if obj.get('is_ready'):
                pygame.draw.circle(surface, GOLD, (cx,cy), tile//3)
                t = font_sm.render('RDY', True, (0,0,0))
                surface.blit(t, (cx-t.get_width()//2, cy-t.get_height()//2))
            elif obj.get('is_cooking'):
                tick = obj.get('_cooking_tick', 0)
                pct  = min(1.0, tick / max(obj.get('cook_time', COOK_TIME), 1))
                col  = (int(230*pct), int(80+46*(1-pct)), 34)
                pygame.draw.circle(surface, col, (cx,cy), tile//3)
                t = font_sm.render(str(int(tick)), True, WHITE)
                surface.blit(t, (cx-t.get_width()//2, cy-t.get_height()//2))
            else:
                pygame.draw.circle(surface, (155,89,182), (cx,cy), tile//4)
        elif obj['name'] in ('onion','dish','tomato'):
            cx = ox + obj['position'][0]*tile + tile//2
            cy = oy + obj['position'][1]*tile + tile//2
            pygame.draw.circle(surface, HELD_COLORS.get(obj['name'], WHITE), (cx,cy), tile//5)

def draw_players(surface, players, ox, oy, tile, font):
    for i, player in enumerate(players):
        px = ox + player['position'][0]*tile + tile//2
        py = oy + player['position'][1]*tile + tile//2
        r  = tile//2 - 4
        pygame.draw.circle(surface, PLAYER_COLORS[i], (px,py), r)
        pygame.draw.circle(surface, WHITE, (px,py), r, 2)
        lbl = font.render(f'P{i}', True, WHITE)
        surface.blit(lbl, (px-lbl.get_width()//2, py-lbl.get_height()//2))
        held = player.get('held_object')
        if held:
            name = held['name'] if isinstance(held,dict) else str(held)
            hcol = HELD_COLORS.get(name, WHITE)
            pygame.draw.circle(surface, hcol, (px+r-2, py-r+2), 9)
            sm = pygame.font.SysFont('Arial', 9, bold=True)
            ht = sm.render(name[0].upper(), True, (0,0,0))
            surface.blit(ht, (px+r-2-ht.get_width()//2, py-r+2-ht.get_height()//2))

def draw_stats(surface, tracker, score, total_score, deliveries,
               team_name, ox, oy, width, font, font_sm, font_xs, coord_type):
    tc = TEAM_COLORS[team_name]

    # Team label
    lbl = font.render(f'Team {team_name}', True, tc)
    surface.blit(lbl, (ox, oy))

    # Score bar
    score_t = font_sm.render(
        f"Score: {int(score)} / {total_score}   Del: {tracker.deliveries_so_far}/{deliveries}",
        True, WHITE)
    surface.blit(score_t, (ox, oy + 22))

    # Anticipation
    ant_col = GREEN if tracker.ant_rate >= 0.7 else (GOLD if tracker.ant_rate >= 0.4 else RED)
    ant_t   = font_sm.render(
        f"Anticipation: {tracker.ant_rate:.0%}  ({tracker.ant_yes}/{tracker.ant_tot})",
        True, ant_col)
    surface.blit(ant_t, (ox, oy + 40))

    # Coordination
    coord_lbl = 'Counter wait' if coord_type == 'required' else 'Handoff gap'
    coord_col = GREEN if tracker.avg_gap < 5 else (GOLD if tracker.avg_gap < 20 else RED)
    coord_t   = font_sm.render(f"{coord_lbl}: {tracker.avg_gap:.1f} steps", True, coord_col)
    surface.blit(coord_t, (ox, oy + 58))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found.")
        print("Make sure teams_side_by_side.json is in the same folder.")
        sys.exit(1)

    with open(DATA_FILE) as f:
        data = json.load(f)

    pygame.init()

    TILE   = 64
    PAD    = 10
    GAP    = 20       # gap between two grids
    INFO_H = 100

    # Find the largest layout to size the window
    max_cols = max(len(data[l]['8+9']['layout'][0]) for l in LAYOUT_ORDER)
    max_rows = max(len(data[l]['8+9']['layout'])    for l in LAYOUT_ORDER)

    GRID_W = max_cols * TILE
    GRID_H = max_rows * TILE
    WIN_W  = GRID_W * 2 + GAP + PAD * 2
    WIN_H  = GRID_H + INFO_H + PAD * 2 + 60

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Side-by-Side: Team 8+9 vs Team 6+7')
    clock  = pygame.time.Clock()

    font    = pygame.font.SysFont('Arial', 14, bold=True)
    font_sm = pygame.font.SysFont('Arial', 12, bold=True)
    font_xs = pygame.font.SysFont('Arial', 10)

    layout_idx = 0
    frame_idx  = 0
    playing    = False

    def cur_layout():
        return LAYOUT_ORDER[layout_idx]

    def cur_data():
        return data[cur_layout()]

    def total():
        return min(len(cur_data()['8+9']['frames']),
                   len(cur_data()['6+7']['frames']))

    trackers = {
        '8+9': MetricTracker('optional'),
        '6+7': MetricTracker('optional'),
    }

    def reset_trackers():
        ct = COORD_TYPE[cur_layout()]
        for team in ['8+9','6+7']:
            trackers[team] = MetricTracker(ct)

    def update_trackers(fi):
        for team in ['8+9','6+7']:
            frames = cur_data()[team]['frames']
            if fi < len(frames):
                trackers[team].update(fi, frames[fi])

    def advance_to(target):
        reset_trackers()
        for fi in range(target + 1):
            update_trackers(fi)

    reset_trackers()
    advance_to(0)

    while True:
        d   = cur_data()
        tot = total()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    frame_idx = 0
                    playing   = False
                    advance_to(0)
                elif event.key == pygame.K_UP:
                    frame_idx = max(0, frame_idx - 1)
                    advance_to(frame_idx)
                elif event.key == pygame.K_DOWN:
                    frame_idx = min(tot-1, frame_idx + 1)
                    update_trackers(frame_idx)
                elif event.key == pygame.K_LEFT:
                    layout_idx = (layout_idx - 1) % len(LAYOUT_ORDER)
                    frame_idx  = 0
                    playing    = False
                    reset_trackers()
                    advance_to(0)
                elif event.key == pygame.K_RIGHT:
                    layout_idx = (layout_idx + 1) % len(LAYOUT_ORDER)
                    frame_idx  = 0
                    playing    = False
                    reset_trackers()
                    advance_to(0)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); return

        if playing:
            frame_idx += 1
            if frame_idx >= tot:
                frame_idx = tot - 1
                playing   = False
            update_trackers(frame_idx)

        screen.fill(BG)

        # ── Header ───────────────────────────────────────────────────────────
        nav = font_xs.render(
            'L/R = switch layout   SPACE = play/pause   UP/DOWN = step   R = reset   ESC = quit',
            True, MUTED)
        screen.blit(nav, (PAD, 6))

        layout_lbl = font.render(
            f"{LAYOUT_LABELS[cur_layout()]}  ({layout_idx+1}/5)", True, WHITE)
        screen.blit(layout_lbl, (PAD, 22))

        # ── Grids side by side ────────────────────────────────────────────────
        oy = 45
        ox_left  = PAD
        ox_right = PAD + GRID_W + GAP

        shared = {2} if COORD_TYPE[cur_layout()] == 'required' else None

        for team, ox in [('8+9', ox_left), ('6+7', ox_right)]:
            layout  = d[team]['layout']
            frames  = d[team]['frames']
            frame   = frames[min(frame_idx, len(frames)-1)]
            draw_grid(screen, layout, ox, oy, TILE, font_sm, shared)
            draw_objects(screen, frame['objects'], ox, oy, TILE, font_sm)
            draw_players(screen, frame['players'], ox, oy, TILE, font)

        # ── Divider ───────────────────────────────────────────────────────────
        div_x = PAD + GRID_W + GAP // 2
        pygame.draw.line(screen, (40, 55, 90),
                         (div_x, oy), (div_x, oy + GRID_H), 1)

        # ── Stats panels ─────────────────────────────────────────────────────
        iy = oy + GRID_H + 12

        for team, ox in [('8+9', ox_left), ('6+7', ox_right)]:
            frame = d[team]['frames'][min(frame_idx, len(d[team]['frames'])-1)]
            draw_stats(
                screen, trackers[team],
                frame['score'], d[team]['score'], d[team]['deliveries'],
                team, ox, iy, GRID_W,
                font, font_sm, font_xs, COORD_TYPE[cur_layout()]
            )

            # Delivery flash
            if frame['reward'] > 0:
                dl = font_sm.render('DELIVERY!', True, GOLD)
                screen.blit(dl, (ox, iy + 76))

        # ── Score comparison banner ───────────────────────────────────────────
        s89 = int(d['8+9']['frames'][min(frame_idx, len(d['8+9']['frames'])-1)]['score'])
        s67 = int(d['6+7']['frames'][min(frame_idx, len(d['6+7']['frames'])-1)]['score'])
        if s89 != s67:
            leader = '8+9' if s89 > s67 else '6+7'
            gap    = abs(s89 - s67)
            lc     = TEAM_COLORS[leader]
            banner = font_sm.render(f"Team {leader} leads by {gap} pts", True, lc)
            screen.blit(banner, (WIN_W//2 - banner.get_width()//2, iy))
        else:
            tied = font_sm.render("Tied", True, MUTED)
            screen.blit(tied, (WIN_W//2 - tied.get_width()//2, iy))

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_y = WIN_H - 14
        bar_w = WIN_W - PAD * 2
        pygame.draw.rect(screen, (40,50,80), (PAD, bar_y, bar_w, 6), border_radius=3)
        prog = int(bar_w * frame_idx / max(tot-1, 1))
        pygame.draw.rect(screen, BLUE, (PAD, bar_y, prog, 6), border_radius=3)
        pt = font_xs.render(f'Step {frame_idx+1} / {tot}', True, MUTED)
        screen.blit(pt, (PAD, bar_y - 14))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()