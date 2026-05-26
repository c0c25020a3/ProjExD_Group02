import os
import math
import random
import sys
import time
import pygame as pg


WIDTH = 1100
HEIGHT = 650
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内にあるか判定する
    """
    yoko, tate = True, True

    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate

def draw_heart_surface(size: int, color: tuple) -> pg.Surface:
    """
    数式を使ってハート形を描いたSurface
    """
    surf = pg.Surface((size, size), pg.SRCALPHA)
    cx, cy = size // 2, size // 2
    scale = size / 44

    points = [
        (
            16 * math.sin(t / 100) ** 3 * scale + cx,
            -(13 * math.cos(t / 100) - 5 * math.cos(2 * t / 100)
              - 2 * math.cos(3 * t / 100) - math.cos(4 * t / 100)) * scale + cy
        )
        for t in range(0, 628)
    ]
    pg.draw.polygon(surf, color, points)
    return surf


class Life:
    HEART_SIZE = 50

    def __init__(self, num: int):
        """
        num：初期残機数
        """
        self.num = num
        self._hearts: list[pg.Surface] = []
        self._build_hearts()

        # 割れエフェクト
        self._kakera: list[dict] = []

    def _build_hearts(self):
        """残機数に応じた色でハートSurfaceを作り直す"""
        self._hearts = []
        for _ in range(self.num):
            if self.num == 3:
                color = (220, 30, 60)    # 赤
            elif self.num == 2:
                color = (255, 140, 0)    # オレンジ
            else:
                color = (255, 50, 50)    # 赤（点滅用）
            self._hearts.append(draw_heart_surface(self.HEART_SIZE, color))

    def decrease(self):
        """残機を1減らして割れエフェクトを起動する"""
        if self.num > 0:
            self._spawn_kakera()   # 割れエフェクト生成
            self.num -= 1
            self._build_hearts()   # ハートを作り直す

    def _spawn_kakera(self):
        """割れるパーティクル"""
        idx = self.num - 1
        rx = WIDTH - 50 - idx * (self.HEART_SIZE + 8)
        ry = HEIGHT - 50
        self._kakera = []
        for _ in range(18):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 6)
            self._kakera.append({
                "x": rx, "y": ry,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.randint(20, 40),  # 残り寿命
                "color": (
                    random.randint(180, 255),
                    random.randint(0, 60),
                    random.randint(0, 60),
                ),
                "size": random.randint(3, 8),
            })

    def update(self, dt: int):
        """パーティクルを毎フレーム動かす"""
        for p in self._kakera:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.3
            p["life"] -= 1

        self._kakera = [p for p in self._kakera if p["life"] > 0]

    def draw(self, screen: pg.Surface, now: int):
        """
        画面右下にハートを描画する
        """
        blink_visible = True
        if self.num == 1 and (now // 250) % 2 == 0:
            blink_visible = False

        for i, heart in enumerate(self._hearts):
            x = WIDTH - 50 - i * (self.HEART_SIZE + 8) - self.HEART_SIZE // 2
            y = HEIGHT - 50 - self.HEART_SIZE // 2

            if i == self.num - 1 and not blink_visible:
                continue
            screen.blit(heart, (x, y))

        # 割れパーティクル
        for p in self._kakera:
            pg.draw.circle(
                screen,
                p["color"],
                (int(p["x"]), int(p["y"])),
                p["size"]
            )


class Player(pg.sprite.Sprite):
    """
    プレイヤーに関するクラス
    """

    delta = {
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self):
        super().__init__()
        self.image = pg.image.load("fig/alien1.png")
        self.rect = self.image.get_rect()

        # スタート位置
        self.rect.center = (50, HEIGHT//2)

        # ★変更：速度設定
        self.normal_speed = 1
        self.dash_speed = 3
        self.speed = self.normal_speed
        self.move_flag = False

        # ★追加：スタミナ
        self.stamina = 100
        self.max_stamina = 100

        self.walk_se = pg.mixer.Sound("sound/asioto.mp3")

    def update(self, key_lst: list[bool]):
        """
        プレイヤー更新
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        moving = (sum_mv != [0, 0])  # ★追加：移動中判定
        # ★追加：ダッシュ処理
        if key_lst[pg.K_LSHIFT] and self.stamina > 0:
            self.speed = self.dash_speed
            self.stamina -= 1
        else:
            self.speed = self.normal_speed
            if not moving:
                self.stamina += 0.2

        # ★追加：スタミナ制限
        if self.stamina < 0:
            self.stamina = 0
        if self.stamina > self.max_stamina:
            self.stamina = self.max_stamina

        self.rect.move_ip(
            self.speed * sum_mv[0],
            self.speed * sum_mv[1]
        )

        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(
                -self.speed * sum_mv[0],
                -self.speed * sum_mv[1]
            )

        if moving:
            self.move_flag = True

            if not self.walk_se.get_num_channels():
                self.walk_se.play(-1)
        else:
            self.move_flag = False
            self.walk_se.stop()


class Oni(pg.sprite.Sprite):
    """
    鬼に関するクラス
    """

    def __init__(self):
        super().__init__()
        self.image_back = pg.image.load("fig/2.png")
        self.image_front = pg.transform.flip(
            self.image_back,
            True,
            False
        )

        self.image = self.image_back
        self.rect = self.image.get_rect()

        self.rect.center = (WIDTH - 50, HEIGHT // 2)
        self.look_flag = False

        self.next_turn = time.time() + random.uniform(5, 15)

        self.voice = pg.mixer.Sound("sound/sound.mp3")
        self.voice.play(-1)

    def update(self):
        """
        鬼更新
        """
        now = time.time()

        if not self.look_flag:
            if now >= self.next_turn:
                self.look_flag = True
                self.image = self.image_front
                self.voice.stop()
                self.next_turn = now + 3

        else:
            if now >= self.next_turn:
                self.look_flag = False
                self.image = self.image_back
                self.voice.play(-1)
                self.next_turn = now + random.uniform(5, 15)


def draw_text(
        screen: pg.Surface,
        text: str,
        size: int,
        color: tuple[int, int, int],
        center: tuple[int, int]
):
    """
    文字表示
    """
    font = pg.font.Font(None, size)
    txt = font.render(text, True, color)
    rect = txt.get_rect()
    rect.center = center
    screen.blit(txt, rect)


def gameover(screen: pg.Surface):
    fonto = pg.font.Font(None, 80)
    txt = fonto.render("Game Over", True, (255, 0, 0))
    screen.blit(txt, [WIDTH//2-150, HEIGHT//2])

def clear(screen: pg.Surface):
    fonto = pg.font.Font(None, 80)
    txt = fonto.render("Clear!", True, (0, 255, 0))
    screen.blit(txt, [WIDTH//2-150, HEIGHT//2])


# ★追加：スタミナバー表示
def draw_stamina(screen: pg.Surface, player: Player):
    pg.draw.rect(screen, (255, 255, 255), [20, 20, 200, 20])
    pg.draw.rect(screen, (0, 255, 0), [20, 20, player.stamina * 2, 20])
    pg.draw.rect(screen, (0, 0, 0), [20, 20, 200, 20], 2)

    draw_text(screen, "STAMINA", 30, (255, 255, 255), (120, 55))

def main():
    pg.display.set_caption("こうかとんが転んだ")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()

    bg_img = pg.image.load("fig/pg_bg.jpg")
    player = Player()
    oni = Oni()
    life = Life(num=3)
    muteki_time = 0

    while True:
        dt = clock.tick(50)
        now = pg.time.get_ticks()
        key_lst = pg.key.get_pressed()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_r:
                return "restart"

        screen.blit(bg_img, [0, 0])

        player.update(key_lst)
        oni.update()

        life.update(dt)

        screen.blit(player.image, player.rect)
        screen.blit(oni.image, oni.rect)

        # ★追加：スタミナ表示
        draw_stamina(screen, player)

        if oni.look_flag and player.move_flag:
            if now >= muteki_time:
                life.decrease()                # ライフを1減らす
                muteki_time = now + 1500

                if life.num <= 0:              # ライフが0ならゲームオーバー
                    life.draw(screen, now)
                    gameover(screen)
                    pg.display.update()
                    time.sleep(3)
                    return

        if player.rect.colliderect(oni.rect):
            life.draw(screen, now)
            clear(screen)
            pg.display.update()
            time.sleep(3)
            return

        life.draw(screen, now)

        pg.display.update()


if __name__ == "__main__":
    pg.init()
    while True:
        ret = main()
        if ret != "restart":
            break
    pg.quit()
    sys.exit()