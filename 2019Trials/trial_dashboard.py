"""
Trial Dashboard Viewer — Trials 10, 11, 12, 13, 14
====================================================
Shows the game grid on the left and three live charts on the right:
  - Score over time
  - Anticipation rate (cumulative)
  - Coordination gap per cycle (handoff gap or counter wait)

Requires:
  - trials_10_to_14.json  (in same folder as this script)
  - pygame, matplotlib

Install:  pip install pygame matplotlib

Controls:
  SPACE          — play / pause
  R              — reset to start
  UP / DOWN      — step one frame
  LEFT / RIGHT   — previous / next trial
  ESC            — quit
"""

import json, os, sys
import pygame
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from io import BytesIO

# ── Config ───────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.abspath(__file__))
DATA_FILE  = os.path.join(BASE, 'trials_10_to_14.json')
COOK_TIME  = 20
FPS        = 12

TRIAL_IDS  = ['10', '11', '12', '13', '14']

LAYOUT_SHORT = {
    'cramped_room':           'Cramped room',
    'asymmetric_advantages':  'Asymmetric adv.',
    'coordination_ring':      'Coordination ring',
    'random3':                'Random3',
    'random0':                'Random0',
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
    'O': (230, 126, 34),
    'D': (149, 165, 166),
    'S': (231, 76,  60),
    'P': (155, 89,  182),
    '1': (44,  62,  80),
    '2': (44,  62,  80),
}
TILE_LABELS    = {'O':'ONI', 'D':'DSH', 'S':'SRV', 'P':'POT'}
PLAYER_COLORS  = [(52, 152, 219), (46, 204, 113)]
HELD_COLORS    = {'onion':(230,126,34), 'dish':(200,200,200),
                  'soup':(241,196,15), 'tomato':(231,76,60)}
SHARED_CTR_COL = (80, 120, 160)

BG     = (15,  20,  40)
WHITE  = (240, 240, 240)
MUTED  = (120, 130, 160)
GOLD   = (241, 196, 15)
GREEN  = (46,  204, 113)
RED    = (231, 76,  60)

# Chart colours matching the widget
CHART_COLORS = {
    '10': '#5DCAA5',
    '11': '#7F77DD',
    '12': '#EF9F27',
    '13': '#D85A30',
    '14': '#378ADD',
}

# ── Metric tracker ────────────────────────────────────────────────────────────
class MetricTracker:
    def __init__(self, coord_type):
        self.coord_type   = coord_type
        self.ant_yes      = 0
        self.ant_tot      = 0
        self.prev_ready   = False
        self.ant_history  = []   # (step, rate)
        self.gap_history  = []   # (step, gap)
        self.score_history= []   # (step, score)
        self._onion_adds  = []
        self._dish_collects = []
        self._counter_items = {}
        self._prev_soups  = {}

    def reset(self):
        self.__init__(self.coord_type)

    def update(self, frame_idx, frame):
        objects = frame['objects']
        players = frame['players']
        score   = frame['score']

        self.score_history.append((frame_idx, score))

        # ── Anticipation ─────────────────────────────────────────────────────
        ready = any(o['name'] == 'soup' and o['is_ready'] for o in objects)
        if ready and not self.prev_ready:
            self.ant_tot += 1
            p0h = players[0].get('held_object')
            p1h = players[1].get('held_object')
            if (p0h and p0h['name'] == 'dish') or (p1h and p1h['name'] == 'dish'):
                self.ant_yes += 1
            self.ant_history.append((frame_idx, self.ant_yes / self.ant_tot))
        self.prev_ready = ready

        # ── Coordination ──────────────────────────────────────────────────────
        if self.coord_type == 'optional':
            curr_soups = {str(o['position']): o for o in objects if o['name'] == 'soup'}
            for key, cs in curr_soups.items():
                ps = self._prev_soups.get(key)
                if ps:
                    pi = len(ps.get('_ingredients', []))
                    ci = len(cs.get('_ingredients', []))
                    if ci > pi:
                        self._onion_adds.append({'step': frame_idx, 'count': ci})
            for p_idx in [0, 1]:
                prev_h = None
                if hasattr(self, '_prev_frame'):
                    prev_h = self._prev_frame['players'][p_idx].get('held_object')
                curr_h = players[p_idx].get('held_object')
                if prev_h and prev_h['name'] == 'dish' and curr_h and curr_h['name'] == 'soup':
                    self._dish_collects.append({'step': frame_idx})
            self._prev_soups = curr_soups

            # Match 3rd onions to next dish collect
            for e in list(self._onion_adds):
                if e['count'] == 3:
                    ready_at = e['step'] + COOK_TIME
                    if frame_idx >= ready_at:
                        nxt = next((d for d in self._dish_collects
                                    if d['step'] >= ready_at - 5), None)
                        if nxt:
                            gap = nxt['step'] - ready_at
                            self.gap_history.append((nxt['step'], gap))
                            self._dish_collects.remove(nxt)
                        self._onion_adds.remove(e)

        else:  # required — counter wait
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
                        self.gap_history.append((frame_idx, wait))
                    del self._counter_items[key]

        self._prev_frame = frame

    @property
    def ant_rate(self):
        return self.ant_yes / max(self.ant_tot, 1)

    @property
    def avg_gap(self):
        if not self.gap_history:
            return 0.0
        return sum(g for _, g in self.gap_history) / len(self.gap_history)


# ── Drawing helpers (grid) ────────────────────────────────────────────────────
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
                t = font_sm.render('RDY', True, (0,0,0))
                surface.blit(t, (cx-t.get_width()//2, cy-t.get_height()//2))
            elif obj['is_cooking']:
                tick = obj.get('_cooking_tick', 0)
                pct  = min(1.0, tick / max(obj.get('cook_time', COOK_TIME), 1))
                col  = (int(230*pct), int(80+46*(1-pct)), 34)
                pygame.draw.circle(surface, col, (cx, cy), tile//3)
                t = font_sm.render(str(int(tick)), True, WHITE)
                surface.blit(t, (cx-t.get_width()//2, cy-t.get_height()//2))
            else:
                pygame.draw.circle(surface, (155,89,182), (cx, cy), tile//4)
        elif obj['name'] in ('onion','dish','tomato'):
            cx = ox + obj['position'][0]*tile + tile//2
            cy = oy + obj['position'][1]*tile + tile//2
            pygame.draw.circle(surface, HELD_COLORS.get(obj['name'], WHITE), (cx,cy), tile//5)

def draw_players(surface, players, ox, oy, tile, font):
    for i, player in enumerate(players):
        px = ox + player['position'][0]*tile + tile//2
        py = oy + player['position'][1]*tile + tile//2
        r  = tile//2 - 4
        pygame.draw.circle(surface, PLAYER_COLORS[i], (px, py), r)
        pygame.draw.circle(surface, WHITE, (px, py), r, 2)
        lbl = font.render(f'P{i}', True, WHITE)
        surface.blit(lbl, (px-lbl.get_width()//2, py-lbl.get_height()//2))
        held = player.get('held_object')
        if held:
            name   = held['name'] if isinstance(held, dict) else str(held)
            hcol   = HELD_COLORS.get(name, WHITE)
            pygame.draw.circle(surface, hcol, (px+r-2, py-r+2), 9)
            sm = pygame.font.SysFont('Arial', 9, bold=True)
            ht = sm.render(name[0].upper(), True, (0,0,0))
            surface.blit(ht, (px+r-2-ht.get_width()//2, py-r+2-ht.get_height()//2))


# ── Chart renderer ────────────────────────────────────────────────────────────
def render_charts(trackers, current_tid, frame_idx, total_frames, chart_w, chart_h):
    """Render all three charts into one matplotlib figure, return as pygame Surface."""
    bg   = '#0F1428'
    fg   = '#B0B8C8'
    grid = '#1E2840'

    fig, axes = plt.subplots(3, 1, figsize=(chart_w/100, chart_h/100), dpi=100)
    fig.patch.set_facecolor(bg)

    titles = ['Score', 'Anticipation rate', 'Coordination gap (steps)']
    ylabels = ['pts', 'rate (0–1)', 'steps']

    for ax, title, ylabel in zip(axes, titles, ylabels):
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=8)
        ax.set_title(title, color=fg, fontsize=9, pad=4)
        ax.set_ylabel(ylabel, color=fg, fontsize=8)
        ax.set_xlabel('timestep', color=fg, fontsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(grid)
        ax.grid(color=grid, linewidth=0.5)
        ax.set_xlim(0, total_frames)

    ax_score, ax_ant, ax_coord = axes

    for tid, tracker in trackers.items():
        col   = CHART_COLORS[tid]
        alpha = 1.0 if tid == current_tid else 0.35
        lw    = 2.0 if tid == current_tid else 1.0
        label = f'T{tid}'

        # Score
        if tracker.score_history:
            xs, ys = zip(*tracker.score_history)
            ax_score.plot(xs, ys, color=col, lw=lw, alpha=alpha, label=label)

        # Anticipation
        if tracker.ant_history:
            xs, ys = zip(*tracker.ant_history)
            ax_ant.step(xs, ys, color=col, lw=lw, alpha=alpha, label=label, where='post')
        ax_ant.set_ylim(-0.05, 1.05)

        # Coordination gap
        if tracker.gap_history:
            xs, ys = zip(*tracker.gap_history)
            marker = '^' if COORD_TYPE.get(trackers[tid]._layout_name, 'optional') == 'required' else 'o'
            ax_coord.scatter(xs, ys, color=col, s=20 if tid == current_tid else 10,
                             alpha=alpha, label=label, marker=marker, zorder=3)

    # Vertical line for current frame
    for ax in axes:
        ax.axvline(x=frame_idx, color='#FFFFFF', lw=0.8, alpha=0.4, linestyle='--')

    # Legend on first chart
    handles = [mpatches.Patch(color=CHART_COLORS[tid],
                               label=f'T{tid} ({LAYOUT_SHORT.get(trackers[tid]._layout_name,"?")})')
               for tid in TRIAL_IDS]
    ax_score.legend(handles=handles, fontsize=7, loc='upper left',
                    facecolor='#1E2840', edgecolor=grid, labelcolor=fg)

    fig.tight_layout(pad=0.8)

    buf = BytesIO()
    fig.savefig(buf, format='png', facecolor=bg, dpi=100)
    plt.close(fig)
    buf.seek(0)
    return pygame.image.load(buf, 'png')


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Load data
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} not found.")
        print("Make sure trials_10_to_14.json is in the same folder as this script.")
        sys.exit(1)

    with open(DATA_FILE) as f:
        data = json.load(f)

    # Attach layout name to each trial entry
    for tid in TRIAL_IDS:
        data[tid]['_layout_name'] = data[tid]['layout_name']

    pygame.init()

    TILE       = 64
    GRID_PAD   = 8
    INFO_H     = 120
    CHART_W    = 540
    CHART_H    = 600
    REDRAW_EVERY = 8   # re-render charts every N frames for performance

    # Compute grid dimensions from first trial
    sample_layout = data[TRIAL_IDS[0]]['layout']
    ROWS = len(sample_layout)
    COLS = len(sample_layout[0])
    GRID_W = COLS * TILE
    GRID_H = ROWS * TILE
    WIN_W  = GRID_W + CHART_W + GRID_PAD * 3
    WIN_H  = max(GRID_H + INFO_H + GRID_PAD * 2, CHART_H + 40)

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Overcooked Trial Dashboard — Trials 10–14')
    clock = pygame.time.Clock()

    font    = pygame.font.SysFont('Arial', 14, bold=True)
    font_sm = pygame.font.SysFont('Arial', 11, bold=True)
    font_xs = pygame.font.SysFont('Arial', 10)

    trial_idx = 0
    frame_idx = 0
    playing   = False
    chart_surface = None
    chart_dirty   = True

    # Create one tracker per trial, store layout name on it
    trackers = {}
    for tid in TRIAL_IDS:
        ct = COORD_TYPE.get(data[tid]['layout_name'], 'optional')
        t  = MetricTracker(ct)
        t._layout_name = data[tid]['layout_name']
        trackers[tid] = t

    def current_tid():
        return TRIAL_IDS[trial_idx]

    def total_frames():
        return len(data[current_tid()]['frames'])

    def reset_all():
        nonlocal frame_idx, playing, chart_surface, chart_dirty
        frame_idx     = 0
        playing       = False
        chart_surface = None
        chart_dirty   = True
        for t in trackers.values():
            t.reset()

    def advance_trackers_to(target):
        """Replay all trackers from 0 to target frame."""
        for t in trackers.values():
            t.reset()
        for fi in range(target + 1):
            for tid in TRIAL_IDS:
                frames = data[tid]['frames']
                if fi < len(frames):
                    trackers[tid].update(fi, frames[fi])

    reset_all()
    advance_trackers_to(0)

    while True:
        tid     = current_tid()
        layout  = data[tid]['layout']
        frames  = data[tid]['frames']
        total   = len(frames)
        frame   = frames[min(frame_idx, total-1)]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    reset_all()
                    advance_trackers_to(0)
                elif event.key == pygame.K_UP:
                    frame_idx = max(0, frame_idx - 1)
                    advance_trackers_to(frame_idx)
                    chart_dirty = True
                elif event.key == pygame.K_DOWN:
                    frame_idx = min(total-1, frame_idx + 1)
                    for tid2 in TRIAL_IDS:
                        f2 = data[tid2]['frames']
                        if frame_idx < len(f2):
                            trackers[tid2].update(frame_idx, f2[frame_idx])
                    chart_dirty = True
                elif event.key == pygame.K_LEFT:
                    trial_idx = (trial_idx - 1) % len(TRIAL_IDS)
                    chart_dirty = True
                elif event.key == pygame.K_RIGHT:
                    trial_idx = (trial_idx + 1) % len(TRIAL_IDS)
                    chart_dirty = True
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); return

        if playing:
            frame_idx += 1
            if frame_idx >= total:
                frame_idx = total - 1
                playing = False
            for tid2 in TRIAL_IDS:
                f2 = data[tid2]['frames']
                if frame_idx < len(f2):
                    trackers[tid2].update(frame_idx, f2[frame_idx])
            if frame_idx % REDRAW_EVERY == 0:
                chart_dirty = True

        # Re-render charts when needed
        if chart_dirty:
            chart_surface = render_charts(trackers, current_tid(), frame_idx, total, CHART_W, CHART_H)
            chart_dirty = False

        screen.fill(BG)

        # ── Grid ─────────────────────────────────────────────────────────────
        ox = GRID_PAD
        oy = 55
        shared = {2} if COORD_TYPE.get(data[tid]['layout_name'], 'optional') == 'required' else None
        draw_grid(screen, layout, ox, oy, TILE, font_sm, shared)
        draw_objects(screen, frame['objects'], ox, oy, TILE, font_sm)
        draw_players(screen, frame['players'], ox, oy, TILE, font)

        # ── Charts ───────────────────────────────────────────────────────────
        if chart_surface:
            screen.blit(chart_surface, (GRID_W + GRID_PAD * 2, 20))

        # ── Header ───────────────────────────────────────────────────────────
        tr = trackers[current_tid()]
        score_now = int(frame['score'])
        del_total = data[tid]['deliveries']

        title = font.render(
            f"Trial {current_tid()} — {LAYOUT_SHORT.get(data[tid]['layout_name'], '?')}",
            True, WHITE)
        screen.blit(title, (ox, 10))

        nav = font_xs.render(
            f"◄ L/R switch trial ►   SPACE play/pause   UP/DOWN step   R reset   ESC quit",
            True, MUTED)
        screen.blit(nav, (ox, 30))

        # ── Info panel below grid ─────────────────────────────────────────────
        iy = oy + GRID_H + 10
        score_t = font.render(f"Score: {score_now}   Deliveries: {del_total}", True, WHITE)
        screen.blit(score_t, (ox, iy))

        ant_col = GREEN if tr.ant_rate >= 0.7 else (GOLD if tr.ant_rate >= 0.4 else RED)
        ant_t   = font.render(f"Anticipation: {tr.ant_rate:.0%}  ({tr.ant_yes}/{tr.ant_tot})", True, ant_col)
        screen.blit(ant_t, (ox, iy + 22))

        coord_type = COORD_TYPE.get(data[tid]['layout_name'], 'optional')
        coord_lbl  = 'Counter wait' if coord_type == 'required' else 'Mean handoff gap'
        coord_col  = GREEN if tr.avg_gap < 5 else (GOLD if tr.avg_gap < 20 else RED)
        coord_t    = font.render(f"{coord_lbl}: {tr.avg_gap:.1f} steps", True, coord_col)
        screen.blit(coord_t, (ox, iy + 44))

        if frame['reward'] > 0:
            dl = font.render('*** DELIVERY! ***', True, GOLD)
            screen.blit(dl, (ox, iy + 66))

        # Soup ready flash
        ready_now = any(o['name'] == 'soup' and o['is_ready'] for o in frame['objects'])
        if ready_now:
            rt = font_sm.render('Soup ready — waiting for collection', True, GOLD)
            screen.blit(rt, (ox, iy + 88))

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_y = WIN_H - 16
        bar_w = GRID_W
        pygame.draw.rect(screen, (40,50,80), (ox, bar_y, bar_w, 6), border_radius=3)
        prog = int(bar_w * frame_idx / max(total-1, 1))
        pygame.draw.rect(screen, (52,152,219), (ox, bar_y, prog, 6), border_radius=3)
        pt = font_xs.render(f'Step {frame_idx+1}/{total}', True, MUTED)
        screen.blit(pt, (ox, bar_y - 14))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
