"""
============================================================
  SUPERHOT DODGER v2 - 시간 멈춤 피하기
  창의 프로그래밍 입문 설계 - 중간 프로젝트
============================================================
  핵심 메커니즘:
    - 가만히 있으면 시간이 멈춘다 (흑백 화면)
    - 움직이면 시간이 흐른다 (컬러 화면)
    - 에너지 소진 시 BURNOUT

  추가 요소:
    CRYSTAL  - 에너지 풀충전 + 보너스
    HEART    - 생명 +1 (최대 5, 희귀)
    GLITCH   - 시간 멈춰도 움직이는 적
    SLOWMO   - 피격 시 슬로우 모션

  에셋:
    assets/images/ 에 있으면 사용, 없으면 도형으로 렌더링
    assets/sounds/ 에 있으면 재생, 없으면 무음
============================================================
"""

import pygame
import random
import sys
import math
import os

pygame.init()
# 작은 버퍼로 초기화 (지연 최소화)
pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.mixer.init()

# 볼륨 설정 (0.0 ~ 1.0)
BGM_VOLUME = 0.1
SFX_VOLUME = 0.6

# ------------------------------------------------------------
# 경로 설정 (Thonny/Windows/Mac/Linux 호환)
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "assets", "images")
SND_DIR = os.path.join(BASE_DIR, "assets", "sounds")

# ------------------------------------------------------------
# 에셋 로드 헬퍼 (파일 없어도 에러 안 나게)
# ------------------------------------------------------------
def load_image(filename, size=None):
    """이미지 로드. 없으면 None 반환."""
    path = os.path.join(IMG_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        if size is not None:
            img = pygame.transform.scale(img, size)
        return img
    except Exception as e:
        print(f"[경고] 이미지 로드 실패: {filename} - {e}")
        return None

def load_sound(filename):
    """효과음 로드. 없으면 None 반환."""
    path = os.path.join(SND_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        snd = pygame.mixer.Sound(path)
        return snd
    except Exception as e:
        print(f"[경고] 사운드 로드 실패: {filename} - {e}")
        return None

def play_sound(snd):
    """None이면 조용히 스킵. 재생 시 현재 SFX_VOLUME 적용."""
    if snd is not None:
        snd.set_volume(SFX_VOLUME)
        snd.play()

def apply_bgm_volume():
    pygame.mixer.music.set_volume(BGM_VOLUME)

def load_bgm(filename):
    """배경음악 로드 및 재생. 없으면 조용히 스킵."""
    path = os.path.join(SND_DIR, filename)
    if not os.path.exists(path):
        return False
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(BGM_VOLUME)
        pygame.mixer.music.play(-1)
        return True
    except Exception as e:
        print(f"[경고] BGM 로드 실패: {filename} - {e}")
        return False

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

PLAYER_W, PLAYER_H = 40, 40
ENEMY_W, ENEMY_H = 30, 30
PLAYER_SPEED = 5

TIME_DECAY_RATE = 0.4
TIME_REGEN_RATE = 0.25
MAX_TIME_ENERGY = 100.0
BURNOUT_DURATION = 120

MAX_LIVES = 5
CRYSTAL_SPAWN_MIN = 600
CRYSTAL_SPAWN_MAX = 900
HEART_SPAWN_MIN = 1800
HEART_SPAWN_MAX = 3000
GLITCH_CHANCE_START = 40 * 60
GLITCH_SPAWN_RATE = 0.15
SLOWMO_DURATION = 40

screen = pygame.display.set_mode((WIDTH, HEIGHT))

def flip_display():
    pygame.display.flip()
pygame.display.set_caption("SUPERHOT DODGER v2")
clock = pygame.time.Clock()

font_tiny  = get_korean_font(18)
font_small = get_korean_font(24)
font       = get_korean_font(32)
font_big   = get_korean_font(56)
font_huge  = get_korean_font(80)

# ------------------------------------------------------------
# 에셋 로드 (게임 시작 시 한 번만)
# ------------------------------------------------------------
print("=" * 50)
print("에셋 로드 중...")

IMG_PLAYER     = load_image("player.png",     (PLAYER_W, PLAYER_H))
IMG_ENEMY      = load_image("enemy.png",      (ENEMY_W, ENEMY_H))
IMG_GLITCH     = load_image("glitch.png",     (ENEMY_W, ENEMY_H))
IMG_CRYSTAL    = load_image("crystal.png",    (30, 30))
IMG_HEART      = load_image("heart.png",      (30, 30))
IMG_BACKGROUND = load_image("background.png", (WIDTH, HEIGHT))

SND_HIT     = load_sound("hit.wav")
SND_CRYSTAL = load_sound("crystal.wav")
SND_HEART   = load_sound("heart.wav")
SND_FREEZE  = load_sound("freeze.wav")
SND_GAMEOVER = load_sound("gameover.wav")

# 에셋 상태 출력
assets_status = {
    "player.png":     IMG_PLAYER is not None,
    "enemy.png":      IMG_ENEMY is not None,
    "glitch.png":     IMG_GLITCH is not None,
    "background.png": IMG_BACKGROUND is not None,
    "crystal.png":    IMG_CRYSTAL is not None,
    "heart.png":      IMG_HEART is not None,
    "hit.wav":        SND_HIT is not None,
    "crystal.wav":    SND_CRYSTAL is not None,
    "bgm.ogg":        False,  # 아래서 로드
}
for name, loaded in assets_status.items():
    mark = "OK " if loaded else "-- "
    print(f"  [{mark}] {name}")

# BGM 시도 (여러 확장자)
bgm_loaded = False
for ext in ["ogg", "mp3", "wav"]:
    if load_bgm(f"bgm.{ext}"):
        bgm_loaded = True
        print(f"  [OK ] bgm.{ext}")
        break
if not bgm_loaded:
    print("  [-- ] bgm (어떤 확장자도 못 찾음)")

print("=" * 50)

LEVELS = [
    {"min_speed": 2, "max_speed": 4,  "spawn": 55, "label": "Lv.1 BEGINNER"},
    {"min_speed": 3, "max_speed": 6,  "spawn": 42, "label": "Lv.2 WARRIOR"},
    {"min_speed": 4, "max_speed": 8,  "spawn": 32, "label": "Lv.3 MASTER"},
    {"min_speed": 6, "max_speed": 11, "spawn": 24, "label": "Lv.4 LEGEND"},
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

def draw_background(surface, time_flowing):
    """배경 이미지가 있으면 그림, 없으면 별 배경."""
    if IMG_BACKGROUND is not None:
        surface.blit(IMG_BACKGROUND, (0, 0))
        # 시간 멈춤 시 어둡게
        if not time_flowing:
            dark = pygame.Surface((WIDTH, HEIGHT))
            dark.fill((0, 0, 0))
            dark.set_alpha(100)
            surface.blit(dark, (0, 0))
    else:
        # 기본 배경색 + 별
        if time_flowing:
            surface.fill((30, 25, 40))
        else:
            surface.fill((20, 20, 30))
        update_and_draw_stars(surface, time_flowing)

# ============================================================
# Enemy
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
            shake = math.sin(self.glitch_phase * 2) * 2
            r.x += int(shake)

            if IMG_GLITCH is not None:
                surface.blit(IMG_GLITCH, r)
                border_c = WHITE if math.sin(self.glitch_phase * 3) > 0 else GLITCH_COLOR
                pygame.draw.rect(surface, border_c, r, 2)
            else:
                pygame.draw.rect(surface, GLITCH_COLOR, r)
                border_c = WHITE if math.sin(self.glitch_phase * 3) > 0 else GLITCH_COLOR
                pygame.draw.rect(surface, border_c, r, 3)
                pygame.draw.line(surface, WHITE,
                               (r.x + 6, r.y + 6),
                               (r.right - 6, r.bottom - 6), 2)
                pygame.draw.line(surface, WHITE,
                               (r.right - 6, r.y + 6),
                               (r.x + 6, r.bottom - 6), 2)
        else:
            if IMG_ENEMY is not None:
                if not time_flowing:
                    dark_sprite = IMG_ENEMY.copy()
                    dark_sprite.fill((80, 80, 80),
                                     special_flags=pygame.BLEND_RGB_MULT)
                    surface.blit(dark_sprite, r)
                else:
                    surface.blit(IMG_ENEMY, r)
            else:
                if time_flowing:
                    pygame.draw.rect(surface, ENEMY_COLOR, r)
                    pygame.draw.rect(surface, WHITE, r, 2)
                else:
                    pygame.draw.rect(surface, (120, 40, 40), r)
                    pygame.draw.rect(surface, (255, 200, 200), r, 2)

# ============================================================
# Item
# ============================================================
class Item:
    def __init__(self, item_type):
        self.type = item_type
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(80, HEIGHT - 150)
        self.phase = random.uniform(0, math.pi * 2)
        self.size = 30
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

        remaining = self.max_lifetime - self.lifetime
        if remaining < 120:
            if (int(remaining) // 10) % 2 == 0:
                return

        pulse = math.sin(self.phase) * 3
        size = self.size + int(pulse)

        sprite = IMG_CRYSTAL if self.type == "crystal" else IMG_HEART

        if sprite is not None:
            color = CRYSTAL_COLOR if self.type == "crystal" else HEART_COLOR
            for i in range(3):
                r = size // 2 + i * 3
                alpha = 80 - i * 25
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, alpha), (r, r), r)
                surface.blit(s, (cx - r, cy - r))
            scaled = pygame.transform.scale(sprite, (size, size))
            rect = scaled.get_rect(center=(cx, cy))
            surface.blit(scaled, rect)
        else:
            if self.type == "crystal":
                color = CRYSTAL_COLOR
                for i in range(3):
                    r = size // 2 + i * 3
                    alpha = 80 - i * 25
                    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*color, alpha), (r, r), r)
                    surface.blit(s, (cx - r, cy - r))
                points = [
                    (cx, cy - size // 2),
                    (cx + size // 2, cy),
                    (cx, cy + size // 2),
                    (cx - size // 2, cy),
                ]
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, WHITE, points, 2)
            else:  # heart
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

    for i in range(lives):
        x = WIDTH - 30 - i * 28
        soap_rect = pygame.Rect(x, 16, 22, 20)
        pygame.draw.rect(surface, CRYSTAL_COLOR, soap_rect, border_radius=5)
        pygame.draw.rect(surface, WHITE, soap_rect, 2, border_radius=5)
        pygame.draw.circle(surface, WHITE, (x + 5, 20), 2)

    if combo >= 2:
        combo_text = font.render(f"COMBO x{combo}", True, GOLD)
        surface.blit(combo_text, (WIDTH // 2 - combo_text.get_width() // 2, 15))

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
    surface.blit(label, (WIDTH // 2 - label.get_width() // 2, bar_y - 30))

    if burnout_timer > 0:
        status = font_small.render("BURNOUT - CAN'T STOP TIME!",
                                    True, ENEMY_COLOR)
    elif time_flowing:
        status = font_small.render("TIME FLOWING", True, GREEN)
    else:
        status = font_small.render("TIME STOPPED", True, (180, 180, 220))
    surface.blit(status, (WIDTH // 2 - status.get_width() // 2, HEIGHT - 100))

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
# 볼륨 팝업 (마우스 드래그 슬라이더)
# ============================================================
def volume_popup():
    """볼륨 조절 팝업. 마우스로 슬라이더 드래그 or ESC/X 버튼으로 닫음."""
    global BGM_VOLUME, SFX_VOLUME

    # 팝업 박스 위치
    box_w, box_h = 460, 320
    box_x = WIDTH // 2 - box_w // 2
    box_y = HEIGHT // 2 - box_h // 2
    box = pygame.Rect(box_x, box_y, box_w, box_h)

    # 슬라이더 레이아웃
    bar_x     = box_x + 130
    bar_w     = 250
    bar_h     = 20
    bar_rects = [
        pygame.Rect(bar_x, box_y + 100, bar_w, bar_h),  # BGM
        pygame.Rect(bar_x, box_y + 180, bar_w, bar_h),  # SFX
    ]

    # X(닫기) 버튼
    close_rect = pygame.Rect(box_x + box_w - 40, box_y + 10, 28, 28)

    dragging = -1  # -1: 안 드래그, 0: BGM, 1: SFX

    def vol_to_x(idx):
        """볼륨 값 → 슬라이더 핸들 X 좌표"""
        vol = BGM_VOLUME if idx == 0 else SFX_VOLUME
        return bar_rects[idx].x + int(vol * bar_w)

    def x_to_vol(idx, mx):
        """마우스 X → 볼륨 값 (0.0~1.0)"""
        rel = mx - bar_rects[idx].x
        return max(0.0, min(1.0, rel / bar_w))

    def handle_x(idx):
        return pygame.Rect(vol_to_x(idx) - 8, bar_rects[idx].y - 5, 16, bar_h + 10)

    while True:
        draw_background(screen, True)

        # 어두운 오버레이
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        screen.blit(overlay, (0, 0))

        # 팝업 박스
        pygame.draw.rect(screen, (30, 30, 40), box, border_radius=12)
        pygame.draw.rect(screen, WHITE, box, 3, border_radius=12)

        # 제목
        title = font.render("VOLUME SETTINGS", True, GOLD)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, box_y + 22))

        # X 닫기 버튼
        pygame.draw.rect(screen, (80, 30, 30), close_rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, close_rect, 2, border_radius=5)
        x_lbl = font_small.render("X", True, WHITE)
        screen.blit(x_lbl, (close_rect.x + close_rect.w // 2 - x_lbl.get_width() // 2,
                             close_rect.y + close_rect.h // 2 - x_lbl.get_height() // 2))

        # 슬라이더 그리기
        for i, (label, vol) in enumerate([("BGM", BGM_VOLUME),
                                           ("SFX", SFX_VOLUME)]):
            bar = bar_rects[i]
            is_drag = (dragging == i)
            color = GOLD if is_drag else WHITE

            # 라벨
            lbl = font.render(label, True, color)
            screen.blit(lbl, (box_x + 30, bar.y - 4))

            # 트랙 (배경)
            pygame.draw.rect(screen, (60, 60, 70), bar, border_radius=8)

            # 채워진 부분
            fill_w = int(bar_w * vol)
            if fill_w > 0:
                fill_rect = pygame.Rect(bar.x, bar.y, fill_w, bar_h)
                pygame.draw.rect(screen, color, fill_rect, border_radius=8)

            # 트랙 테두리
            pygame.draw.rect(screen, WHITE, bar, 2, border_radius=8)

            # 핸들 (동그라미)
            hx = bar.x + fill_w
            hy = bar.centery
            pygame.draw.circle(screen, color, (hx, hy), 11)
            pygame.draw.circle(screen, (20, 20, 30), (hx, hy), 7)
            if is_drag:
                pygame.draw.circle(screen, GOLD, (hx, hy), 11, 2)

            # 퍼센트
            pct = font_small.render(f"{int(vol * 100)}%", True, color)
            screen.blit(pct, (bar.x + bar_w + 14, bar.y - 2))

        # 도움말
        help1 = font_tiny.render("슬라이더를 마우스로 드래그하세요   ESC: 닫기", True, (180, 180, 180))
        screen.blit(help1, (WIDTH // 2 - help1.get_width() // 2, box_y + box_h - 38))

        flip_display()
        clock.tick(FPS)

        mx, my = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ---------- 마우스 버튼 누름 ----------
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # X 버튼 클릭
                if close_rect.collidepoint(mx, my):
                    return
                # 핸들 또는 트랙 클릭 → 드래그 시작
                for i in range(2):
                    # 핸들 영역 or 트랙 전체 영역 클릭
                    hit_area = bar_rects[i].inflate(0, 20)
                    if hit_area.collidepoint(mx, my) or handle_x(i).collidepoint(mx, my):
                        dragging = i
                        # 클릭 즉시 값 적용
                        new_vol = x_to_vol(i, mx)
                        if i == 0:
                            BGM_VOLUME = new_vol
                            pygame.mixer.music.set_volume(BGM_VOLUME)
                        else:
                            SFX_VOLUME = new_vol
                        break

            # ---------- 마우스 버튼 뗌 ----------
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                dragging = -1

            # ---------- 키보드 ----------
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return

        # ---------- 드래그 중이면 실시간 업데이트 ----------
        if dragging >= 0:
            new_vol = x_to_vol(dragging, mx)
            if dragging == 0:
                BGM_VOLUME = new_vol
                pygame.mixer.music.set_volume(BGM_VOLUME)
            else:
                SFX_VOLUME = new_vol

# ============================================================
# 타이틀 화면 (600~700행 부근)
# ============================================================
def title_screen():
    # 폰트 설정
    try:
        font_main = pygame.font.SysFont("malgungothic", 100, bold=True)
        font_sub = pygame.font.SysFont("malgungothic", 35, bold=True)
        font_info = pygame.font.SysFont("malgungothic", 20, bold=True)
        font_small = pygame.font.SysFont("malgungothic", 18, bold=True)
    except:
        font_main = pygame.font.SysFont("arial", 100, bold=True)
        font_sub = pygame.font.SysFont("arial", 35, bold=True)
        font_info = pygame.font.SysFont("arial", 20, bold=True)
        font_small = pygame.font.SysFont("arial", 18, bold=True)

    title_text = "똥 피하기" # 제목을 강조
    sub_text = "뿌직"
    
    instructions = [
        "방향키: 이동 (움직여야 시간이 흐릅니다)",
        "가만히 있기: 시간 정지 (에너지 급속 소모)",
        "휴지: 에너지 충전 | 비누: 생명 연장",
        "번아웃: 에너지 방전 시 강제로 시간이 흐릅니다!"
    ]

    while True:
        screen.fill((15, 15, 20))
        
        # 1. 제목 (위로 올림: 150 -> 80)
        title_shadow = font_main.render(title_text, True, (40, 20, 0))
        title_surf = font_main.render(title_text, True, GOLD)
        screen.blit(title_shadow, (WIDTH // 2 - title_shadow.get_width() // 2 + 5, 85))
        screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 80))

        # 2. 부제목 (280 -> 200)
        sub_surf = font_sub.render(sub_text, True, (200, 200, 200))
        screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, 200))

        # 3. 설명 박스 (350 -> 270)
        box_rect = pygame.Rect(80, 270, WIDTH - 160, 160)
        pygame.draw.rect(screen, (30, 30, 40), box_rect, border_radius=15)
        pygame.draw.rect(screen, GOLD, box_rect, 2, border_radius=15)

        for i, line in enumerate(instructions):
            line_surf = font_info.render(line, True, WHITE)
            screen.blit(line_surf, (WIDTH // 2 - line_surf.get_width() // 2, 290 + i * 32))

        # 4. 볼륨 설정 안내 (위치를 살짝 위로: 540 -> 460)
        opt_surf = font_small.render("O: 볼륨 설정 | ESC: 종료", True, (150, 150, 150))
        screen.blit(opt_surf, (WIDTH // 2 - opt_surf.get_width() // 2, 460))

        # 5. 시작 안내 (깜빡임 효과, 가장 아래 유지)
        if (pygame.time.get_ticks() // 600) % 2 == 0:
            start_surf = font_sub.render("- PRESS SPACE TO START -", True, (0, 255, 150))
            screen.blit(start_surf, (WIDTH // 2 - start_surf.get_width() // 2, 530))

        flip_display()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return
                if event.key == pygame.K_o:
                    volume_popup()
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

        # 볼륨 설정 안내
       

        flip_display()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    return
                if e.key == pygame.K_o:
                    volume_popup()
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

# ============================================================
# 게임 오버
# ============================================================
def game_over_screen(score, best, crystals, hearts):
    t = 0
    played_gameover = False
    while True:
        t += 1
        if not played_gameover:
            play_sound(SND_GAMEOVER)
            played_gameover = True

        draw_background(screen, False)
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
        c_txt = font_small.render(f"휴지 획득: {crystals}",
                                   True, CRYSTAL_COLOR)
        screen.blit(c_txt, (WIDTH // 2 - c_txt.get_width() // 2, stats_y))
        h_txt = font_small.render(f"비누 획득: {hearts}", True, HEART_COLOR)
        screen.blit(h_txt, (WIDTH // 2 - h_txt.get_width() // 2, stats_y + 28))

        if (t // 30) % 2 == 0:
            retry = font.render("R: RESTART   Q: QUIT", True, WHITE)
            screen.blit(retry, (WIDTH // 2 - retry.get_width() // 2, 475))

        flip_display()
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
    prev_time_flowing = True

    trail = []

    while True:
        clock.tick(FPS)
        frame += 1

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return score, crystals_total, hearts_total

        is_slowmo = slowmo_timer > 0
        slowmo_factor = 0.4 if is_slowmo else 1.0
        if slowmo_timer > 0:
            slowmo_timer -= 1

        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:  dx -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]: dx += PLAYER_SPEED
        if keys[pygame.K_UP]:    dy -= PLAYER_SPEED
        if keys[pygame.K_DOWN]:  dy += PLAYER_SPEED

        moving = (dx != 0 or dy != 0)
        player.x = max(0, min(WIDTH - PLAYER_W, player.x + dx))
        player.y = max(0, min(HEIGHT - PLAYER_H, player.y + dy))

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

        if prev_time_flowing and not time_flowing:
            play_sound(SND_FREEZE)
        prev_time_flowing = time_flowing

        if time_flowing and moving and frame % 3 == 0:
            trail.append((player.x + PLAYER_W // 2,
                         player.y + PLAYER_H // 2, 8))
            if len(trail) > 4:
                trail.pop(0)
        trail = [(x, y, life - 1) for x, y, life in trail if life > 1]

        if time_flowing:
            spawn_timer += slowmo_factor
            if spawn_timer >= level_cfg["spawn"]:
                spawn_timer = 0
                is_glitch = (frame >= GLITCH_CHANCE_START and
                            random.random() < GLITCH_SPAWN_RATE)
                enemies.append(Enemy(level_cfg, is_glitch=is_glitch))

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

        items_survived = []
        for item in items:
            item.update(time_flowing, slowmo_factor)
            if not item.should_despawn():
                items_survived.append(item)
        items = items_survived

        for p in particles:
            p.update(time_flowing)
        particles[:] = [p for p in particles if p.life > 0]

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
                    play_sound(SND_CRYSTAL)
                else:
                    if lives < MAX_LIVES:
                        lives += 1
                    score += 30
                    hearts_total += 1
                    spawn_particles(item.x, item.y,
                                  HEART_COLOR, count=30, spread=7)
                    add_shake(8)
                    play_sound(SND_HEART)
                items.remove(item)

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
                    play_sound(SND_HIT)
                    if lives <= 0:
                        return score, crystals_total, hearts_total
                    break

        level_idx = min(score // 25, len(LEVELS) - 1)
        level_cfg = LEVELS[level_idx]

        # ============ 렌더링 ============
        draw_background(screen, time_flowing)
        shake_x, shake_y = get_shake_offset()

        for tx, ty, life in trail:
            alpha_ratio = life / 8
            if IMG_PLAYER is not None:
                trail_sprite = IMG_PLAYER.copy()
                trail_sprite.set_alpha(int(80 * alpha_ratio))
                rect = trail_sprite.get_rect(
                    center=(tx + shake_x, ty + shake_y))
                screen.blit(trail_sprite, rect)
            else:
                size = int(PLAYER_W * alpha_ratio * 0.8)
                c = (int(PLAYER_COLOR[0] * alpha_ratio * 0.5),
                     int(PLAYER_COLOR[1] * alpha_ratio * 0.5),
                     int(PLAYER_COLOR[2] * alpha_ratio * 0.5))
                if size > 0:
                    pygame.draw.rect(screen, c,
                                   (tx - size // 2 + shake_x,
                                    ty - size // 2 + shake_y, size, size))

        for item in items:
            item.draw(screen, shake_x, shake_y)

        for enemy in enemies:
            enemy.draw(screen, shake_x, shake_y, time_flowing)

        if invincible == 0 or (invincible // 6) % 2 == 0:
            pr = player.copy()
            pr.x += shake_x
            pr.y += shake_y

            if IMG_PLAYER is not None:
                if not time_flowing:
                    dark_sprite = IMG_PLAYER.copy()
                    dark_sprite.fill((80, 80, 80),
                                     special_flags=pygame.BLEND_RGB_MULT)
                    screen.blit(dark_sprite, pr)
                else:
                    screen.blit(IMG_PLAYER, pr)
            else:
                glow_color = PLAYER_COLOR if time_flowing else (60, 100, 140)
                glow_size = PLAYER_W + 20
                glow_surf = pygame.Surface((glow_size, glow_size),
                                          pygame.SRCALPHA)
                for i in range(3):
                    r = glow_size // 2 - i * 3
                    alpha = 40 - i * 10 if time_flowing else 20 - i * 5
                    if alpha > 0:
                        pygame.draw.circle(glow_surf, (*glow_color, alpha),
                                         (glow_size // 2, glow_size // 2), r)
                screen.blit(glow_surf,
                           (pr.centerx - glow_size // 2,
                            pr.centery - glow_size // 2))
                if time_flowing:
                    pygame.draw.rect(screen, PLAYER_COLOR, pr)
                else:
                    pygame.draw.rect(screen, (40, 100, 130), pr)
                    pygame.draw.rect(screen, PLAYER_COLOR, pr, 3)
                pygame.draw.circle(screen, WHITE,
                                 (pr.centerx, pr.centery), 3)

        for p in particles:
            p.draw(screen)

        if tint_level > 0:
            apply_grayscale_tint(screen, tint_level * 0.6)

        if slowmo_timer > 0:
            intensity = slowmo_timer / SLOWMO_DURATION
            apply_slowmo_tint(screen, intensity)
            hit_text = font_big.render("HIT!", True, ENEMY_COLOR)
            alpha_surf = pygame.Surface(hit_text.get_size(), pygame.SRCALPHA)
            alpha_surf.blit(hit_text, (0, 0))
            alpha_surf.set_alpha(int(255 * intensity))
            screen.blit(alpha_surf,
                       (WIDTH // 2 - hit_text.get_width() // 2, 120))

        if burnout_timer > 0:
            if (frame // 6) % 2 == 0:
                pygame.draw.rect(screen, ENEMY_COLOR,
                               (0, 0, WIDTH, HEIGHT), 8)

        draw_hud(screen, score, level_cfg, lives, combo,
                time_energy, time_flowing, burnout_timer)

        if GLITCH_CHANCE_START <= frame < GLITCH_CHANCE_START + 180:
            if (frame // 10) % 2 == 0:
                warn = font.render("!! 더 강한 똥 등장 !!", True, GLITCH_COLOR)
                screen.blit(warn,
                           (WIDTH // 2 - warn.get_width() // 2, 105))
            if frame == GLITCH_CHANCE_START:
                add_shake(15)

        if frame < 300:
            help_text = font_tiny.render(
                "TIP: 가만히 있으면 시간이 멈춥니다. 휴지로 에너지 충전!",
                True, GOLD)
            screen.blit(help_text,
                       (WIDTH // 2 - help_text.get_width() // 2, 90))

        flip_display()

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