"""
Overcooked Fluency Viewer
=========================
Displays high vs low fluency trial pairs side by side for all 5 layouts.
Press LEFT/RIGHT arrow keys to switch between layouts.

Controls:
  SPACE       — play / pause
  R           — reset to start
  arrow UP/DOWN  — step 1 frame
  arrow LEFT/RIGHT — previous / next layout
  ESC         — quit

Metrics shown live:
  - Anticipation rate (dish in hand when soup ready)
  - Coordination metric:
      random0: counter wait time (required handoff via shared wall)
      all others: handoff gap (loading-to-collection cycle)
  - Soup ready but uncollected (pot state indicator)
"""

import json, os, sys
import pygame

# ── Data paths ──────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))

LAYOUTS = [
    {
        'name':       'Cramped room',
        'file':       os.path.join(BASE, 'cramped_room_trials.json'),
        'high_id':    '10',
        'low_id':     '80',
        'high_label': 'Trial 10',
        'low_label':  'Trial 80',
        'coord_type': 'optional',
        'tile_size':  80,
        'note':       'Both players can reach all stations',
    },
    {
        'name':       'Asymmetric advantages',
        'file':       os.path.join(BASE, 'asymmetric_trials.json'),
        'high_id':    '76',
        'low_id':     '66',
        'high_label': 'Trial 76',
        'low_label':  'Trial 66',
        'coord_type': 'optional',
        'tile_size':  52,
        'note':       'Both players can reach all stations',
    },
    {
        'name':       'Coordination ring',
        'file':       os.path.join(BASE, 'coordination_ring_trials.json'),
        'high_id':    '112',
        'low_id':     '67',
        'high_label': 'Trial 112',
        'low_label':  'Trial 67',
        'coord_type': 'optional',
        'tile_size':  80,
        'note':       'Both players can reach all stations',
    },
    {
        'name':       'Random3',
        'file':       os.path.join(BASE, 'random3_trials_v2.json'),
        'high_id':    '78',
        'low_id':     '88',
        'high_label': 'Trial 78',
        'low_label':  'Trial 88',
        'coord_type': 'optional',
        'tile_size':  60,
        'note':       'Both players can reach all stations',
    },
    {
        'name':       'Random0',
        'file':       os.path.join(BASE, 'random0_trials.json'),
        'high_id':    '114',
        'low_id':     '69',
        'high_label': 'Trial 114',
        'low_label':  'Trial 69',
        'coord_type': 'required',
        'tile_size':  80,
        'note':       'REQUIRED handoff — shared counter at col 2',
    },
]

# ── Colours ──────────────────────────────────────────────────────────────────
TILE_COLORS = {
    'X': (92,  64,  51),
    ' ': (44,  62,  80),
    'O': (230, 126, 34),
    'D': (149, 165, 166),
    'S': (231, 76,  60),
    'P': (155, 89,  182),
    '1': (44,  62,  80),
    '2': (44,  62,  80),
}
TILE_LABELS   = {'O': 'ONI', 'D': 'DSH', 'S': 'SRV', 'P': 'POT'}
PLAYER_COLORS = [(52, 152, 219), (46, 204, 113)]
HELD_COLORS   = {
    'onion':  (230, 126, 34),
    'dish':   (200, 200, 200),
    'soup':   (241, 196, 15),
    'tomato': (231, 76,  60),
}
SHARED_COUNTER_COLOR = (80, 120, 160)   # highlight for random0 shared wall

BG      = (15,  20,  40)
GREEN   = (29,  158, 117)
RED     = (226, 75,  74)
GOLD    = (241, 196, 15)
MUTED   = (120, 130, 160)
WHITE   = (240, 240, 240)

FPS = 12


# ── Drawing helpers ───────────────────────────────────────────────────────────
def draw_grid(surface, layout, ox, oy, tile, font_sm, shared_cols=None):
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            color = TILE_COLORS.get(ch, (44, 62, 80))
            # Highlight shared counter column in random0
            if shared_cols and ch == 'X' and c in shared_cols:
                color = SHARED_COUNTER_COLOR
            rect = pygame.Rect(ox + c*tile, oy + r*tile, tile-2, tile-2)
            pygame.draw.rect(surface, color, rect, border_radius=5)
            if ch in TILE_LABELS:
                txt = font_sm.render(TILE_LABELS[ch], True, (255, 255, 255))
                surface.blit(txt, (ox + c*tile + 4, oy + r*tile + 4))


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
                pct  = min(1.0, tick / max(obj.get('cook_time', 20), 1))
                col  = (int(230*pct), int(80 + 46*(1-pct)), 34)
                pygame.draw.circle(surface, col, (cx, cy), tile//3)
                t = font_sm.render(str(int(tick)), True, (255, 255, 255))
                surface.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))
            else:
                pygame.draw.circle(surface, (155, 89, 182), (cx, cy), tile//4)
        elif obj['name'] in ('onion', 'dish', 'tomato'):
            cx = ox + obj['position'][0]*tile + tile//2
            cy = oy + obj['position'][1]*tile + tile//2
            pygame.draw.circle(surface, HELD_COLORS.get(obj['name'], WHITE),
                                (cx, cy), tile//5)


def draw_players(surface, players, ox, oy, tile, font):
    for i, player in enumerate(players):
        px = ox + player['position'][0]*tile + tile//2
        py = oy + player['position'][1]*tile + tile//2
        r  = tile//2 - 4
        pygame.draw.circle(surface, PLAYER_COLORS[i], (px, py), r)
        pygame.draw.circle(surface, WHITE,             (px, py), r, 2)
        lbl = font.render(f'P{i}', True, WHITE)
        surface.blit(lbl, (px - lbl.get_width()//2, py - lbl.get_height()//2))
        held = player.get('held_object')
        if held:
            name   = held['name'] if isinstance(held, dict) else str(held)
            hcolor = HELD_COLORS.get(name, WHITE)
            pygame.draw.circle(surface, hcolor, (px + r - 2, py - r + 2), 10)
            sm = pygame.font.SysFont('Arial', 10, bold=True)
            ht = sm.render(name[0].upper(), True, (0, 0, 0))
            surface.blit(ht, (px + r - 2 - ht.get_width()//2,
                               py - r + 2 - ht.get_height()//2))


# ── Live metric tracker ───────────────────────────────────────────────────────
class MetricTracker:
    def __init__(self, coord_type, layout):
        self.coord_type  = coord_type
        self.layout      = layout

        # Anticipation
        self.ant_total   = 0
        self.ant_count   = 0
        self.prev_ready  = False

        # Optional coordination: handoff gap
        self.gaps        = []
        self.prev_soups  = {}

        # Required coordination: counter wait (random0)
        self.counter_items = {}   # str(pos) -> step placed
        self.counter_waits = []

        # Soup ready timer
        self.wait_now    = 0
        self.wait_list   = []

    def reset(self):
        self.__init__(self.coord_type, self.layout)

    def update(self, frame, frame_idx):
        objects  = frame['objects']
        players  = frame['players']

        # ── Soup ready for anticipation ───────────────────────────────────
        ready = any(o['name'] == 'soup' and o['is_ready'] for o in objects)

        if ready and not self.prev_ready:
            self.ant_total += 1
            p0h = players[0].get('held_object')
            p1h = players[1].get('held_object')
            if (p0h and p0h['name'] == 'dish') or (p1h and p1h['name'] == 'dish'):
                self.ant_count += 1

        # ── Soup wait tracker ─────────────────────────────────────────────
        if ready:
            self.wait_now += 1
        else:
            if self.wait_now > 0:
                self.wait_list.append(self.wait_now)
            self.wait_now = 0

        self.prev_ready = ready

        # ── Optional coordination: handoff gap ───────────────────────────
        if self.coord_type == 'optional':
            curr_soups = {str(o['position']): o for o in objects
                         if o['name'] == 'soup'}
            COOK_TIME = 20
            for key, cs in curr_soups.items():
                ps = self.prev_soups.get(key)
                if ps:
                    pi = len(ps.get('_ingredients', []))
                    ci = len(cs.get('_ingredients', []))
                    if ci == 3 and pi < 3:
                        # Third onion just added — cooking starts
                        ready_at = frame_idx + COOK_TIME
                        self._pending_ready = getattr(self, '_pending_ready', [])
                        self._pending_ready.append(ready_at)

            # Check if any pending ready events fired
            pending = getattr(self, '_pending_ready', [])
            for p_ready in list(pending):
                if frame_idx >= p_ready:
                    # Find if someone has a dish
                    p0h = players[0].get('held_object')
                    p1h = players[1].get('held_object')
                    has_dish = (p0h and p0h['name']=='dish') or (p1h and p1h['name']=='dish')
                    pending.remove(p_ready)

            self.prev_soups = curr_soups

        # ── Required coordination: counter wait ───────────────────────────
        if self.coord_type == 'required':
            curr_counter = {}
            for o in objects:
                if o['position'][0] == 2 and o['name'] in ('onion', 'dish'):
                    curr_counter[str(o['position'])] = (o['name'], frame_idx)

            # New items on counter
            for key, (name, step) in curr_counter.items():
                if key not in self.counter_items:
                    self.counter_items[key] = frame_idx

            # Items that left counter
            for key in list(self.counter_items.keys()):
                if key not in curr_counter:
                    wait = frame_idx - self.counter_items[key]
                    if wait >= 1:
                        self.counter_waits.append(wait)
                    del self.counter_items[key]

    @property
    def ant_rate(self):
        return self.ant_count / max(self.ant_total, 1)

    @property
    def avg_soup_wait(self):
        return sum(self.wait_list) / len(self.wait_list) if self.wait_list else 0

    @property
    def avg_counter_wait(self):
        return sum(self.counter_waits) / len(self.counter_waits) if self.counter_waits else 0

    @property
    def coord_label(self):
        if self.coord_type == 'required':
            avg = self.avg_counter_wait
            return f'Counter wait: {avg:.1f} steps'
        else:
            w = self.avg_soup_wait
            return f'Avg soup wait: {w:.1f} steps'


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    pygame.init()

    # Load all layout data
    all_data = []
    for cfg in LAYOUTS:
        with open(cfg['file']) as f:
            d = json.load(f)
        all_data.append(d)

    layout_idx = 0

    def get_cfg():
        return LAYOUTS[layout_idx]

    def get_data():
        return all_data[layout_idx]

    def make_trackers():
        cfg = get_cfg()
        data = get_data()
        layout = data[cfg['high_id']]['layout']
        return (MetricTracker(cfg['coord_type'], layout),
                MetricTracker(cfg['coord_type'], layout))

    def reset_all():
        nonlocal frame_idx, playing, tracker_h, tracker_l
        frame_idx = 0
        playing   = False
        tracker_h, tracker_l = make_trackers()

    # Window sizing
    def compute_window():
        cfg   = get_cfg()
        data  = get_data()
        tile  = cfg['tile_size']
        layout = data[cfg['high_id']]['layout']
        rows_g = len(layout)
        cols_g = len(layout[0])
        gw = cols_g * tile
        gh = rows_g * tile
        WIN_W = gw * 2 + 60 + 20
        WIN_H = gh + 230
        return WIN_W, WIN_H, gw, gh, tile

    WIN_W, WIN_H, gw, gh, tile = compute_window()
    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
    pygame.display.set_caption('Overcooked Fluency Viewer')

    font    = pygame.font.SysFont('Arial', 15, bold=True)
    font_sm = pygame.font.SysFont('Arial', 12, bold=True)
    font_lg = pygame.font.SysFont('Arial', 17, bold=True)
    font_xs = pygame.font.SysFont('Arial', 11)
    font_nav= pygame.font.SysFont('Arial', 13, bold=True)

    clock    = pygame.time.Clock()
    frame_idx = 0
    playing   = False
    tracker_h, tracker_l = make_trackers()

    while True:
        cfg   = get_cfg()
        data  = get_data()
        tile  = cfg['tile_size']
        layout_h = data[cfg['high_id']]['layout']
        layout_l = data[cfg['low_id']]['layout']
        total = min(len(data[cfg['high_id']]['frames']),
                    len(data[cfg['low_id']]['frames']))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    reset_all()
                elif event.key == pygame.K_UP:
                    frame_idx = max(frame_idx - 1, 0)
                elif event.key == pygame.K_DOWN:
                    frame_idx = min(frame_idx + 1, total - 1)
                elif event.key == pygame.K_LEFT:
                    layout_idx = (layout_idx - 1) % len(LAYOUTS)
                    WIN_W, WIN_H, gw, gh, tile = compute_window()
                    screen = pygame.display.set_mode((WIN_W, WIN_H))
                    reset_all()
                elif event.key == pygame.K_RIGHT:
                    layout_idx = (layout_idx + 1) % len(LAYOUTS)
                    WIN_W, WIN_H, gw, gh, tile = compute_window()
                    screen = pygame.display.set_mode((WIN_W, WIN_H))
                    reset_all()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); return

        if playing:
            frame_idx += 1
            if frame_idx >= total:
                frame_idx = total - 1
                playing = False

        fh = data[cfg['high_id']]['frames'][min(frame_idx, len(data[cfg['high_id']]['frames'])-1)]
        fl = data[cfg['low_id']]['frames'][min(frame_idx, len(data[cfg['low_id']]['frames'])-1)]

        tracker_h.update(fh, frame_idx)
        tracker_l.update(fl, frame_idx)

        WIN_W, WIN_H, gw, gh, tile = compute_window()
        screen.fill(BG)

        # ── Header ─────────────────────────────────────────────────────────
        hint = font_xs.render(
            'SPACE=play/pause   R=reset   UP/DOWN=step   LEFT/RIGHT=switch layout   ESC=quit',
            True, MUTED)
        screen.blit(hint, (WIN_W//2 - hint.get_width()//2, 5))

        # Layout nav
        nav = font_nav.render(
            f'◄  {layout_idx+1}/{len(LAYOUTS)}: {cfg["name"].upper()}  ►',
            True, WHITE)
        screen.blit(nav, (WIN_W//2 - nav.get_width()//2, 22))

        note = font_xs.render(cfg['note'], True, MUTED)
        screen.blit(note, (WIN_W//2 - note.get_width()//2, 40))

        # Shared counter legend for random0
        if cfg['coord_type'] == 'required':
            leg = font_xs.render('■  Shared counter (col 2) — required handoff zone',
                                 True, SHARED_COUNTER_COLOR)
            screen.blit(leg, (WIN_W//2 - leg.get_width()//2, 55))

        # ── Grids ──────────────────────────────────────────────────────────
        oy  = 78
        ox_h = 10
        ox_l = gw + 60 + 10

        shared_cols = {2} if cfg['coord_type'] == 'required' else None

        draw_grid(screen, layout_h, ox_h, oy, tile, font_sm, shared_cols)
        draw_grid(screen, layout_l, ox_l, oy, tile, font_sm, shared_cols)
        draw_objects(screen, fh['objects'], ox_h, oy, tile, font_sm)
        draw_objects(screen, fl['objects'], ox_l, oy, tile, font_sm)
        draw_players(screen, fh['players'], ox_h, oy, tile, font)
        draw_players(screen, fl['players'], ox_l, oy, tile, font)

        # ── Trial labels ───────────────────────────────────────────────────
        lbl_h = font_lg.render(f'{cfg["high_label"]} — HIGH FLUENCY', True, GREEN)
        lbl_l = font_lg.render(f'{cfg["low_label"]} — LOW FLUENCY',  True, RED)
        screen.blit(lbl_h, (ox_h, oy - 28))
        screen.blit(lbl_l, (ox_l, oy - 28))

        # ── Stats panels ───────────────────────────────────────────────────
        sy = oy + gh + 10

        def draw_stats(ox, tracker, frame, color, is_high):
            score = int(frame['score'])
            deliv = data[cfg['high_id']]['deliveries'] if is_high else data[cfg['low_id']]['deliveries']

            sc = font.render(f'Score: {score}   Deliveries: {deliv}', True, color)
            screen.blit(sc, (ox, sy))

            ant_pct = 100 * tracker.ant_rate
            ant_col = GREEN if (ant_pct >= 70 and is_high) or (ant_pct < 70 and not is_high) else WHITE
            ant_txt = font.render(
                f'Anticipation: {ant_pct:.0f}%  ({tracker.ant_count}/{tracker.ant_total})',
                True, ant_col)
            screen.blit(ant_txt, (ox, sy + 22))

            coord_txt = font.render(tracker.coord_label, True,
                                    GREEN if is_high else RED)
            screen.blit(coord_txt, (ox, sy + 44))

            # Delivery flash
            if frame['reward'] > 0:
                dl = font_lg.render('*** DELIVERY! ***', True, GOLD)
                screen.blit(dl, (ox, sy + 68))

            # Live soup wait counter
            if tracker.wait_now > 0:
                wt_col = GOLD if is_high else RED
                wt = font.render(f'Soup waiting: {tracker.wait_now} steps', True, wt_col)
                screen.blit(wt, (ox, sy + 68 if frame['reward'] == 0 else sy + 90))

            # Counter wait flash for random0
            if cfg['coord_type'] == 'required' and tracker.counter_items:
                max_wait = max(frame_idx - v for v in tracker.counter_items.values())
                if max_wait > 0:
                    ct = font.render(f'Item on counter: {max_wait} steps',
                                    True, GOLD if is_high else RED)
                    screen.blit(ct, (ox, sy + 90))

            # Anticipation flash
            ready_now = any(o['name']=='soup' and o['is_ready'] for o in frame['objects'])
            if ready_now and tracker.wait_now <= 2 and tracker.wait_now > 0:
                fl2 = font_lg.render('ANTICIPATED!', True, (100, 255, 180))
                screen.blit(fl2, (ox, sy + 112))

        draw_stats(ox_h, tracker_h, fh, GREEN, True)
        draw_stats(ox_l, tracker_l, fl, RED,   False)

        # ── Progress bar ───────────────────────────────────────────────────
        bar_y = WIN_H - 22
        bar_w = WIN_W - 20
        pygame.draw.rect(screen, (40, 50, 80), (10, bar_y, bar_w, 8), border_radius=4)
        prog = int(bar_w * frame_idx / max(total - 1, 1))
        pygame.draw.rect(screen, (52, 152, 219), (10, bar_y, prog, 8), border_radius=4)
        pt = font_xs.render(f'Timestep {frame_idx+1} / {total}', True, MUTED)
        screen.blit(pt, (10, bar_y - 16))

        # ── Legend ─────────────────────────────────────────────────────────
        legend = [
            ((155, 89, 182), 'Pot'),
            ((230, 126, 34), 'Onions'),
            ((149, 165, 166), 'Dishes'),
            ((231, 76, 60),  'Serve'),
            (GOLD,           'Soup ready'),
            (PLAYER_COLORS[0], 'Player 0'),
            (PLAYER_COLORS[1], 'Player 1'),
        ]
        lx = WIN_W // 2 - 260
        for color, label in legend:
            pygame.draw.rect(screen, color, (lx, 58, 12, 12), border_radius=2)
            lt = font_xs.render(label, True, (160, 170, 200))
            screen.blit(lt, (lx + 16, 57))
            lx += lt.get_width() + 28

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
