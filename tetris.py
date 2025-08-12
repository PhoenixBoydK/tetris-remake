import pygame
import random
import os
import json
import traceback

# --- CONFIG ---
CELL_SIZE = 30
COLS = 10
VISIBLE_ROWS = 20      # rows visible in the game window
HIDDEN_ROWS = 4        # hidden buffer above the visible area (common in Tetris)
TOTAL_ROWS = VISIBLE_ROWS + HIDDEN_ROWS

WIDTH = CELL_SIZE * COLS
HEIGHT = CELL_SIZE * VISIBLE_ROWS  # screen height uses only visible rows

NEXT_AREA_WIDTH = 150  # extra width for next piece display

FPS = 60
FALL_EVENT = pygame.USEREVENT + 1

# Save stats file (JSON) path in same folder as script
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tetris_stats.json")

# Colors (R, G, B)
COLORS = [
    (0, 0, 0),        # 0 - Empty
    (0, 255, 255),    # 1 - I - cyan
    (0, 0, 255),      # 2 - J - blue
    (255, 165, 0),    # 3 - L - orange
    (255, 255, 0),    # 4 - O - yellow
    (0, 255, 0),      # 5 - S - green
    (128, 0, 128),    # 6 - T - purple
    (255, 0, 0),      # 7 - Z - red
]

# Tetromino shapes (as integer codes to index COLORS)
SHAPES = {
    'I': [[0,0,0,0],
          [1,1,1,1],
          [0,0,0,0],
          [0,0,0,0]],
    'J': [[2,0,0],
          [2,2,2],
          [0,0,0]],
    'L': [[0,0,3],
          [3,3,3],
          [0,0,0]],
    'O': [[4,4],
          [4,4]],
    'S': [[0,5,5],
          [5,5,0],
          [0,0,0]],
    'T': [[0,6,0],
          [6,6,6],
          [0,0,0]],
    'Z': [[7,7,0],
          [0,7,7],
          [0,0,0]],
}

# ----------------- Utilities -----------------
def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]

def new_board():
    """Create an empty board with TOTAL_ROWS rows (hidden + visible)."""
    return [[0 for _ in range(COLS)] for _ in range(TOTAL_ROWS)]

def collide(board, shape, offset):
    """Return True if shape placed at offset collides with walls/floor or existing blocks."""
    off_x, off_y = offset
    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                bx = off_x + x
                by = off_y + y
                # horizontal out of bounds
                if bx < 0 or bx >= COLS:
                    return True
                # below bottom
                if by >= TOTAL_ROWS:
                    return True
                # if inside stored board and cell occupied -> collision
                if by >= 0 and board[by][bx]:
                    return True
    return False

def merge(shape, board, offset):
    """Write shape into board at offset. Only writes cells with by >= 0."""
    off_x, off_y = offset
    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                by = off_y + y
                bx = off_x + x
                if 0 <= by < TOTAL_ROWS and 0 <= bx < COLS:
                    board[by][bx] = cell

def clear_lines(board):
    """Clear any completely filled rows across TOTAL_ROWS.
       Returns (new_board, cleared_count)."""
    new_rows = [row for row in board if any(cell == 0 for cell in row)]
    cleared = TOTAL_ROWS - len(new_rows)
    for _ in range(cleared):
        new_rows.insert(0, [0]*COLS)
    return new_rows, cleared

def draw_text(surface, text, size, pos, color=(255,255,255)):
    font = pygame.font.SysFont("consolas", size)
    surf = font.render(text, True, color)
    surface.blit(surf, pos)

# ----------------- Stats -----------------
def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                high_level = int(data.get("high_level", 0))
                high_lines = int(data.get("high_lines", 0))
                print(f"[LOAD] Loaded stats from {STATS_FILE}: level={high_level}, lines={high_lines}")
                return high_level, high_lines
        except Exception:
            print("[LOAD] Error reading stats file, starting fresh.")
            traceback.print_exc()
    else:
        print(f"[LOAD] No stats file at {STATS_FILE}. Starting fresh.")
    return 0, 0

def save_stats(high_level, high_lines):
    try:
        data = {"high_level": int(high_level), "high_lines": int(high_lines)}
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[SAVE] Stats saved to {STATS_FILE}: {data}")
    except Exception:
        print("[SAVE] Error saving stats!")
        traceback.print_exc()

# ----------------- Game -----------------
class Tetris:
    def __init__(self, surface):
        self.surface = surface
        self.board = new_board()
        self.score = 0
        self.level = 1
        self.lines = 0
        self.high_level, self.high_lines = load_stats()
        self.game_over = False
        self.paused = False
        # initialize next piece first
        self.next_type = random.choice(list(SHAPES.keys()))
        self.spawn_new()

    def find_spawn_x_order(self, shape_width):
        center = (COLS - shape_width) // 2
        order = [center]
        for i in range(1, COLS):
            left = center - i
            right = center + i
            if left >= 0:
                order.append(left)
            if right <= COLS - shape_width and right != left:
                order.append(right)
        return [x for x in order if 0 <= x <= COLS - shape_width]

    def spawn_new(self):
        self.current_type = self.next_type
        self.current_shape = [row[:] for row in SHAPES[self.current_type]]
        self.next_type = random.choice(list(SHAPES.keys()))

        shape_h = len(self.current_shape)
        shape_w = len(self.current_shape[0])
        spawn_y = HIDDEN_ROWS - shape_h
        if spawn_y < 0:
            spawn_y = 0

        spawn_x_candidates = self.find_spawn_x_order(shape_w)
        for spawn_x in spawn_x_candidates:
            if not collide(self.board, self.current_shape, (spawn_x, spawn_y)):
                self.x = spawn_x
                self.y = spawn_y
                print(f"[SPAWN] Piece {self.current_type} at ({self.x},{self.y})")
                return

        print("[SPAWN] No valid spawn position found -> Game Over")
        self.game_over = True
        changed = False
        if self.level > self.high_level:
            self.high_level = self.level
            changed = True
        if self.lines > self.high_lines:
            self.high_lines = self.lines
            changed = True
        if changed:
            save_stats(self.high_level, self.high_lines)

    def rotate_piece(self):
        new_shape = rotate(self.current_shape)
        if not collide(self.board, new_shape, (self.x, self.y)):
            self.current_shape = new_shape

    def move(self, dx):
        if not collide(self.board, self.current_shape, (self.x + dx, self.y)):
            self.x += dx

    def soft_drop(self):
        if not collide(self.board, self.current_shape, (self.x, self.y + 1)):
            self.y += 1
            return True
        else:
            self.lock_piece()
            return False

    def hard_drop(self):
        while not collide(self.board, self.current_shape, (self.x, self.y + 1)):
            self.y += 1
        self.lock_piece()

    def lock_piece(self):
        merge(self.current_shape, self.board, (self.x, self.y))
        self.board, cleared = clear_lines(self.board)
        if cleared:
            self.lines += cleared
            self.score += (100 * cleared) * self.level
            old_level = self.level
            self.level = 1 + self.lines // 10
            changed = False
            if self.lines > self.high_lines:
                self.high_lines = self.lines
                changed = True
            if self.level > self.high_level:
                self.high_level = self.level
                changed = True
            if changed:
                save_stats(self.high_level, self.high_lines)
        self.spawn_new()

    def update(self):
        if self.game_over or self.paused:
            return
        self.soft_drop()

    def draw(self):
        self.surface.fill((10,10,20))
        # Draw board (only visible rows)
        for r in range(HIDDEN_ROWS, TOTAL_ROWS):
            screen_row = r - HIDDEN_ROWS
            for c in range(COLS):
                val = self.board[r][c]
                rect = pygame.Rect(c*CELL_SIZE, screen_row*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.surface, (30,30,40), rect, 1)
                if val:
                    pygame.draw.rect(self.surface, COLORS[val], rect.inflate(-2, -2))
        # Draw current piece in visible area
        for r, row in enumerate(self.current_shape):
            for c, val in enumerate(row):
                if val:
                    bx = self.x + c
                    by = self.y + r
                    if by >= HIDDEN_ROWS and by < TOTAL_ROWS:
                        screen_row = by - HIDDEN_ROWS
                        rect = pygame.Rect(bx*CELL_SIZE, screen_row*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                        pygame.draw.rect(self.surface, COLORS[val], rect.inflate(-2, -2))
        # Draw HUD
        draw_text(self.surface, f"Score: {self.score}", 20, (10, 10))
        draw_text(self.surface, f"Level: {self.level}", 20, (10, 30))
        draw_text(self.surface, f"Lines: {self.lines}", 20, (10, 50))
        draw_text(self.surface, f"High Level: {self.high_level}", 20, (10, 80))
        draw_text(self.surface, f"High Lines: {self.high_lines}", 20, (10, 100))

        # Draw Next piece label
        draw_text(self.surface, "Next:", 20, (WIDTH + 10, 10))
        # Draw next piece preview
        start_x = WIDTH + 10
        start_y = 40
        next_shape = SHAPES[self.next_type]
        for r, row in enumerate(next_shape):
            for c, val in enumerate(row):
                if val:
                    rect = pygame.Rect(start_x + c * CELL_SIZE, start_y + r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(self.surface, COLORS[val], rect.inflate(-2, -2))
                    pygame.draw.rect(self.surface, (255, 255, 255), rect, 1)  # outline

        if self.paused:
            draw_text(self.surface, "PAUSED", 40, (WIDTH//2 - 60, HEIGHT//2 - 20), (255,255,0))
        if self.game_over:
            draw_text(self.surface, "GAME OVER", 40, (WIDTH//2 - 100, HEIGHT//2 - 20), (255,0,0))

    def debug_print_board(self):
        print("==== board (top = hidden rows) ====")
        for r in range(TOTAL_ROWS):
            prefix = "H" if r < HIDDEN_ROWS else "V"
            print(f"{prefix}{r:02d} " + "".join(str(x) for x in self.board[r]))
        print("==================================")

# ----------------- Main -----------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH + NEXT_AREA_WIDTH, HEIGHT))
    pygame.display.set_caption("Tetris (Python / Pygame)")
    clock = pygame.time.Clock()

    print("Tetris starting. Stats path:", STATS_FILE)
    game = Tetris(screen)

    fall_speed = max(1000 - (game.level - 1) * 60, 100)
    pygame.time.set_timer(FALL_EVENT, fall_speed)

    running = True
    try:
        while running:
            dt = clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == FALL_EVENT:
                    if not game.paused and not game.game_over:
                        game.update()
                        new_speed = max(1000 - (game.level - 1) * 60, 100)
                        if new_speed != fall_speed:
                            fall_speed = new_speed
                            pygame.time.set_timer(FALL_EVENT, fall_speed)
                elif event.type == pygame.KEYDOWN:
                    # Debug / helper keys:
                    if event.key == pygame.K_d:   # D = dump board to console
                        game.debug_print_board()
                    elif event.key == pygame.K_s: # S = force-save stats
                        save_stats(game.high_level, game.high_lines); print("[MANUAL SAVE] done")
                    elif event.key == pygame.K_r: # R = reset board (keep highs)
                        game.board = new_board(); game.score = 0; game.level = 1; game.lines = 0; game.game_over=False; game.spawn_new(); print("[RESET] board reset")
                    # Normal keys:
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_p:
                        game.paused = not game.paused
                    elif not game.game_over and not game.paused:
                        if event.key == pygame.K_LEFT:
                            game.move(-1)
                        elif event.key == pygame.K_RIGHT:
                            game.move(1)
                        elif event.key == pygame.K_UP:
                            game.rotate_piece()
                        elif event.key == pygame.K_DOWN:
                            game.soft_drop()
                        elif event.key == pygame.K_SPACE:
                            game.hard_drop()

            game.draw()
            pygame.display.flip()
    finally:
        save_stats(game.high_level, game.high_lines)
        pygame.quit()

if __name__ == "__main__":
    main()
