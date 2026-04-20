"""
============================================================
  SUPERHOT DODGER v2 - 시간 멈춤 피하기 (업그레이드 버전)
  창의 프로그래밍 입문 설계 - 중간 프로젝트
============================================================
  핵심 메커니즘:
    - 가만히 있으면 시간이 멈춘다 (흑백 화면)
    - 움직이면 시간이 흐른다 (컬러 화면)
    - 에너지 소진 시 BURNOUT (시간 강제 흐름)

  v2 추가 요소:
    💎 크리스탈  - 에너지 풀충전 + 보너스 점수
    ❤️ 생명 하트  - 희귀 아이템, 생명 +1 (최대 5)
    👾 글리치 적  - 시간 멈춰도 1/4 속도로 움직임
    🎬 슬로우 모션 - 피격 시 연출
============================================================
"""

import pygame
import random
import sys
import math

pygame.init()

# ------------------------------------------------------------
# 한글 폰트
# ------------------------------------------------------------
def get_korean_font(size):
    candidates = ["malgungothic", "applegothic", "nanumgothic", "notosanscjk"]
    for name in candidates:
        font = pygame.font.SysFont(name, size)
        if font.get_ascent() > 0:
            return font
    return pygame.font.SysFont(None, size)

# ------------------------------------------------------------
# 상수
# ------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
FPS = 60

WHITE    = (255, 255, 255)
BLACK    = (0, 0, 0)
BG_COLOR = (20, 22, 30)
PLAYER_COLOR  = (80, 200, 255)
ENEMY_COLOR   = (255, 80, 80)
GLITCH_COLOR  = (180, 80, 255)
CRYSTAL_COLOR = (100, 200, 255)
HEART_COLOR   = (255, 100, 140)
GOLD     = (255, 215, 0)
GREEN    = (80, 220, 120)
PURPLE   = (180, 100, 255)
ORANGE   = (255, 140, 60)

PLAYER_W, PLAYER_H = 40, 40
ENEMY_W, ENEMY_H = 30, 30
PLAYER_SPEED = 5

# 시간 시스템
TIME_DECAY_RATE = 0.4
TIME_REGEN_RATE = 0.25
MAX_TIME_ENERGY = 100.0
BURNOUT_DURATION = 120

# v2 추가 상수
MAX_LIVES = 5
CRYSTAL_SPAWN_MIN = 600
CRYSTAL_SPAWN_MAX = 900
HEART_SPAWN_MIN = 1800
HEART_SPAWN_MAX = 3000
GLITCH_CHANCE_START = 40 * 60
GLITCH_SPAWN_RATE = 0.15
SLOWMO_DURATION = 40

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SUPERHOT DODGER v2")
clock = pygame.time.Clock()

font_tiny  = get_korean_font(18)
font_small = get_korean_font(24)
font       = get_korean_font(32)
font_big   = get_korean_font(56)
font_huge  = get_korean_font(80)

LEVELS = [
    {"min_speed": 3, "max_speed": 5,  "spawn": 45, "label": "Lv.1 BEGINNER"},
    {"min_speed": 4, "max_speed": 7,  "spawn": 32, "label": "Lv.2 WARRIOR"},
    {"min_speed": 6, "max_speed": 10, "spawn": 22, "label": "Lv.3 MASTER"},
    {"min_speed": 8, "max_speed": 14, "spawn": 15, "label": "Lv.4 LEGEND"},
]

# ============================================================
# 파티클
# ============================================================
class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=30, size=4):
        self.x = x
        self.y = y
        self.vx = vx if vx is not None else random.uniform(-3, 3)
        self.vy = vy if vy is not None else random.uniform(-3, 3)
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, time_flowing):
        if time_flowing:
            self.x += self.vx
            self.y += self.vy
            self.vy += 0.1
            self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            alpha = self.life / self.max_life
            size = max(1, int(self.size * alpha))
            c = (int(self.color[0] * alpha),
                 int(self.color[1] * alpha),
                 int(self.color[2] * alpha))
            pygame.draw.rect(surface, c,
                           (int(self.x), int(self.y), size, size))

particles = []

def spawn_particles(x, y, color, count=15, spread=4):
    for _ in range(count):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, spread)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        particles.append(Particle(x, y, color, vx, vy,
                                   life=random.randint(20, 40),
                                   size=random.randint(2, 5)))

# ============================================================
# 화면 흔들림
# ============================================================
shake_amount = 0

def add_shake(power):
    global shake_amount
    shake_amount = max(shake_amount, power)

def get_shake_offset():
    global shake_amount
    if shake_amount > 0:
        ox = random.randint(-int(shake_amount), int(shake_amount))
        oy = random.randint(-int(shake_amount), int(shake_amount))
        shake_amount *= 0.85
        if shake_amount < 0.5:
            shake_amount = 0
        return ox, oy
    return 0, 0

# ============================================================
# 배경 별
# ============================================================
stars = []
for _ in range(60):
    stars.append({
        "x": random.randint(0, WIDTH),
        "y": random.randint(0, HEIGHT),
        "speed": random.uniform(0.3, 1.5),
        "size": random.randint(1, 3)
    })

def update_and_draw_stars(surface, time_flowing):
    for s in stars:
        if time_flowing:
            s["y"] += s["speed"]
            if s["y"] > HEIGHT:
                s["y"] = 0
                s["x"] = random.randint(0, WIDTH)
        brightness = int(150 + s["speed"] * 50)
        if time_flowing:
            c = (brightness, brightness, brightness)
        else:
            c = (brightness // 2, brightness // 2, brightness // 2 + 20)
        pygame.draw.rect(surface, c,
                        (int(s["x"]), int(s["y"]), s["size"], s["size"]))

# ============================================================
# Enemy (일반 + 글리치)
# ============================================================
class Enemy:
    def __init__(self, level_cfg, is_glitch=False):
        self.is_glitch = is_glitch
        pattern = random.choice(["top", "top", "top", "side"])
        speed = random.uniform(level_cfg["min_speed"], level_cfg["max_speed"])

        if pattern == "top":
            x = random.randint(0, WIDTH - ENEMY_W)
            self.rect = pygame.Rect(x, -ENEMY_H, ENEMY_W, ENEMY_H)
            self.vx, self.vy = 0, speed
        else:
            side = random.choice(["left", "right"])
            y = random.randint(50, HEIGHT - 200)
            if side == "left":
                self.rect = pygame.Rect(-ENEMY_W, y, ENEMY_W, ENEMY_H)
                self.vx, self.vy = speed, 0
            else:
                self.rect = pygame.Rect(WIDTH, y, ENEMY_W, ENEMY_H)
                self.vx, self.vy = -speed, 0

        if is_glitch:
            self.vx *= 0.7
            self.vy *= 0.7
        self.glitch_phase = random.uniform(0, math.pi * 2)

    def update(self, time_flowing, slowmo_factor=1.0):
        if time_flowing:
            self.rect.x += self.vx * slowmo_factor
            self.rect.y += self.vy * slowmo_factor
        elif self.is_glitch:
            # 글리치 적: 시간 멈춰도 1/4 속도로 움직임!
            self.rect.x += self.vx * 0.25 * slowmo_factor
            self.rect.y += self.vy * 0.25 * slowmo_factor
        self.glitch_phase += 0.2 * slowmo_factor

    def is_off_screen(self):
        return (self.rect.top > HEIGHT or
                self.rect.right < 0 or
                self.rect.left > WIDTH)

    def draw(self, surface, ox, oy, time_flowing):
        r = self.rect.copy()
        r.x += ox
        r.y += oy

        if self.is_glitch:
            # 글리치 적 - 깜빡임 + 흔들림
            shake = math.sin(self.glitch_phase * 2) * 2
            r.x += int(shake)

            pygame.draw.rect(surface, GLITCH_COLOR, r)

            border_c = WHITE if math.sin(self.glitch_phase * 3) > 0 else GLITCH_COLOR
            pygame.draw.rect(surface, border_c, r, 3)

            # X 표시
            pygame.draw.line(surface, WHITE,
                           (r.x + 6, r.y + 6),
                           (r.right - 6, r.bottom - 6), 2)
            pygame.draw.line(surface, WHITE,
                           (r.right - 6, r.y + 6),
                           (r.x + 6, r.bottom - 6), 2)
        else:
            if time_flowing:
                pygame.draw.rect(surface, ENEMY_COLOR, r)
                pygame.draw.rect(surface, WHITE, r, 2)
            else:
                pygame.draw.rect(surface, (120, 40, 40), r)
                pygame.draw.rect(surface, (255, 200, 200), r, 2)

# ============================================================
# Item (크리스탈 + 하트)
# ============================================================
class Item:
    def __init__(self, item_type):
        self.type = item_type
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(80, HEIGHT - 150)
        self.phase = random.uniform(0, math.pi * 2)
        self.size = 22 if item_type == "crystal" else 26
        self.lifetime = 0
        self.max_lifetime = 600

    def update(self, time_flowing, slowmo_factor=1.0):
        if time_flowing:
            self.phase += 0.1 * slowmo_factor
            self.lifetime += slowmo_factor

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2,
                          int(self.y) - self.size // 2,
                          self.size, self.size)

    def should_despawn(self):
        return self.lifetime >= self.max_lifetime

    def draw(self, surface, ox, oy):
        cx = int(self.x) + ox
        cy = int(self.y) + oy

        # 수명 마지막엔 깜빡임
        remaining = self.max_lifetime - self.lifetime
        if remaining < 120:
            if (int(remaining) // 10) % 2 == 0:
                return

        pulse = math.sin(self.phase) * 3
        size = self.size + int(pulse)

        if self.type == "crystal":
            color = CRYSTAL_COLOR
            # 글로우
            for i in range(3):
                r = size // 2 + i * 3
                alpha = 80 - i * 25
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, alpha), (r, r), r)
                surface.blit(s, (cx - r, cy - r))
            # 다이아몬드
            points = [
                (cx, cy - size // 2),
                (cx + size // 2, cy),
                (cx, cy + size // 2),
                (cx - size // 2, cy),
            ]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, WHITE, points, 2)
        else:
            # 하트
            color = HEART_COLOR
            for i in range(3):
                r = size // 2 + i * 4
                alpha = 100 - i * 30
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, alpha), (r, r), r)
                surface.blit(s, (cx - r, cy - r))

            h_size = size // 2
            pygame.draw.circle(surface, color,
                             (cx - h_size // 2, cy - 2), h_size // 2)
            pygame.draw.circle(surface, color,
                             (cx + h_size // 2, cy - 2), h_size // 2)
            points = [
                (cx - h_size, cy),
                (cx + h_size, cy),
                (cx, cy + h_size),
            ]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.circle(surface, WHITE,
                             (cx - h_size // 2 - 2, cy - 5), 3)

# ============================================================
# HUD
# ============================================================
def draw_hud(surface, score, level_cfg, lives, combo, time_energy,
             time_flowing, burnout_timer):
    surface.blit(font.render(f"SCORE {score}", True, WHITE), (15, 10))
    surface.blit(font_small.render(level_cfg["label"], True, GOLD), (15, 48))

    # 라이프 (하트 아이콘)
    for i in range(lives):
        x = WIDTH - 30 - i * 28
        pygame.draw.circle(surface, HEART_COLOR, (x + 6, 23), 5)
        pygame.draw.circle(surface, HEART_COLOR, (x + 16, 23), 5)
        points = [(x + 1, 25), (x + 21, 25), (x + 11, 36)]
        pygame.draw.polygon(surface, HEART_COLOR, points)

    if combo >= 2:
        combo_text = font.render(f"COMBO x{combo}", True, GOLD)
        surface.blit(combo_text, (WIDTH // 2 - combo_text.get_width() // 2, 15))

    # 타임 에너지 바
    bar_w, bar_h = 300, 16
    bar_x = WIDTH // 2 - bar_w // 2
    bar_y = HEIGHT - 30
    pygame.draw.rect(surface, (50, 50, 60), (bar_x, bar_y, bar_w, bar_h))
    fill_w = int(bar_w * (time_energy / MAX_TIME_ENERGY))

    blink = (pygame.time.get_ticks() // 100) % 2 == 0
    if burnout_timer > 0:
        bar_color = ENEMY_COLOR if blink else (120, 30, 30)
        fill_w = bar_w
    elif time_energy > 50:
        bar_color = PURPLE
    elif time_energy > 30:
        bar_color = GOLD
    else:
        bar_color = ENEMY_COLOR if blink else (120, 30, 30)

    pygame.draw.rect(surface, bar_color, (bar_x, bar_y, fill_w, bar_h))
    pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 2)

    if burnout_timer > 0:
        label = font_tiny.render(
            f"!! BURNOUT !! {burnout_timer / 60:.1f}s", True, ENEMY_COLOR)
    else:
        label = font_tiny.render("TIME ENERGY", True, WHITE)
    surface.blit(label, (WIDTH // 2 - label.get_width() // 2, bar_y - 20))

    if burnout_timer > 0:
        status = font_small.render("BURNOUT - CAN'T STOP TIME!",
                                    True, ENEMY_COLOR)
    elif time_flowing:
        status = font_small.render("TIME FLOWING", True, GREEN)
    else:
        status = font_small.render("TIME STOPPED", True, (180, 180, 220))
    surface.blit(status, (WIDTH // 2 - status.get_width() // 2, HEIGHT - 60))

# ============================================================
# 오버레이
# ============================================================
def apply_grayscale_tint(surface, intensity=0.7):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill((120, 120, 140))
    overlay.set_alpha(int(100 * intensity))
    surface.blit(overlay, (0, 0))

def apply_slowmo_tint(surface, intensity):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill((255, 100, 100))
    overlay.set_alpha(int(80 * intensity))
    surface.blit(overlay, (0, 0))
    thickness = int(15 * intensity)
    if thickness > 0:
        pygame.draw.rect(surface, (255, 80, 80),
                        (0, 0, WIDTH, HEIGHT), thickness)

# ============================================================
# 타이틀
# ============================================================
def title_screen():
    t = 0
    while True:
        t += 1
        screen.fill(BG_COLOR)
        update_and_draw_stars(screen, True)

        title1 = font_huge.render("SUPERHOT", True, ENEMY_COLOR)
        title2 = font_huge.render("DODGER", True, WHITE)
        screen.blit(title1, (WIDTH // 2 - title1.get_width() // 2, 90))
        screen.blit(title2, (WIDTH // 2 - title2.get_width() // 2, 170))

        sub = font_small.render("TIME MOVES ONLY WHEN YOU MOVE", True, GOLD)
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 265))

        features = [
            "방향키 : 이동 (움직이면 시간이 흐름)",
            "가만히 있으면 시간 멈춤 / 에너지 소진 시 BURNOUT",
            "[CRYSTAL] 에너지 충전 + 보너스",
            "[HEART] 생명 회복 (희귀)",
            "[GLITCH] 시간 멈춰도 움직이는 적!",
        ]
        for i, line in enumerate(features):
            txt = font_small.render(line, True, WHITE)
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 320 + i * 28))

        if (t // 30) % 2 == 0:
            start = font.render("PRESS SPACE TO START", True, GREEN)
            screen.blit(start, (WIDTH // 2 - start.get_width() // 2, 500))

        pygame.display.flip()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    return
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

# ============================================================
# 게임 오버
# ============================================================
def game_over_screen(score, best, crystals, hearts):
    t = 0
    while True:
        t += 1
        screen.fill(BG_COLOR)
        update_and_draw_stars(screen, False)
        apply_grayscale_tint(screen, 0.9)

        over = font_huge.render("GAME OVER", True, ENEMY_COLOR)
        screen.blit(over, (WIDTH // 2 - over.get_width() // 2, 80))

        score_txt = font_big.render(f"SCORE: {score}", True, WHITE)
        screen.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 200))

        best_txt = font.render(f"BEST: {best}", True, GOLD)
        screen.blit(best_txt, (WIDTH // 2 - best_txt.get_width() // 2, 280))

        if score >= best and score > 0:
            new_txt = font.render("*** NEW RECORD ***", True, GOLD)
            screen.blit(new_txt, (WIDTH // 2 - new_txt.get_width() // 2, 325))

        stats_y = 380
        c_txt = font_small.render(f"CRYSTAL 획득: {crystals}",
                                   True, CRYSTAL_COLOR)
        screen.blit(c_txt, (WIDTH // 2 - c_txt.get_width() // 2, stats_y))
        h_txt = font_small.render(f"HEART 획득: {hearts}", True, HEART_COLOR)
        screen.blit(h_txt, (WIDTH // 2 - h_txt.get_width() // 2, stats_y + 28))

        if (t // 30) % 2 == 0:
            retry = font.render("R: RESTART   Q: QUIT", True, WHITE)
            screen.blit(retry, (WIDTH // 2 - retry.get_width() // 2, 475))

        pygame.display.flip()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r: return True
                if e.key == pygame.K_q or e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

# ============================================================
# 메인 루프
# ============================================================
def game_loop(best_score):
    player = pygame.Rect(WIDTH // 2 - PLAYER_W // 2,
                         HEIGHT - 120, PLAYER_W, PLAYER_H)
    enemies = []
    items = []
    score = 0
    lives = 3
    combo = 0
    spawn_timer = 0
    level_idx = 0
    level_cfg = LEVELS[level_idx]
    invincible = 0
    time_energy = MAX_TIME_ENERGY
    burnout_timer = 0
    tint_level = 1.0
    frame = 0

    crystal_spawn_timer = random.randint(CRYSTAL_SPAWN_MIN, CRYSTAL_SPAWN_MAX)
    heart_spawn_timer = random.randint(HEART_SPAWN_MIN, HEART_SPAWN_MAX)
    slowmo_timer = 0
    crystals_total = 0
    hearts_total = 0

    trail = []

    while True:
        clock.tick(FPS)
        frame += 1

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return score, crystals_total, hearts_total

        # 슬로우 모션
        is_slowmo = slowmo_timer > 0
        slowmo_factor = 0.4 if is_slowmo else 1.0
        if slowmo_timer > 0:
            slowmo_timer -= 1

        # 입력
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]: dx += PLAYER_SPEED
        if keys[pygame.K_UP]:    dy -= PLAYER_SPEED
        if keys[pygame.K_DOWN]:  dy += PLAYER_SPEED

        moving = (dx != 0 or dy != 0)
        player.x = max(0, min(WIDTH - PLAYER_W, player.x + dx))
        player.y = max(0, min(HEIGHT - PLAYER_H, player.y + dy))

        # 시간 흐름
        if burnout_timer > 0:
            burnout_timer -= 1
            time_flowing = True
            time_energy = min(MAX_TIME_ENERGY,
                            time_energy + TIME_REGEN_RATE * 2)
            tint_level = max(0, tint_level - 0.08)
        elif moving:
            time_flowing = True
            time_energy = min(MAX_TIME_ENERGY,
                            time_energy + TIME_REGEN_RATE)
            tint_level = max(0, tint_level - 0.08)
        else:
            time_flowing = False
            time_energy -= TIME_DECAY_RATE
            tint_level = min(1.0, tint_level + 0.08)
            if time_energy <= 0:
                time_energy = 0
                burnout_timer = BURNOUT_DURATION
                add_shake(10)
                spawn_particles(player.centerx, player.centery,
                               ENEMY_COLOR, count=15, spread=5)

        # 트레일
        if time_flowing and moving:
            trail.append((player.x + PLAYER_W // 2,
                         player.y + PLAYER_H // 2, 15))
            if len(trail) > 8:
                trail.pop(0)
        trail = [(x, y, life - 1) for x, y, life in trail if life > 1]

        # 적 스폰
        if time_flowing:
            spawn_timer += slowmo_factor
            if spawn_timer >= level_cfg["spawn"]:
                spawn_timer = 0
                is_glitch = (frame >= GLITCH_CHANCE_START and
                            random.random() < GLITCH_SPAWN_RATE)
                enemies.append(Enemy(level_cfg, is_glitch=is_glitch))

        # 아이템 스폰
        if time_flowing:
            crystal_spawn_timer -= slowmo_factor
            if crystal_spawn_timer <= 0:
                crystal_spawn_timer = random.randint(CRYSTAL_SPAWN_MIN,
                                                     CRYSTAL_SPAWN_MAX)
                items.append(Item("crystal"))

            heart_spawn_timer -= slowmo_factor
            if heart_spawn_timer <= 0:
                heart_spawn_timer = random.randint(HEART_SPAWN_MIN,
                                                   HEART_SPAWN_MAX)
                if lives < MAX_LIVES:
                    items.append(Item("heart"))

        # 적 업데이트
        survived = []
        for enemy in enemies:
            enemy.update(time_flowing, slowmo_factor)
            if enemy.is_off_screen():
                score += 1
                combo += 1
                if combo >= 5:
                    score += combo // 5
            else:
                survived.append(enemy)
        enemies = survived

        # 아이템 업데이트
        items_survived = []
        for item in items:
            item.update(time_flowing, slowmo_factor)
            if not item.should_despawn():
                items_survived.append(item)
        items = items_survived

        # 파티클
        for p in particles:
            p.update(time_flowing)
        particles[:] = [p for p in particles if p.life > 0]

        # 아이템 획득
        for item in items[:]:
            if player.colliderect(item.get_rect()):
                if item.type == "crystal":
                    time_energy = MAX_TIME_ENERGY
                    burnout_timer = 0
                    score += 15
                    crystals_total += 1
                    spawn_particles(item.x, item.y,
                                  CRYSTAL_COLOR, count=25, spread=6)
                    add_shake(5)
                else:
                    if lives < MAX_LIVES:
                        lives += 1
                    score += 30
                    hearts_total += 1
                    spawn_particles(item.x, item.y,
                                  HEART_COLOR, count=30, spread=7)
                    add_shake(8)
                items.remove(item)

        # 충돌
        if invincible > 0:
            invincible -= 1
        else:
            for enemy in enemies:
                if player.colliderect(enemy.rect):
                    lives -= 1
                    invincible = 90
                    combo = 0
                    slowmo_timer = SLOWMO_DURATION
                    add_shake(20)
                    p_color = GLITCH_COLOR if enemy.is_glitch else ENEMY_COLOR
                    spawn_particles(player.centerx, player.centery,
                                   p_color, count=35, spread=8)
                    enemies.clear()
                    if lives <= 0:
                        return score, crystals_total, hearts_total
                    break

        # 레벨
        level_idx = min(score // 20, len(LEVELS) - 1)
        level_cfg = LEVELS[level_idx]

        # =================== 렌더링 ===================
        if tint_level > 0.5:
            bg = (20, 20, 30)
        else:
            bg = (30, 25, 40)
        screen.fill(bg)

        update_and_draw_stars(screen, time_flowing)
        shake_x, shake_y = get_shake_offset()

        # 트레일
        for tx, ty, life in trail:
            alpha = life / 15
            size = int(PLAYER_W * alpha * 0.8)
            c = (int(PLAYER_COLOR[0] * alpha * 0.5),
                 int(PLAYER_COLOR[1] * alpha * 0.5),
                 int(PLAYER_COLOR[2] * alpha * 0.5))
            if size > 0:
                pygame.draw.rect(screen, c,
                               (tx - size // 2 + shake_x,
                                ty - size // 2 + shake_y, size, size))

        # 아이템 (적보다 먼저 - 배경에 가깝게)
        for item in items:
            item.draw(screen, shake_x, shake_y)

        # 적
        for enemy in enemies:
            enemy.draw(screen, shake_x, shake_y, time_flowing)

        # 플레이어
        if invincible == 0 or (invincible // 6) % 2 == 0:
            pr = player.copy()
            pr.x += shake_x
            pr.y += shake_y
            if time_flowing:
                pygame.draw.rect(screen, PLAYER_COLOR, pr)
            else:
                pygame.draw.rect(screen, (40, 100, 130), pr)
                pygame.draw.rect(screen, PLAYER_COLOR, pr, 3)
            pygame.draw.circle(screen, WHITE,
                             (pr.centerx, pr.centery), 3)

        # 파티클
        for p in particles:
            p.draw(screen)

        # 시간 멈춤 오버레이
        if tint_level > 0:
            apply_grayscale_tint(screen, tint_level * 0.6)

        # 슬로우 모션 오버레이
        if slowmo_timer > 0:
            intensity = slowmo_timer / SLOWMO_DURATION
            apply_slowmo_tint(screen, intensity)
            hit_text = font_big.render("HIT!", True, ENEMY_COLOR)
            alpha_surf = pygame.Surface(hit_text.get_size(), pygame.SRCALPHA)
            alpha_surf.blit(hit_text, (0, 0))
            alpha_surf.set_alpha(int(255 * intensity))
            screen.blit(alpha_surf,
                       (WIDTH // 2 - hit_text.get_width() // 2, 120))

        # BURNOUT 경고
        if burnout_timer > 0:
            if (frame // 6) % 2 == 0:
                pygame.draw.rect(screen, ENEMY_COLOR,
                               (0, 0, WIDTH, HEIGHT), 8)

        draw_hud(screen, score, level_cfg, lives, combo,
                time_energy, time_flowing, burnout_timer)

        # 글리치 해금 알림
        if GLITCH_CHANCE_START <= frame < GLITCH_CHANCE_START + 180:
            if (frame // 10) % 2 == 0:
                warn = font.render("!! GLITCH ENEMY 등장 !!", True, GLITCH_COLOR)
                screen.blit(warn,
                           (WIDTH // 2 - warn.get_width() // 2, 105))
            if frame == GLITCH_CHANCE_START:
                add_shake(15)

        # 도움말
        if frame < 300:
            help_text = font_tiny.render(
                "TIP: 가만히 있으면 시간이 멈춥니다. CRYSTAL로 에너지 충전!",
                True, GOLD)
            screen.blit(help_text,
                       (WIDTH // 2 - help_text.get_width() // 2, 90))

        pygame.display.flip()

# ============================================================
# 엔트리
# ============================================================
def main():
    best_score = 0
    title_screen()
    while True:
        score, crystals, hearts = game_loop(best_score)
        if score > best_score:
            best_score = score
        if not game_over_screen(score, best_score, crystals, hearts):
            break

if __name__ == "__main__":
    main()