import json
import os
import pygame

script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'asymmetric_trials.json')

with open(data_path) as f:
    data = json.load(f)

TILE_COLORS = {
    'X': (92, 64, 51),
    ' ': (44, 62, 80),
    'O': (230, 126, 34),
    'D': (149, 165, 166),
    'S': (231, 76, 60),
    'P': (155, 89, 182),
    '1': (44, 62, 80),
    '2': (44, 62, 80),
}
TILE_LABELS = {'O': 'ONI', 'D': 'DSH', 'S': 'SRV', 'P': 'POT'}
PLAYER_COLORS = [(52, 152, 219), (46, 204, 113)]
HELD_COLORS = {
    'onion': (230, 126, 34),
    'dish': (200, 200, 200),
    'soup': (241, 196, 15),
    'tomato': (231, 76, 60)
}

TILE = 60
FPS = 12


def draw_grid(surface, layout, ox, oy, font_sm):
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            color = TILE_COLORS.get(ch, (44, 62, 80))
            rect = pygame.Rect(ox + c*TILE, oy + r*TILE, TILE-2, TILE-2)
            pygame.draw.rect(surface, color, rect, border_radius=5)
            if ch in TILE_LABELS:
                txt = font_sm.render(TILE_LABELS[ch], True, (255, 255, 255))
                surface.blit(txt, (ox + c*TILE + 4, oy + r*TILE + 4))


def draw_objects(surface, objects, ox, oy, font_sm):
    for obj in objects:
        if obj['name'] == 'soup':
            cx = ox + obj['position'][0]*TILE + TILE//2
            cy = oy + obj['position'][1]*TILE + TILE//2
            if obj['is_ready']:
                pygame.draw.circle(surface, (241, 196, 15), (cx, cy), TILE//3)
                txt = font_sm.render('RDY', True, (0, 0, 0))
                surface.blit(txt, (cx - txt.get_width()//2, cy - txt.get_height()//2))
            elif obj['is_cooking']:
                tick = obj.get('_cooking_tick', 0)
                cook = max(obj.get('cook_time', 20), 1)
                pct = min(1.0, tick / cook)
                color = (int(230*pct), int(80 + 46*(1-pct)), 34)
                pygame.draw.circle(surface, color, (cx, cy), TILE//3)
                txt = font_sm.render(str(int(tick)), True, (255, 255, 255))
                surface.blit(txt, (cx - txt.get_width()//2, cy - txt.get_height()//2))
            else:
                pygame.draw.circle(surface, (155, 89, 182), (cx, cy), TILE//4)
        elif obj['name'] in ('onion', 'dish', 'tomato'):
            cx = ox + obj['position'][0]*TILE + TILE//2
            cy = oy + obj['position'][1]*TILE + TILE//2
            color = HELD_COLORS.get(obj['name'], (200, 200, 200))
            pygame.draw.circle(surface, color, (cx, cy), TILE//5)


def draw_players(surface, players, ox, oy, font):
    for i, player in enumerate(players):
        px = ox + player['position'][0]*TILE + TILE//2
        py = oy + player['position'][1]*TILE + TILE//2
        pygame.draw.circle(surface, PLAYER_COLORS[i], (px, py), TILE//2 - 4)
        pygame.draw.circle(surface, (255, 255, 255), (px, py), TILE//2 - 4, 2)
        lbl = font.render(f'P{i}', True, (255, 255, 255))
        surface.blit(lbl, (px - lbl.get_width()//2, py - lbl.get_height()//2))
        held = player.get('held_object')
        if held:
            name = held['name'] if isinstance(held, dict) else str(held)
            hcolor = HELD_COLORS.get(name, (255, 255, 255))
            pygame.draw.circle(surface, hcolor,
                (px + TILE//2 - 4, py - TILE//2 + 4), 10)
            sm = pygame.font.SysFont('Arial', 10, bold=True)
            ht = sm.render(name[0].upper(), True, (0, 0, 0))
            surface.blit(ht, (px + TILE//2 - 4 - ht.get_width()//2,
                               py - TILE//2 + 4 - ht.get_height()//2))


def main():
    pygame.init()

    trial_76 = data['76']
    trial_66 = data['66']
    layout = trial_76['layout']

    rows_g = len(layout)
    cols_g = len(layout[0])
    grid_w = cols_g * TILE
    grid_h = rows_g * TILE

    GAP = 50
    WIN_W = grid_w * 2 + GAP + 20
    WIN_H = grid_h + 190

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Asymmetric Advantages — Trial 76 (High) vs Trial 66 (Low)')

    font = pygame.font.SysFont('Arial', 15, bold=True)
    font_sm = pygame.font.SysFont('Arial', 11, bold=True)
    font_lg = pygame.font.SysFont('Arial', 17, bold=True)
    font_xs = pygame.font.SysFont('Arial', 11)

    clock = pygame.time.Clock()
    frame_idx = 0
    playing = False
    total_frames = min(len(trial_76['frames']), len(trial_66['frames']))

    # Live tracking
    wait_76 = wait_66 = 0
    wait_counts_76 = []
    wait_counts_66 = []
    pot_empty_76 = pot_empty_66 = 0
    empty_counts_76 = []
    empty_counts_66 = []
    ant_76 = ant_total_76 = 0
    ant_66 = ant_total_66 = 0
    prev_ready_76 = prev_ready_66 = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    frame_idx = 0
                    playing = False
                    wait_76 = wait_66 = 0
                    wait_counts_76.clear()
                    wait_counts_66.clear()
                    pot_empty_76 = pot_empty_66 = 0
                    empty_counts_76.clear()
                    empty_counts_66.clear()
                    ant_76 = ant_total_76 = 0
                    ant_66 = ant_total_66 = 0
                    prev_ready_76 = prev_ready_66 = False
                elif event.key == pygame.K_RIGHT:
                    frame_idx = min(frame_idx + 10, total_frames - 1)
                elif event.key == pygame.K_LEFT:
                    frame_idx = max(frame_idx - 10, 0)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

        if playing:
            frame_idx += 1
            if frame_idx >= total_frames:
                frame_idx = total_frames - 1
                playing = False

        screen.fill((15, 20, 40))

        f76 = trial_76['frames'][frame_idx]
        f66 = trial_66['frames'][frame_idx]

        # Soup ready tracking
        ready_76 = any(o['name']=='soup' and o['is_ready'] for o in f76['objects'])
        ready_66 = any(o['name']=='soup' and o['is_ready'] for o in f66['objects'])
        has_soup_76 = any(o['name']=='soup' for o in f76['objects'])
        has_soup_66 = any(o['name']=='soup' for o in f66['objects'])

        # Anticipation tracking - detect soup just becoming ready
        if ready_76 and not prev_ready_76:
            ant_total_76 += 1
            p0h = f76['players'][0].get('held_object')
            p1h = f76['players'][1].get('held_object')
            p0n = p0h['name'] if p0h else 'nothing'
            p1n = p1h['name'] if p1h else 'nothing'
            if p0n == 'dish' or p1n == 'dish':
                ant_76 += 1

        if ready_66 and not prev_ready_66:
            ant_total_66 += 1
            p0h = f66['players'][0].get('held_object')
            p1h = f66['players'][1].get('held_object')
            p0n = p0h['name'] if p0h else 'nothing'
            p1n = p1h['name'] if p1h else 'nothing'
            if p0n == 'dish' or p1n == 'dish':
                ant_66 += 1

        prev_ready_76 = ready_76
        prev_ready_66 = ready_66

        # Soup wait
        if ready_76:
            wait_76 += 1
        else:
            if wait_76 > 0:
                wait_counts_76.append(wait_76)
            wait_76 = 0

        if ready_66:
            wait_66 += 1
        else:
            if wait_66 > 0:
                wait_counts_66.append(wait_66)
            wait_66 = 0

        # Pot empty
        if not has_soup_76:
            pot_empty_76 += 1
        else:
            if pot_empty_76 > 0:
                empty_counts_76.append(pot_empty_76)
            pot_empty_76 = 0

        if not has_soup_66:
            pot_empty_66 += 1
        else:
            if pot_empty_66 > 0:
                empty_counts_66.append(pot_empty_66)
            pot_empty_66 = 0

        avg_w76 = sum(wait_counts_76)/len(wait_counts_76) if wait_counts_76 else 0
        avg_w66 = sum(wait_counts_66)/len(wait_counts_66) if wait_counts_66 else 0
        ant_pct_76 = 100*ant_76/max(ant_total_76, 1)
        ant_pct_66 = 100*ant_66/max(ant_total_66, 1)

        # Controls
        hint = font_xs.render(
            'SPACE = play/pause    R = reset    LEFT/RIGHT = step 10 frames    ESC = quit',
            True, (120, 130, 160))
        screen.blit(hint, (10, 6))

        ox_76 = 10
        ox_66 = grid_w + GAP + 10
        oy = 72

        # Labels
        lbl76 = font_lg.render('Trial 76 — HIGH FLUENCY', True, (29, 158, 117))
        screen.blit(lbl76, (ox_76, oy - 30))
        lbl66 = font_lg.render('Trial 66 — LOW FLUENCY', True, (226, 75, 74))
        screen.blit(lbl66, (ox_66, oy - 30))

        # Grids
        draw_grid(screen, layout, ox_76, oy, font_sm)
        draw_grid(screen, layout, ox_66, oy, font_sm)

        # Objects
        draw_objects(screen, f76['objects'], ox_76, oy, font_sm)
        draw_objects(screen, f66['objects'], ox_66, oy, font_sm)

        # Players
        draw_players(screen, f76['players'], ox_76, oy, font)
        draw_players(screen, f66['players'], ox_66, oy, font)

        # Stats
        sy = oy + grid_h + 10

        # Trial 76
        sc76 = font.render(f"Score: {int(f76['score'])}   Deliveries: {trial_76['deliveries']}", True, (29, 158, 117))
        screen.blit(sc76, (ox_76, sy))
        sw76 = font.render(f"Avg soup wait: {avg_w76:.1f} steps", True, (180, 220, 180))
        screen.blit(sw76, (ox_76, sy + 22))
        at76 = font.render(f"Anticipation: {ant_pct_76:.0f}%  ({ant_76}/{ant_total_76} events)", True, (100, 200, 150))
        screen.blit(at76, (ox_76, sy + 44))
        if f76['reward'] > 0:
            dl = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl, (ox_76, sy + 66))
        if wait_76 > 0:
            wt = font.render(f'Soup waiting: {wait_76} steps', True, (241, 196, 15))
            screen.blit(wt, (ox_76, sy + 66))

        # Trial 66
        sc66 = font.render(f"Score: {int(f66['score'])}   Deliveries: {trial_66['deliveries']}", True, (226, 75, 74))
        screen.blit(sc66, (ox_66, sy))
        sw66 = font.render(f"Avg soup wait: {avg_w66:.1f} steps", True, (220, 160, 160))
        screen.blit(sw66, (ox_66, sy + 22))
        at66 = font.render(f"Anticipation: {ant_pct_66:.0f}%  ({ant_66}/{ant_total_66} events)", True, (220, 120, 80))
        screen.blit(at66, (ox_66, sy + 44))
        if f66['reward'] > 0:
            dl2 = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl2, (ox_66, sy + 66))
        if wait_66 > 0:
            wt2 = font.render(f'Soup waiting: {wait_66} steps', True, (231, 76, 60))
            screen.blit(wt2, (ox_66, sy + 66))

        # Anticipation highlight when soup just became ready
        if ready_76 and wait_76 <= 3:
            flash = font_lg.render('ANTICIPATED!', True, (100, 255, 180))
            screen.blit(flash, (ox_76, sy + 88))
        if ready_66 and not prev_ready_66:
            flash2 = font_lg.render('NOT ANTICIPATED', True, (255, 120, 80))
            screen.blit(flash2, (ox_66, sy + 88))

        # Progress bar
        bar_y = WIN_H - 22
        bar_w = WIN_W - 20
        pygame.draw.rect(screen, (40, 50, 80), (10, bar_y, bar_w, 8), border_radius=4)
        prog = int(bar_w * frame_idx / max(total_frames - 1, 1))
        pygame.draw.rect(screen, (52, 152, 219), (10, bar_y, prog, 8), border_radius=4)
        pt = font_xs.render(f'Timestep {frame_idx + 1} / {total_frames}', True, (120, 130, 160))
        screen.blit(pt, (10, bar_y - 16))

        # Legend
        legend = [
            ((155, 89, 182), 'Pot'),
            ((230, 126, 34), 'Onions'),
            ((149, 165, 166), 'Dishes'),
            ((231, 76, 60), 'Serve'),
            ((241, 196, 15), 'Soup ready'),
            ((52, 152, 219), 'Player 0'),
            ((46, 204, 113), 'Player 1'),
        ]
        lx = WIN_W // 2 - 240
        for color, label in legend:
            pygame.draw.rect(screen, color, (lx, 28, 12, 12), border_radius=2)
            lt = font_xs.render(label, True, (160, 170, 200))
            screen.blit(lt, (lx + 16, 27))
            lx += lt.get_width() + 30

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
