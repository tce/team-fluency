"""
Trial Viewer — Trials 10, 11, 12, 13, 14
==========================================
Shows the game grid and live metrics. No charts.

Requires:
  - trials_10_to_14.json  (in same folder as this script)
  - pygame

Install:  pip install pygame

Controls:
  SPACE          — play / pause
  R              — reset to start
  UP / DOWN      — step one frame
  LEFT / RIGHT   — previous / next trial
  ESC            — quit
"""

import json, os, sys
import pygame

# ── Config ───────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, 'trials_10_to_14.json')
COOK_TIME = 20
FPS       = 12

TRIAL_IDS = ['10', '11', '12', '13', '14']

LAYOUT_SHORT = {
    'cramped_room':          'Cramped room',
    'asymmetric_advantages': 'Asymmetric adv.',
    'coordination_ring':     'Coordination ring',
    'random3':               'Random3',
    'random0':               'Random0',
}

COORD_TYPE = {
    'cramped_room':          'optional',
    'asymmetric_advantages': 'optional',
    'coordination_ring':     'optional',
    'random3':               'optional',
    'random0':               'required',
}

TILE_COLORS = {
    'X': (92,  64,  51),
    ' ': (44,  62,  80),
    'O': (230, 126,  34),
    'D': (149, 165, 166),
    'S': (231,  76,  60),
    'P': (155,  89, 182),
    '1': (44,   62,  80),
    '2': (44,   62,  80),
}
TILE_LABELS   = {'O': 'ONI', 'D': 'DSH', 'S': 'SRV', 'P': 'POT'}
PLAYER_COLORS = [(52, 152, 219), (46, 204, 113)]
HELD_COLORS   = {
    'onion':  (230, 126,  34),
    'dish':   (200, 200, 200),
    'soup':   (241, 196,  15),
    'tomato': (231,  76,  60),
}
SHARED_CTR_COL = (80, 120, 160)

BG    = (15,  20,  40)
WHITE = (240, 240, 240)
MUTED = (120, 130, 160)
GOLD  = (241, 196,  15)
GREEN = (46,  204, 113)
RED   = (231,  76,  60)


# ── Metric tracker ────────────────────────────────────────────────────────────
class MetricTracker:
    def __init__(self, coord_type):
        self.coord_type      = coord_type
        self.ant_yes         = 0
        self.ant_tot         = 0
        self.prev_ready      = False
        self.gap_history     = []
        self._onion_adds     = []
        self._dish_collects  = []
        self._counter_items  = {}
        self._prev_soups     = {}
        self._prev_frame     = None

    def reset(self):
        self.__init__(self.coord_type)

    def update(self, frame_idx, frame):
        objects = frame['objects']
        players = frame['players']

        # Anticipation
        ready = any(o['name'] == 'soup' and o['is_ready'] for o in objects)
        if ready and not self.prev_ready:
            self.ant_tot += 1
            p0h = players[0].get('held_object')
            p1h = players[1].get('held_object')
            if (p0h and p0h['name'] == 'dish') or (p1h and p1h['name'] == 'dish'):
                self.ant_yes += 1
        self.prev_ready = ready

        # Coordination
        if self.coord_type == 'optional':
            curr_soups = {str(o['position']): o for o in objects if o['name'] == 'soup'}
            for key, cs in curr_soups.items():
                ps = self._prev_soups.get(key)
                if ps:
                    pi = len(ps.get('_ingredients', []))
                    ci = len(cs.get('_ingredients', []))
                    if ci > pi:
                        self._onion_adds.append({'step': frame_idx, 'count': ci})
            if self._prev_frame:
                for p_idx in [0, 1]:
                    prev_h = self._prev_frame['players'][p_idx].get('held_object')
                    curr_h = players[p_idx].get('held_object')
                    if prev_h and prev_h['name'] == 'dish' and curr_h and curr_h['name'] == 'soup':
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
                if o['position'][0] == 2 and o['name'] in ('onion', 'dish'):
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
            col = TILE_COLORS.get(ch, (44, 62, 80))
            if shared_cols and ch == 'X' and c in shared_cols:
                col = SHARED_CTR_COL
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
            if obj['is_ready']:
                pygame.draw.circle(surface, GOLD, (cx, cy), tile//3)
                t = font_sm.render('RDY', True, (0, 0, 0))
                surface.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))
            elif obj['is_cooking']:
                tick = obj.get('_cooking_tick', 0)
                pct  = min(1.0, tick / max(obj.get('cook_time', COOK_TIME), 1))
                col  = (int(230*pct), int(80 + 46*(1-pct)), 34)
                pygame.draw.circle(surface, col, (cx, cy), tile//3)
                t = font_sm.render(str(int(tick)), True, WHITE)
                surface.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))
            else:
                pygame.draw.circle(surface, (155, 89, 182), (cx, cy), tile//4)
        elif obj['name'] in ('onion', 'dish', 'tomato'):
            cx = ox + obj['position'][0]*tile + tile//2
            cy = oy + obj['position'][1]*tile + tile//2
            pygame.draw.circle(surface, HELD_COLORS.get(obj['name'], WHITE), (cx, cy), tile//5)


def draw_players(surface, players, ox, oy, tile, font):
    for i, player in enumerate(players):
        px = ox + player['position'][0]*tile + tile//2
        py = oy + player['position'][1]*tile + tile//2
        r  = tile//2 - 4
        pygame.draw.circle(surface, PLAYER_COLORS[i], (px, py), r)
        pygame.draw.circle(surface, WHITE, (px, py), r, 2)
        lbl = font.render(f'P{i}', True, WHITE)
        surface.blit(lbl, (px - lbl.get_width()//2, py - lbl.get_height()//2))
        held = player.get('held_object')
        if held:
            name  = held['name'] if isinstance(held, dict) else str(held)
            hcol  = HELD_COLORS.get(name, WHITE)
            pygame.draw.circle(surface, hcol, (px + r - 2, py - r + 2), 9)
            sm = pygame.font.SysFont('Arial', 9, bold=True)
            ht = sm.render(name[0].upper(), True, (0, 0, 0))
            surface.blit(ht, (px + r - 2 - ht.get_width()//2,
                               py - r + 2 - ht.get_height()//2))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found.")
        print("Make sure trials_10_to_14.json is in the same folder as this script.")
        sys.exit(1)

    with open(DATA_FILE) as f:
        data = json.load(f)

    pygame.init()

    TILE   = 80
    PAD    = 12
    INFO_H = 130

    # Size window to the largest layout
    max_cols = max(len(data[tid]['layout'][0]) for tid in TRIAL_IDS)
    max_rows = max(len(data[tid]['layout'])    for tid in TRIAL_IDS)
    GRID_W = max_cols * TILE
    GRID_H = max_rows * TILE
    WIN_W  = GRID_W + PAD * 2
    WIN_H  = GRID_H + INFO_H + PAD * 2 + 50

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Overcooked Trial Viewer — Trials 10–14')
    clock = pygame.time.Clock()

    font    = pygame.font.SysFont('Arial', 15, bold=True)
    font_sm = pygame.font.SysFont('Arial', 12, bold=True)
    font_xs = pygame.font.SysFont('Arial', 11)

    trial_idx = 0
    frame_idx = 0
    playing   = False

    trackers = {}
    for tid in TRIAL_IDS:
        ct = COORD_TYPE.get(data[tid]['layout_name'], 'optional')
        trackers[tid] = MetricTracker(ct)

    def tid():
        return TRIAL_IDS[trial_idx]

    def total():
        return len(data[tid()]['frames'])

    def reset_all():
        nonlocal frame_idx, playing
        frame_idx = 0
        playing   = False
        for t in trackers.values():
            t.reset()

    def advance_to(target):
        for t in trackers.values():
            t.reset()
        for fi in range(target + 1):
            for t_id in TRIAL_IDS:
                frames = data[t_id]['frames']
                if fi < len(frames):
                    trackers[t_id].update(fi, frames[fi])

    reset_all()
    advance_to(0)

    while True:
        t_id   = tid()
        layout = data[t_id]['layout']
        frames = data[t_id]['frames']
        tot    = len(frames)
        frame  = frames[min(frame_idx, tot - 1)]
        tr     = trackers[t_id]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    reset_all()
                    advance_to(0)
                elif event.key == pygame.K_UP:
                    frame_idx = max(0, frame_idx - 1)
                    advance_to(frame_idx)
                elif event.key == pygame.K_DOWN:
                    frame_idx = min(tot - 1, frame_idx + 1)
                    for t_id2 in TRIAL_IDS:
                        f2 = data[t_id2]['frames']
                        if frame_idx < len(f2):
                            trackers[t_id2].update(frame_idx, f2[frame_idx])
                elif event.key == pygame.K_LEFT:
                    trial_idx = (trial_idx - 1) % len(TRIAL_IDS)
                elif event.key == pygame.K_RIGHT:
                    trial_idx = (trial_idx + 1) % len(TRIAL_IDS)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); return

        if playing:
            frame_idx += 1
            if frame_idx >= tot:
                frame_idx = tot - 1
                playing = False
            for t_id2 in TRIAL_IDS:
                f2 = data[t_id2]['frames']
                if frame_idx < len(f2):
                    trackers[t_id2].update(frame_idx, f2[frame_idx])

        screen.fill(BG)

        # ── Header ────────────────────────────────────────────────────────────
        nav = font_xs.render(
            f'◄ L/R switch trial ►   SPACE play/pause   UP/DOWN step   R reset   ESC quit',
            True, MUTED)
        screen.blit(nav, (PAD, 8))

        title = font.render(
            f'Trial {t_id}  —  {LAYOUT_SHORT.get(data[t_id]["layout_name"], "?")}  '
            f'({trial_idx + 1}/{len(TRIAL_IDS)})',
            True, WHITE)
        screen.blit(title, (PAD, 26))

        # ── Grid ──────────────────────────────────────────────────────────────
        ox = PAD
        oy = 50
        shared = {2} if COORD_TYPE.get(data[t_id]['layout_name'], 'optional') == 'required' else None
        draw_grid(screen, layout, ox, oy, TILE, font_sm, shared)
        draw_objects(screen, frame['objects'], ox, oy, TILE, font_sm)
        draw_players(screen, frame['players'], ox, oy, TILE, font)

        # ── Info panel ────────────────────────────────────────────────────────
        iy = oy + len(layout) * TILE + 14

        score_t = font.render(
            f"Score: {int(frame['score'])}   Deliveries: {data[t_id]['deliveries']}",
            True, WHITE)
        screen.blit(score_t, (PAD, iy))

        ant_col = GREEN if tr.ant_rate >= 0.7 else (GOLD if tr.ant_rate >= 0.4 else RED)
        ant_t   = font.render(
            f"Anticipation: {tr.ant_rate:.0%}  ({tr.ant_yes}/{tr.ant_tot})",
            True, ant_col)
        screen.blit(ant_t, (PAD, iy + 24))

        coord_lbl = 'Counter wait' if COORD_TYPE.get(data[t_id]['layout_name']) == 'required' \
                    else 'Mean handoff gap'
        coord_col = GREEN if tr.avg_gap < 5 else (GOLD if tr.avg_gap < 20 else RED)
        coord_t   = font.render(f"{coord_lbl}: {tr.avg_gap:.1f} steps", True, coord_col)
        screen.blit(coord_t, (PAD, iy + 48))

        if frame['reward'] > 0:
            dl = font.render('*** DELIVERY! ***', True, GOLD)
            screen.blit(dl, (PAD, iy + 72))

        ready_now = any(o['name'] == 'soup' and o['is_ready'] for o in frame['objects'])
        if ready_now:
            rt = font_sm.render('Soup ready — waiting for collection', True, GOLD)
            screen.blit(rt, (PAD, iy + 96))

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_y = WIN_H - 18
        bar_w = WIN_W - PAD * 2
        pygame.draw.rect(screen, (40, 50, 80), (PAD, bar_y, bar_w, 6), border_radius=3)
        prog = int(bar_w * frame_idx / max(tot - 1, 1))
        pygame.draw.rect(screen, (52, 152, 219), (PAD, bar_y, prog, 6), border_radius=3)
        pt = font_xs.render(f'Step {frame_idx + 1} / {tot}', True, MUTED)
        screen.blit(pt, (PAD, bar_y - 15))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
