import json
import time
import os

# Try to import pygame
try:
    import pygame
except ImportError:
    print("Installing pygame...")
    os.system("py -m pip install pygame")
    import pygame

# Load trial data
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'random3_trials.json')

with open(data_path) as f:
    data = json.load(f)

# Layout legend
TILE_KEY = {
    'X': {'color': (92, 64, 51),  'label': 'Wall'},
    ' ': {'color': (44, 62, 80),  'label': 'Floor'},
    'O': {'color': (230, 126, 34),'label': 'Onions'},
    'D': {'color': (149, 165, 166),'label': 'Dishes'},
    'S': {'color': (231, 76, 60), 'label': 'Serve'},
    'P': {'color': (155, 89, 182),'label': 'Pot'},
    '1': {'color': (44, 62, 80),  'label': 'P1 start'},
    '2': {'color': (44, 62, 80),  'label': 'P0 start'},
}

PLAYER_COLORS = [(52, 152, 219), (46, 204, 113)]
HELD_EMOJI = {'onion': 'O', 'dish': 'D', 'soup': 'S', 'tomato': 'T'}

TILE = 60
PANEL_W = 260
FPS = 15

def draw_grid(surface, layout, offset_x, offset_y):
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            color = TILE_KEY.get(ch, {}).get('color', (44, 62, 80))
            rect = pygame.Rect(offset_x + c*TILE, offset_y + r*TILE, TILE-1, TILE-1)
            pygame.draw.rect(surface, color, rect, border_radius=4)
            # Labels for key tiles
            if ch in ('O', 'D', 'S', 'P'):
                label = {'O':'ONI','D':'DSH','S':'SRV','P':'POT'}[ch]
                font_sm = pygame.font.SysFont('Arial', 11, bold=True)
                txt = font_sm.render(label, True, (255,255,255))
                surface.blit(txt, (offset_x + c*TILE + 4, offset_y + r*TILE + 4))

def draw_objects(surface, objects, offset_x, offset_y):
    for obj in objects:
        if obj['name'] == 'soup':
            cx = offset_x + obj['position'][0]*TILE + TILE//2
            cy = offset_y + obj['position'][1]*TILE + TILE//2
            if obj['is_ready']:
                pygame.draw.circle(surface, (241, 196, 15), (cx, cy), TILE//3)
                font = pygame.font.SysFont('Arial', 14, bold=True)
                txt = font.render('RDY', True, (0,0,0))
                surface.blit(txt, (cx - txt.get_width()//2, cy - txt.get_height()//2))
            elif obj['is_cooking']:
                pct = min(1.0, obj.get('_cooking_tick', 0) / max(obj.get('cook_time', 20), 1))
                color = (int(230*pct), int(126*(1-pct)+50*pct), 34)
                pygame.draw.circle(surface, color, (cx, cy), TILE//3)
                font = pygame.font.SysFont('Arial', 12)
                tick = obj.get('_cooking_tick', 0)
                txt = font.render(str(int(tick)), True, (255,255,255))
                surface.blit(txt, (cx - txt.get_width()//2, cy - txt.get_height()//2))
            else:
                pygame.draw.circle(surface, (155, 89, 182), (cx, cy), TILE//4)
        elif obj['name'] == 'onion':
            cx = offset_x + obj['position'][0]*TILE + TILE//2
            cy = offset_y + obj['position'][1]*TILE + TILE//2
            pygame.draw.circle(surface, (230, 126, 34), (cx, cy), TILE//5)
        elif obj['name'] == 'dish':
            cx = offset_x + obj['position'][0]*TILE + TILE//2
            cy = offset_y + obj['position'][1]*TILE + TILE//2
            pygame.draw.circle(surface, (200, 200, 200), (cx, cy), TILE//5)

def draw_players(surface, players, offset_x, offset_y, font):
    for i, player in enumerate(players):
        px = offset_x + player['position'][0]*TILE + TILE//2
        py = offset_y + player['position'][1]*TILE + TILE//2
        # Shadow
        pygame.draw.ellipse(surface, (0,0,0,80),
            (px-TILE//3, py+TILE//4, TILE*2//3, TILE//6))
        # Body
        pygame.draw.circle(surface, PLAYER_COLORS[i], (px, py), TILE//2 - 4)
        pygame.draw.circle(surface, (255,255,255), (px, py), TILE//2 - 4, 2)
        # Label
        label = f'P{i}'
        txt = font.render(label, True, (255,255,255))
        surface.blit(txt, (px - txt.get_width()//2, py - txt.get_height()//2))
        # Held object indicator
        held = player.get('held_object')
        if held:
            held_name = held['name'] if isinstance(held, dict) else str(held)
            held_char = HELD_EMOJI.get(held_name, '?')
            held_colors = {'onion':(230,126,34),'dish':(200,200,200),
                          'soup':(241,196,15),'tomato':(231,76,60)}
            hcolor = held_colors.get(held_name, (255,255,255))
            pygame.draw.circle(surface, hcolor,
                (px + TILE//2 - 4, py - TILE//2 + 4), 10)
            sm = pygame.font.SysFont('Arial', 10, bold=True)
            ht = sm.render(held_char[0], True, (0,0,0))
            surface.blit(ht, (px + TILE//2 - 4 - ht.get_width()//2,
                              py - TILE//2 + 4 - ht.get_height()//2))

def draw_panel(surface, trial_id, frame, frame_idx, total_frames,
               fluency_label, fluency_color, x, y, w, h, font, font_sm):
    # Panel background
    pygame.draw.rect(surface, (22, 33, 62), (x, y, w, h), border_radius=8)
    pygame.draw.rect(surface, (50, 60, 90), (x, y, w, h), 1, border_radius=8)

    # Trial label
    title = font.render(f'Trial {trial_id}', True, (255,255,255))
    surface.blit(title, (x+10, y+10))

    # Fluency badge
    badge_w = 120
    pygame.draw.rect(surface, fluency_color,
        (x+w-badge_w-10, y+8, badge_w, 24), border_radius=4)
    bl = font_sm.render(fluency_label, True, (0,0,0))
    surface.blit(bl, (x+w-badge_w-10 + badge_w//2 - bl.get_width()//2, y+12))

    # Stats
    score_txt = font.render(f"Score: {int(frame['score'])}", True, (255,215,0))
    surface.blit(score_txt, (x+10, y+40))

    # Delivery flash
    if frame['reward'] > 0:
        flash = font.render('DELIVERY! +5', True, (241,196,15))
        surface.blit(flash, (x+10, y+65))

    # Progress bar
    bar_y = y + h - 20
    bar_w = w - 20
    pygame.draw.rect(surface, (50,60,90), (x+10, bar_y, bar_w, 8), border_radius=4)
    prog = int(bar_w * frame_idx / max(total_frames-1, 1))
    pygame.draw.rect(surface, (52,152,219), (x+10, bar_y, prog, 8), border_radius=4)
    prog_txt = font_sm.render(f'Step {frame_idx+1}/{total_frames}', True, (150,150,180))
    surface.blit(prog_txt, (x+10, bar_y - 18))

def main():
    pygame.init()

    trial_73 = data['73']
    trial_88 = data['88']
    layout = trial_73['layout']

    rows = len(layout)
    cols = len(layout[0])

    grid_w = cols * TILE
    grid_h = rows * TILE
    panel_h = 100

    # Two kitchens side by side
    WIN_W = grid_w * 2 + PANEL_W * 0 + 60
    WIN_H = grid_h + panel_h + 120

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption('Overcooked Fluency Viewer — Random3 Layout')

    font = pygame.font.SysFont('Arial', 16, bold=True)
    font_sm = pygame.font.SysFont('Arial', 12)
    font_lg = pygame.font.SysFont('Arial', 20, bold=True)
    font_title = pygame.font.SysFont('Arial', 18, bold=True)

    clock = pygame.time.Clock()
    frame_idx = 0
    playing = False
    total_frames = min(len(trial_73['frames']), len(trial_88['frames']))

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
                elif event.key == pygame.K_RIGHT:
                    frame_idx = min(frame_idx + 5, total_frames - 1)
                elif event.key == pygame.K_LEFT:
                    frame_idx = max(frame_idx - 5, 0)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

        if playing:
            frame_idx += 1
            if frame_idx >= total_frames:
                frame_idx = total_frames - 1
                playing = False

        screen.fill((15, 20, 40))

        # Title bar
        title = font_lg.render(
            'Random3 Layout — Fluency Comparison  |  SPACE=play/pause  R=reset  ←→=step',
            True, (200, 210, 230))
        screen.blit(title, (10, 8))

        # Draw Trial 73 (High Fluency) — LEFT
        offset_73_x = 10
        offset_73_y = 80

        label_73 = font_title.render('Trial 73 — HIGH FLUENCY', True, (29, 158, 117))
        screen.blit(label_73, (offset_73_x, offset_73_y - 28))

        frame_73 = trial_73['frames'][frame_idx]
        draw_grid(screen, layout, offset_73_x, offset_73_y)
        draw_objects(screen, frame_73['objects'], offset_73_x, offset_73_y)
        draw_players(screen, frame_73['players'], offset_73_x, offset_73_y, font)

        # Stats panel 73
        py = offset_73_y + grid_h + 8
        score_t = font.render(f"Score: {int(frame_73['score'])}  |  Fluency score: 22.0", True, (29,158,117))
        screen.blit(score_t, (offset_73_x, py))
        if frame_73['reward'] > 0:
            deli = font.render('*** DELIVERY! ***', True, (241,196,15))
            screen.blit(deli, (offset_73_x, py+24))

        # Draw Trial 88 (Low Fluency) — RIGHT
        offset_88_x = grid_w + 40
        offset_88_y = 80

        label_88 = font_title.render('Trial 88 — LOW FLUENCY', True, (226, 75, 74))
        screen.blit(label_88, (offset_88_x, offset_88_y - 28))

        frame_88 = trial_88['frames'][frame_idx]
        draw_grid(screen, layout, offset_88_x, offset_88_y)
        draw_objects(screen, frame_88['objects'], offset_88_x, offset_88_y)
        draw_players(screen, frame_88['players'], offset_88_x, offset_88_y, font)

        # Stats panel 88
        score_t2 = font.render(f"Score: {int(frame_88['score'])}  |  Fluency score: 2.1", True, (226,75,74))
        screen.blit(score_t2, (offset_88_x, py))
        if frame_88['reward'] > 0:
            deli2 = font.render('*** DELIVERY! ***', True, (241,196,15))
            screen.blit(deli2, (offset_88_x, py+24))

        # Progress bar at bottom
        bar_y = WIN_H - 30
        bar_w = WIN_W - 20
        pygame.draw.rect(screen, (40,50,80), (10, bar_y, bar_w, 10), border_radius=5)
        prog = int(bar_w * frame_idx / max(total_frames-1, 1))
        pygame.draw.rect(screen, (52,152,219), (10, bar_y, prog, 10), border_radius=5)
        step_txt = font_sm.render(
            f'Timestep {frame_idx+1} / {total_frames}   (6 soups delivered vs 12 soups — but Trial 73 is MORE fluent)',
            True, (150,160,200))
        screen.blit(step_txt, (10, bar_y - 20))

        # Legend
        legend_items = [
            ((155,89,182), 'Pot (P)'),
            ((230,126,34), 'Onions (O)'),
            ((149,165,166), 'Dishes (D)'),
            ((231,76,60), 'Serve (S)'),
            ((241,196,15), 'Soup ready'),
            ((52,152,219), 'Player 0'),
            ((46,204,113), 'Player 1'),
        ]
        lx = 10
        for color, label in legend_items:
            pygame.draw.rect(screen, color, (lx, WIN_H-58, 14, 14), border_radius=2)
            lt = font_sm.render(label, True, (180,190,210))
            screen.blit(lt, (lx+18, WIN_H-58))
            lx += lt.get_width() + 34

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == '__main__':
    main()
