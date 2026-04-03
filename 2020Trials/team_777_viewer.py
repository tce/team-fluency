"""
Team 777deef2 Viewer — All 8 Layouts, All 8 Layouts
==============================================
Visualises the highest-scoring team across all 8 layouts.
Shows the game grid, live metrics, current recipe orders,
and bonus order highlighted.

Requires:
  - team_777_trials.json  (same folder as this script)
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
DATA_FILE = os.path.join(BASE, 'team_777_trials.json')
FPS       = 12

# Layout display order
LAYOUT_ORDER = [
    'counter_circuit',
    'marshmallow_experiment',
    'marshmallow_experiment_coordination',
    'soup_coordination',
    'you_shall_not_pass',
    'asymmetric_advantages_tomato',
    'cramped_corridor',
    'inverse_marshmallow_experiment',
]

LAYOUT_LABELS = {
    'counter_circuit':                     'Counter circuit',
    'marshmallow_experiment':              'Marshmallow experiment',
    'marshmallow_experiment_coordination': 'Marshmallow coord.',
    'soup_coordination':                   'Soup coordination',
    'you_shall_not_pass':                  'You shall not pass',
    'asymmetric_advantages_tomato':        'Asymmetric adv. tomato',
    'cramped_corridor':                    'Cramped corridor',
    'inverse_marshmallow_experiment':      'Inverse marshmallow',
}

# Tile legend — 2020 layouts add T (tomato dispenser)
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
TILE_LABELS = {'O': 'ONI', 'T': 'TOM', 'D': 'DSH', 'S': 'SRV', 'P': 'POT'}

PLAYER_COLORS = [(52, 152, 219), (46, 204, 113)]
HELD_COLORS   = {
    'onion':  (230, 126,  34),
    'tomato': (231,  76,  60),
    'dish':   (200, 200, 200),
    'soup':   (241, 196,  15),
}

BG    = (15,  20,  40)
WHITE = (240, 240, 240)
MUTED = (120, 130, 160)
GOLD  = (241, 196,  15)
GREEN = (46,  204, 113)
RED   = (231,  76,  60)
BLUE  = (52,  152, 219)


# ── Drawing ───────────────────────────────────────────────────────────────────
def draw_grid(surface, layout, ox, oy, tile, font_sm):
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            col  = TILE_COLORS.get(ch, (44, 62, 80))
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
                pygame.draw.circle(surface, GOLD, (cx, cy), tile//3)
                t = font_sm.render('RDY', True, (0, 0, 0))
                surface.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))
            elif obj.get('is_cooking'):
                tick = obj.get('_cooking_tick', 0)
                cook = max(obj.get('cook_time', 20), 1)
                pct  = min(1.0, tick / cook)
                col  = (int(230*pct), int(80 + 46*(1-pct)), 34)
                pygame.draw.circle(surface, col, (cx, cy), tile//3)
                t = font_sm.render(str(int(tick)), True, WHITE)
                surface.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))
                # Show ingredients in pot
                ings = obj.get('_ingredients', [])
                ing_str = '+'.join(x['name'][0].upper() for x in ings)
                if ing_str:
                    it = font_sm.render(ing_str, True, WHITE)
                    surface.blit(it, (cx - it.get_width()//2, cy + tile//3 + 2))
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
        pygame.draw.circle(surface, WHITE, (px, py), r, 2)
        lbl = font.render(f'P{i}', True, WHITE)
        surface.blit(lbl, (px - lbl.get_width()//2, py - lbl.get_height()//2))
        held = player.get('held_object')
        if held:
            name = held['name'] if isinstance(held, dict) else str(held)
            hcol = HELD_COLORS.get(name, WHITE)
            pygame.draw.circle(surface, hcol, (px + r - 2, py - r + 2), 9)
            sm = pygame.font.SysFont('Arial', 9, bold=True)
            ht = sm.render(name[0].upper(), True, (0, 0, 0))
            surface.blit(ht, (px + r - 2 - ht.get_width()//2,
                               py - r + 2 - ht.get_height()//2))


def format_recipe(order):
    ings = order.get('ingredients', [])
    counts = {}
    for ing in ings:
        counts[ing] = counts.get(ing, 0) + 1
    parts = []
    for ing, cnt in counts.items():
        label = 'Onion' if ing == 'onion' else 'Tomato'
        parts.append(f"{cnt}×{label}" if cnt > 1 else label)
    return ' + '.join(parts)


def draw_orders(surface, frame, ox, oy, width, font_sm, font_xs):
    bonus   = frame.get('bonus_orders', [])
    all_ord = frame.get('all_orders', [])
    bonus_strs = {str(sorted(o['ingredients'])) for o in bonus}

    pygame.draw.rect(surface, (25, 35, 65),
                     pygame.Rect(ox, oy, width, 20 + len(all_ord)*20), border_radius=4)

    title = font_xs.render('ORDERS', True, MUTED)
    surface.blit(title, (ox + 6, oy + 4))

    for i, order in enumerate(all_ord):
        key    = str(sorted(order['ingredients']))
        is_bon = key in bonus_strs
        text   = format_recipe(order)
        if is_bon:
            text  = '★ ' + text
            color = GOLD
            pygame.draw.rect(surface, (50, 40, 10),
                             pygame.Rect(ox + 2, oy + 20 + i*20, width - 4, 18),
                             border_radius=3)
        else:
            color = WHITE
        t = font_sm.render(text, True, color)
        surface.blit(t, (ox + 8, oy + 22 + i*20))

    return 20 + len(all_ord)*20


# ── Metric tracker ────────────────────────────────────────────────────────────
class MetricTracker:
    def __init__(self):
        self.ant_yes        = 0
        self.ant_tot        = 0
        self.prev_ready     = False
        self.gap_history    = []
        self._onion_adds    = []
        self._dish_collects = []
        self._prev_soups    = {}
        self._prev_frame    = None
        self.deliveries_so_far = 0

    def reset(self):
        self.__init__()

    def update(self, frame_idx, frame):
        objects = frame['objects']
        players = frame['players']

        if frame['reward'] > 0:
            self.deliveries_so_far += 1

        # Anticipation
        ready = any(o['name'] == 'soup' and o.get('is_ready') for o in objects)
        if ready and not self.prev_ready:
            self.ant_tot += 1
            p0h = players[0].get('held_object')
            p1h = players[1].get('held_object')
            if (p0h and p0h['name'] == 'dish') or (p1h and p1h['name'] == 'dish'):
                self.ant_yes += 1
        self.prev_ready = ready

        # Coordination — handoff gap
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
                ph = self._prev_frame['players'][p_idx].get('held_object')
                ch = players[p_idx].get('held_object')
                if ph and ph['name'] == 'dish' and ch and ch['name'] == 'soup':
                    self._dish_collects.append({'step': frame_idx})
        self._prev_soups = curr_soups

        COOK_TIME = 20
        for e in list(self._onion_adds):
            if e['count'] >= 2:  # 2020 allows shorter recipes
                ready_at = e['step'] + COOK_TIME
                if frame_idx >= ready_at:
                    nxt = next((d for d in self._dish_collects
                                if d['step'] >= ready_at - 5), None)
                    if nxt:
                        self.gap_history.append(nxt['step'] - ready_at)
                        self._dish_collects.remove(nxt)
                    self._onion_adds.remove(e)

        self._prev_frame = frame

    @property
    def ant_rate(self):
        return self.ant_yes / max(self.ant_tot, 1)

    @property
    def avg_gap(self):
        return sum(self.gap_history) / len(self.gap_history) if self.gap_history else 0.0


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found.")
        print("Make sure team_777_trials.json is in the same folder.")
        sys.exit(1)

    with open(DATA_FILE) as f:
        data = json.load(f)

    # Filter to available layouts in order
    layouts = [l for l in LAYOUT_ORDER if l in data]

    pygame.init()

    TILE   = 68
    PAD    = 12
    INFO_H = 160

    # Size to largest layout
    max_cols = max(len(data[l]['layout'][0]) for l in layouts)
    max_rows = max(len(data[l]['layout'])    for l in layouts)
    GRID_W   = max_cols * TILE
    GRID_H   = max_rows * TILE
    WIN_W    = GRID_W + PAD * 2
    WIN_H    = GRID_H + INFO_H + PAD * 2 + 50

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Team 777deef2 Viewer — All 8 Layouts')
    clock  = pygame.time.Clock()

    font    = pygame.font.SysFont('Arial', 15, bold=True)
    font_sm = pygame.font.SysFont('Arial', 12, bold=True)
    font_xs = pygame.font.SysFont('Arial', 11)

    layout_idx = 0
    frame_idx  = 0
    playing    = False
    tracker    = MetricTracker()

    def current_layout():
        return layouts[layout_idx]

    def current_data():
        return data[current_layout()]

    def total():
        return len(current_data()['frames'])

    def reset():
        nonlocal frame_idx, playing
        frame_idx = 0
        playing   = False
        tracker.reset()

    def advance_to(target):
        tracker.reset()
        for fi in range(target + 1):
            frames = current_data()['frames']
            if fi < len(frames):
                tracker.update(fi, frames[fi])

    reset()
    advance_to(0)

    while True:
        d      = current_data()
        layout = d['layout']
        frames = d['frames']
        tot    = len(frames)
        frame  = frames[min(frame_idx, tot - 1)]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    reset()
                    advance_to(0)
                elif event.key == pygame.K_UP:
                    frame_idx = max(0, frame_idx - 1)
                    advance_to(frame_idx)
                elif event.key == pygame.K_DOWN:
                    frame_idx = min(tot - 1, frame_idx + 1)
                    tracker.update(frame_idx, frames[frame_idx])
                elif event.key == pygame.K_LEFT:
                    layout_idx = (layout_idx - 1) % len(layouts)
                    reset()
                    advance_to(0)
                elif event.key == pygame.K_RIGHT:
                    layout_idx = (layout_idx + 1) % len(layouts)
                    reset()
                    advance_to(0)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); return

        if playing:
            frame_idx += 1
            if frame_idx >= tot:
                frame_idx = tot - 1
                playing = False
            tracker.update(frame_idx, frames[frame_idx])

        screen.fill(BG)

        # ── Header ───────────────────────────────────────────────────────────
        nav = font_xs.render(
            '◄ L/R switch layout ►   SPACE play/pause   UP/DOWN step   R reset   ESC quit',
            True, MUTED)
        screen.blit(nav, (PAD, 6))

        title = font.render(
            f"{LAYOUT_LABELS.get(current_layout(), current_layout())}  "
            f"({layout_idx+1}/{len(layouts)})",
            True, WHITE)
        screen.blit(title, (PAD, 22))

        score_lbl = font.render(
            f"Score: {int(frame['score'])} / {int(d['score'])}   "
            f"Deliveries: {tracker.deliveries_so_far} / {d['deliveries']}",
            True, GREEN)
        screen.blit(score_lbl, (PAD, 40))

        # ── Grid ─────────────────────────────────────────────────────────────
        ox = PAD
        oy = 62
        draw_grid(screen, layout, ox, oy, TILE, font_sm)
        draw_objects(screen, frame['objects'], ox, oy, TILE, font_sm)
        draw_players(screen, frame['players'], ox, oy, TILE, font)

        # ── Info panel ───────────────────────────────────────────────────────
        iy = oy + len(layout) * TILE + 12

        # Anticipation
        ant_col = GREEN if tracker.ant_rate >= 0.7 else (GOLD if tracker.ant_rate >= 0.4 else RED)
        ant_t   = font.render(
            f"Anticipation: {tracker.ant_rate:.0%}  ({tracker.ant_yes}/{tracker.ant_tot})",
            True, ant_col)
        screen.blit(ant_t, (PAD, iy))

        # Coordination
        coord_col = GREEN if tracker.avg_gap < 5 else (GOLD if tracker.avg_gap < 20 else RED)
        coord_t   = font.render(f"Mean handoff gap: {tracker.avg_gap:.1f} steps", True, coord_col)
        screen.blit(coord_t, (PAD, iy + 24))

        # Delivery flash
        if frame['reward'] > 0:
            dl = font.render('*** DELIVERY! ***', True, GOLD)
            screen.blit(dl, (PAD, iy + 48))

        # Soup ready indicator
        ready_now = any(o['name'] == 'soup' and o.get('is_ready') for o in frame['objects'])
        if ready_now:
            rt = font_sm.render('Soup ready — waiting for collection', True, GOLD)
            screen.blit(rt, (PAD, iy + 72))

        # Orders panel — right side
        orders_x = GRID_W - 180
        if orders_x < ox + 10:
            orders_x = ox + 10
        draw_orders(screen, frame, orders_x, iy, 175, font_sm, font_xs)

        # ── Legend ───────────────────────────────────────────────────────────
        legend = [
            ((230, 126, 34),  'Onion'),
            ((231,  76, 60),  'Tomato'),
            ((149, 165, 166), 'Dish'),
            ((155,  89, 182), 'Pot'),
            ((231,  76,  60), 'Serve'),
            (GOLD,            'Soup ready'),
            (PLAYER_COLORS[0],'P0'),
            (PLAYER_COLORS[1],'P1'),
        ]
        lx = PAD
        ly = WIN_H - 30
        for col, lbl in legend:
            pygame.draw.rect(screen, col, (lx, ly, 10, 10), border_radius=2)
            lt = font_xs.render(lbl, True, MUTED)
            screen.blit(lt, (lx + 13, ly - 1))
            lx += lt.get_width() + 22

        # ── Progress bar ─────────────────────────────────────────────────────
        bar_y = WIN_H - 14
        bar_w = WIN_W - PAD * 2
        pygame.draw.rect(screen, (40, 50, 80), (PAD, bar_y, bar_w, 6), border_radius=3)
        prog = int(bar_w * frame_idx / max(tot - 1, 1))
        pygame.draw.rect(screen, BLUE, (PAD, bar_y, prog, 6), border_radius=3)
        pt = font_xs.render(f'Step {frame_idx+1} / {tot}', True, MUTED)
        screen.blit(pt, (PAD, bar_y - 14))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
