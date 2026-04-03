import json
import os
import pygame

script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'random3_trials_v2.json')

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

    trial_78 = data['78']
    trial_88 = data['88']
    layout = trial_78['layout']

    rows_g = len(layout)
    cols_g = len(layout[0])
    grid_w = cols_g * TILE
    grid_h = rows_g * TILE

    GAP = 40
    WIN_W = grid_w * 2 + GAP + 20
    WIN_H = grid_h + 160

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Random3 — Trial 78 (High Fluency) vs Trial 88 (Low Fluency)')

    font = pygame.font.SysFont('Arial', 15, bold=True)
    font_sm = pygame.font.SysFont('Arial', 11, bold=True)
    font_lg = pygame.font.SysFont('Arial', 17, bold=True)
    font_xs = pygame.font.SysFont('Arial', 11)

    clock = pygame.time.Clock()
    frame_idx = 0
    playing = False
    total_frames = min(len(trial_78['frames']), len(trial_88['frames']))

    # Track soup wait in real time
    wait_78 = wait_88 = 0
    wait_counts_78 = []
    wait_counts_88 = []

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
                    wait_78 = wait_88 = 0
                    wait_counts_78.clear()
                    wait_counts_88.clear()
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

        f78 = trial_78['frames'][frame_idx]
        f88 = trial_88['frames'][frame_idx]

        # Track live soup wait
        if any(o['name'] == 'soup' and o['is_ready'] for o in f78['objects']):
            wait_78 += 1
        else:
            if wait_78 > 0:
                wait_counts_78.append(wait_78)
            wait_78 = 0

        if any(o['name'] == 'soup' and o['is_ready'] for o in f88['objects']):
            wait_88 += 1
        else:
            if wait_88 > 0:
                wait_counts_88.append(wait_88)
            wait_88 = 0

        avg_w78 = sum(wait_counts_78)/len(wait_counts_78) if wait_counts_78 else 0
        avg_w88 = sum(wait_counts_88)/len(wait_counts_88) if wait_counts_88 else 0

        # Controls hint
        hint = font_xs.render(
            'SPACE = play/pause    R = reset    LEFT/RIGHT = step 10 frames    ESC = quit',
            True, (120, 130, 160))
        screen.blit(hint, (10, 6))

        ox_78 = 10
        ox_88 = grid_w + GAP + 10
        oy = 70

        # Left label
        lbl78 = font_lg.render('Trial 78 — HIGH FLUENCY', True, (29, 158, 117))
        screen.blit(lbl78, (ox_78, oy - 28))

        # Right label
        lbl88 = font_lg.render('Trial 88 — LOW FLUENCY', True, (226, 75, 74))
        screen.blit(lbl88, (ox_88, oy - 28))

        # Draw grids
        draw_grid(screen, layout, ox_78, oy, font_sm)
        draw_grid(screen, layout, ox_88, oy, font_sm)

        # Draw objects
        draw_objects(screen, f78['objects'], ox_78, oy, font_sm)
        draw_objects(screen, f88['objects'], ox_88, oy, font_sm)

        # Draw players
        draw_players(screen, f78['players'], ox_78, oy, font)
        draw_players(screen, f88['players'], ox_88, oy, font)

        # Stats below each grid
        sy = oy + grid_h + 8

        # Trial 78 stats
        sc78 = font.render(f"Score: {int(f78['score'])}   Deliveries: {trial_78['deliveries']}", True, (29, 158, 117))
        screen.blit(sc78, (ox_78, sy))
        sw78 = font.render(f"Avg soup wait: {avg_w78:.1f} steps", True, (200, 200, 200))
        screen.blit(sw78, (ox_78, sy + 22))
        if f78['reward'] > 0:
            dl = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl, (ox_78, sy + 44))
        if wait_78 > 0:
            wt = font.render(f'Soup waiting: {wait_78} steps', True, (241, 196, 15))
            screen.blit(wt, (ox_78, sy + 44))

        # Trial 88 stats
        sc88 = font.render(f"Score: {int(f88['score'])}   Deliveries: {trial_88['deliveries']}", True, (226, 75, 74))
        screen.blit(sc88, (ox_88, sy))
        sw88 = font.render(f"Avg soup wait: {avg_w88:.1f} steps", True, (200, 200, 200))
        screen.blit(sw88, (ox_88, sy + 22))
        if f88['reward'] > 0:
            dl2 = font_lg.render('*** DELIVERY! +5 ***', True, (241, 196, 15))
            screen.blit(dl2, (ox_88, sy + 44))
        if wait_88 > 0:
            wt2 = font.render(f'Soup waiting: {wait_88} steps', True, (231, 76, 60))
            screen.blit(wt2, (ox_88, sy + 44))

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
        lx = WIN_W // 2 - 220
        for color, label in legend:
            pygame.draw.rect(screen, color, (lx, 30, 12, 12), border_radius=2)
            lt = font_xs.render(label, True, (160, 170, 200))
            screen.blit(lt, (lx + 16, 29))
            lx += lt.get_width() + 30

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
