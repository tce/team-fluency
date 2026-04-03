import json
import os
import pygame

script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'cramped_room_trials.json')

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

    trial_10 = data['10']
    trial_80 = data['80']
    layout = trial_10['layout']

    rows_g = len(layout)
    cols_g = len(layout[0])
    grid_w = cols_g * TILE
    grid_h = rows_g * TILE

    GAP = 60
    WIN_W = grid_w * 2 + GAP + 20
    WIN_H = grid_h + 180

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Cramped Room — Trial 10 (High Fluency) vs Trial 80 (Low Fluency)')

    font = pygame.font.SysFont('Arial', 15, bold=True)
    font_sm = pygame.font.SysFont('Arial', 12, bold=True)
    font_lg = pygame.font.SysFont('Arial', 17, bold=True)
    font_xs = pygame.font.SysFont('Arial', 11)

    clock = pygame.time.Clock()
    frame_idx = 0
    playing = False
    total_frames = min(len(trial_10['frames']), len(trial_80['frames']))

    # Live tracking
    wait_10 = wait_80 = 0
    wait_counts_10 = []
    wait_counts_80 = []
    pot_empty_10 = pot_empty_80 = 0
    empty_counts_10 = []
    empty_counts_80 = []
    prev_has_soup_10 = True
    prev_has_soup_80 = True

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
                    wait_10 = wait_80 = 0
                    wait_counts_10.clear()
                    wait_counts_80.clear()
                    pot_empty_10 = pot_empty_80 = 0
                    empty_counts_10.clear()
                    empty_counts_80.clear()
                    prev_has_soup_10 = True
                    prev_has_soup_80 = True
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

        f10 = trial_10['frames'][frame_idx]
        f80 = trial_80['frames'][frame_idx]

        # Live soup wait tracking
        has_soup_ready_10 = any(o['name']=='soup' and o['is_ready'] for o in f10['objects'])
        has_soup_ready_80 = any(o['name']=='soup' and o['is_ready'] for o in f80['objects'])
        has_soup_10 = any(o['name']=='soup' for o in f10['objects'])
        has_soup_80 = any(o['name']=='soup' for o in f80['objects'])

        if has_soup_ready_10:
            wait_10 += 1
        else:
            if wait_10 > 0:
                wait_counts_10.append(wait_10)
            wait_10 = 0

        if has_soup_ready_80:
            wait_80 += 1
        else:
            if wait_80 > 0:
                wait_counts_80.append(wait_80)
            wait_80 = 0

        # Live pot empty tracking
        if not has_soup_10:
            pot_empty_10 += 1
        else:
            if pot_empty_10 > 0:
                empty_counts_10.append(pot_empty_10)
            pot_empty_10 = 0

        if not has_soup_80:
            pot_empty_80 += 1
        else:
            if pot_empty_80 > 0:
                empty_counts_80.append(pot_empty_80)
            pot_empty_80 = 0

        avg_w10 = sum(wait_counts_10)/len(wait_counts_10) if wait_counts_10 else 0
        avg_w80 = sum(wait_counts_80)/len(wait_counts_80) if wait_counts_80 else 0
        avg_e10 = sum(empty_counts_10)/len(empty_counts_10) if empty_counts_10 else 0
        avg_e80 = sum(empty_counts_80)/len(empty_counts_80) if empty_counts_80 else 0

        # Controls hint
        hint = font_xs.render(
            'SPACE = play/pause    R = reset    LEFT/RIGHT = step 10 frames    ESC = quit',
            True, (120, 130, 160))
        screen.blit(hint, (10, 6))

        ox_10 = 10
        ox_80 = grid_w + GAP + 10
        oy = 72

        # Labels
        lbl10 = font_lg.render('Trial 10 — HIGH FLUENCY', True, (29, 158, 117))
        screen.blit(lbl10, (ox_10, oy - 30))
        lbl80 = font_lg.render('Trial 80 — LOW FLUENCY', True, (226, 75, 74))
        screen.blit(lbl80, (ox_80, oy - 30))

        # Grids
        draw_grid(screen, layout, ox_10, oy, font_sm)
        draw_grid(screen, layout, ox_80, oy, font_sm)

        # Objects
        draw_objects(screen, f10['objects'], ox_10, oy, font_sm)
        draw_objects(screen, f80['objects'], ox_80, oy, font_sm)

        # Players
        draw_players(screen, f10['players'], ox_10, oy, font)
        draw_players(screen, f80['players'], ox_80, oy, font)

        # Stats panel
        sy = oy + grid_h + 10

        # Trial 10 stats
        sc10 = font.render(f"Score: {int(f10['score'])}   Deliveries: {trial_10['deliveries']}", True, (29, 158, 117))
        screen.blit(sc10, (ox_10, sy))
        sw10 = font.render(f"Avg soup wait: {avg_w10:.1f} steps  |  Avg pot empty: {avg_e10:.1f}", True, (180, 200, 180))
        screen.blit(sw10, (ox_10, sy + 22))
        ant10 = font_xs.render("Anticipation: 100% — P1 always ready with dish", True, (100, 200, 150))
        screen.blit(ant10, (ox_10, sy + 44))
        if f10['reward'] > 0:
            dl = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl, (ox_10, sy + 62))
        if wait_10 > 0:
            wt = font.render(f'Soup waiting: {wait_10} steps', True, (241, 196, 15))
            screen.blit(wt, (ox_10, sy + 62))
        if pot_empty_10 > 0:
            et = font_xs.render(f'Pot empty: {pot_empty_10} steps', True, (150, 150, 200))
            screen.blit(et, (ox_10, sy + 82))

        # Trial 80 stats
        sc80 = font.render(f"Score: {int(f80['score'])}   Deliveries: {trial_80['deliveries']}", True, (226, 75, 74))
        screen.blit(sc80, (ox_80, sy))
        sw80 = font.render(f"Avg soup wait: {avg_w80:.1f} steps  |  Avg pot empty: {avg_e80:.1f}", True, (220, 160, 160))
        screen.blit(sw80, (ox_80, sy + 22))
        ant80 = font_xs.render("Anticipation: 80% — sometimes reactive", True, (200, 150, 100))
        screen.blit(ant80, (ox_80, sy + 44))
        if f80['reward'] > 0:
            dl2 = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl2, (ox_80, sy + 62))
        if wait_80 > 0:
            wt2 = font.render(f'Soup waiting: {wait_80} steps', True, (231, 76, 60))
            screen.blit(wt2, (ox_80, sy + 62))
        if pot_empty_80 > 0:
            et2 = font_xs.render(f'Pot empty: {pot_empty_80} steps', True, (200, 100, 100))
            screen.blit(et2, (ox_80, sy + 82))

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
