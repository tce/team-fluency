import json
import os
import pygame

script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'coordination_ring_trials.json')

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

TILE = 80
FPS = 12


def draw_grid(surface, layout, ox, oy, font_sm):
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            color = TILE_COLORS.get(ch, (44, 62, 80))
            rect = pygame.Rect(ox + c*TILE, oy + r*TILE, TILE-2, TILE-2)
            pygame.draw.rect(surface, color, rect, border_radius=6)
            if ch in TILE_LABELS:
                txt = font_sm.render(TILE_LABELS[ch], True, (255, 255, 255))
                surface.blit(txt, (ox + c*TILE + 5, oy + r*TILE + 5))


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
        pygame.draw.circle(surface, PLAYER_COLORS[i], (px, py), TILE//2 - 6)
        pygame.draw.circle(surface, (255, 255, 255), (px, py), TILE//2 - 6, 2)
        lbl = font.render(f'P{i}', True, (255, 255, 255))
        surface.blit(lbl, (px - lbl.get_width()//2, py - lbl.get_height()//2))
        held = player.get('held_object')
        if held:
            name = held['name'] if isinstance(held, dict) else str(held)
            hcolor = HELD_COLORS.get(name, (255, 255, 255))
            pygame.draw.circle(surface, hcolor,
                (px + TILE//2 - 6, py - TILE//2 + 6), 12)
            sm = pygame.font.SysFont('Arial', 11, bold=True)
            ht = sm.render(name[0].upper(), True, (0, 0, 0))
            surface.blit(ht, (px + TILE//2 - 6 - ht.get_width()//2,
                               py - TILE//2 + 6 - ht.get_height()//2))


def main():
    pygame.init()

    trial_112 = data['112']
    trial_67 = data['67']
    layout = trial_112['layout']

    rows_g = len(layout)
    cols_g = len(layout[0])
    grid_w = cols_g * TILE
    grid_h = rows_g * TILE

    GAP = 60
    WIN_W = grid_w * 2 + GAP + 20
    WIN_H = grid_h + 200

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Coordination Ring — Trial 112 (High Fluency) vs Trial 67 (Low Fluency)')

    font = pygame.font.SysFont('Arial', 15, bold=True)
    font_sm = pygame.font.SysFont('Arial', 12, bold=True)
    font_lg = pygame.font.SysFont('Arial', 17, bold=True)
    font_xs = pygame.font.SysFont('Arial', 11)

    clock = pygame.time.Clock()
    frame_idx = 0
    playing = False
    total_frames = min(len(trial_112['frames']), len(trial_67['frames']))

    # Live tracking
    wait_112 = wait_67 = 0
    wait_counts_112 = []
    wait_counts_67 = []
    ant_112 = ant_total_112 = 0
    ant_67 = ant_total_67 = 0
    prev_ready_112 = prev_ready_67 = False
    pot_empty_112 = pot_empty_67 = 0
    empty_counts_112 = []
    empty_counts_67 = []

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
                    wait_112 = wait_67 = 0
                    wait_counts_112.clear()
                    wait_counts_67.clear()
                    ant_112 = ant_total_112 = 0
                    ant_67 = ant_total_67 = 0
                    prev_ready_112 = prev_ready_67 = False
                    pot_empty_112 = pot_empty_67 = 0
                    empty_counts_112.clear()
                    empty_counts_67.clear()
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

        f112 = trial_112['frames'][min(frame_idx, len(trial_112['frames'])-1)]
        f67  = trial_67['frames'][min(frame_idx, len(trial_67['frames'])-1)]

        ready_112 = any(o['name']=='soup' and o['is_ready'] for o in f112['objects'])
        ready_67  = any(o['name']=='soup' and o['is_ready'] for o in f67['objects'])
        has_soup_112 = any(o['name']=='soup' for o in f112['objects'])
        has_soup_67  = any(o['name']=='soup' for o in f67['objects'])

        # Anticipation
        if ready_112 and not prev_ready_112:
            ant_total_112 += 1
            p0h = f112['players'][0].get('held_object')
            p1h = f112['players'][1].get('held_object')
            if (p0h and p0h['name']=='dish') or (p1h and p1h['name']=='dish'):
                ant_112 += 1

        if ready_67 and not prev_ready_67:
            ant_total_67 += 1
            p0h = f67['players'][0].get('held_object')
            p1h = f67['players'][1].get('held_object')
            if (p0h and p0h['name']=='dish') or (p1h and p1h['name']=='dish'):
                ant_67 += 1

        prev_ready_112 = ready_112
        prev_ready_67  = ready_67

        # Soup wait
        if ready_112:
            wait_112 += 1
        else:
            if wait_112 > 0: wait_counts_112.append(wait_112)
            wait_112 = 0

        if ready_67:
            wait_67 += 1
        else:
            if wait_67 > 0: wait_counts_67.append(wait_67)
            wait_67 = 0

        # Pot empty
        if not has_soup_112:
            pot_empty_112 += 1
        else:
            if pot_empty_112 > 0: empty_counts_112.append(pot_empty_112)
            pot_empty_112 = 0

        if not has_soup_67:
            pot_empty_67 += 1
        else:
            if pot_empty_67 > 0: empty_counts_67.append(pot_empty_67)
            pot_empty_67 = 0

        avg_w112 = sum(wait_counts_112)/len(wait_counts_112) if wait_counts_112 else 0
        avg_w67  = sum(wait_counts_67)/len(wait_counts_67)   if wait_counts_67  else 0
        avg_e112 = sum(empty_counts_112)/len(empty_counts_112) if empty_counts_112 else 0
        avg_e67  = sum(empty_counts_67)/len(empty_counts_67)   if empty_counts_67  else 0
        ant_pct_112 = 100*ant_112/max(ant_total_112, 1)
        ant_pct_67  = 100*ant_67/max(ant_total_67, 1)

        # Controls hint
        hint = font_xs.render(
            'SPACE = play/pause    R = reset    LEFT/RIGHT = step 10 frames    ESC = quit',
            True, (120, 130, 160))
        screen.blit(hint, (10, 6))

        ox_112 = 10
        ox_67  = grid_w + GAP + 10
        oy = 72

        # Labels
        lbl112 = font_lg.render('Trial 112 — HIGH FLUENCY', True, (29, 158, 117))
        screen.blit(lbl112, (ox_112, oy - 30))
        lbl67 = font_lg.render('Trial 67 — LOW FLUENCY', True, (226, 75, 74))
        screen.blit(lbl67, (ox_67, oy - 30))

        # Grids, objects, players
        draw_grid(screen, layout, ox_112, oy, font_sm)
        draw_grid(screen, layout, ox_67,  oy, font_sm)
        draw_objects(screen, f112['objects'], ox_112, oy, font_sm)
        draw_objects(screen, f67['objects'],  ox_67,  oy, font_sm)
        draw_players(screen, f112['players'], ox_112, oy, font)
        draw_players(screen, f67['players'],  ox_67,  oy, font)

        # Stats
        sy = oy + grid_h + 10

        # Trial 112
        sc112 = font.render(f"Score: {int(f112['score'])}   Deliveries: {trial_112['deliveries']}", True, (29, 158, 117))
        screen.blit(sc112, (ox_112, sy))
        sw112 = font.render(f"Avg soup wait: {avg_w112:.1f} steps  |  Avg pot empty: {avg_e112:.1f}", True, (180, 220, 180))
        screen.blit(sw112, (ox_112, sy + 22))
        at112 = font.render(f"Anticipation: {ant_pct_112:.0f}%  ({ant_112}/{ant_total_112} events)", True, (100, 200, 150))
        screen.blit(at112, (ox_112, sy + 44))
        if f112['reward'] > 0:
            dl = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl, (ox_112, sy + 66))
        elif wait_112 > 0:
            wt = font.render(f'Soup waiting: {wait_112} steps', True, (241, 196, 15))
            screen.blit(wt, (ox_112, sy + 66))
        if ready_112 and wait_112 <= 3:
            flash = font_lg.render('ANTICIPATED!', True, (100, 255, 180))
            screen.blit(flash, (ox_112, sy + 88))

        # Trial 67
        sc67 = font.render(f"Score: {int(f67['score'])}   Deliveries: {trial_67['deliveries']}", True, (226, 75, 74))
        screen.blit(sc67, (ox_67, sy))
        sw67 = font.render(f"Avg soup wait: {avg_w67:.1f} steps  |  Avg pot empty: {avg_e67:.1f}", True, (220, 160, 160))
        screen.blit(sw67, (ox_67, sy + 22))
        at67 = font.render(f"Anticipation: {ant_pct_67:.0f}%  ({ant_67}/{ant_total_67} events)", True, (220, 120, 80))
        screen.blit(at67, (ox_67, sy + 44))
        if f67['reward'] > 0:
            dl2 = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl2, (ox_67, sy + 66))
        elif wait_67 > 0:
            wt2 = font.render(f'Soup waiting: {wait_67} steps', True, (231, 76, 60))
            screen.blit(wt2, (ox_67, sy + 66))
        if ready_67 and not prev_ready_67:
            flash2 = font_lg.render('NOT ANTICIPATED', True, (255, 120, 80))
            screen.blit(flash2, (ox_67, sy + 88))

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
