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
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def draw_heart_surface(size: int, color: tuple) -> pg.Surface:
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
        self.num = num
        self._hearts: list[pg.Surface] = []
        self._build_hearts()
        self._kakera: list[dict] = []

    def _build_hearts(self):
        self._hearts = []
        for _ in range(self.num):
            if self.num == 3:
                color = (220, 30, 60)
            elif self.num == 2:
                color = (255, 140, 0)
            else:
                color = (255, 50, 50)
            self._hearts.append(draw_heart_surface(self.HEART_SIZE, color))

    def decrease(self):
        if self.num > 0:
            self._spawn_kakera()
            self.num -= 1
            self._build_hearts()

    def _spawn_kakera(self):
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
                "life": random.randint(20, 40),
                "color": (
                    random.randint(180, 255),
                    random.randint(0, 60),
                    random.randint(0, 60),
                ),
                "size": random.randint(3, 8),
            })

    def update(self, dt: int):
        for p in self._kakera:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.3
            p["life"] -= 1
        self._kakera = [p for p in self._kakera if p["life"] > 0]

    def draw(self, screen: pg.Surface, now: int):
        blink_visible = True
        if self.num == 1 and (now // 250) % 2 == 0:
            blink_visible = False

        for i, heart in enumerate(self._hearts):
            x = WIDTH - 50 - i * (self.HEART_SIZE + 8) - self.HEART_SIZE // 2
            y = HEIGHT - 50 - self.HEART_SIZE // 2

            if i == self.num - 1 and not blink_visible:
                continue
            screen.blit(heart, (x, y))

        for p in self._kakera:
            pg.draw.circle(screen, p["color"], (int(p["x"]), int(p["y"])), p["size"])


class Player(pg.sprite.Sprite):
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
        self.rect.center = (50, HEIGHT // 2)

        self.normal_speed = 1
        self.dash_speed = 3
        self.speed = self.normal_speed

        self.stamina = 100
        self.max_stamina = 100
        
        self.move_flag = False
        self.walk_se = pg.mixer.Sound("sound/asioto.mp3")

    def update(self, key_lst: list[bool], obstacles: pg.sprite.Group):
        """
        プレイヤー更新
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]

        moving = (sum_mv != [0, 0])

        if key_lst[pg.K_LSHIFT] and self.stamina > 0:
            self.speed = self.dash_speed
            self.stamina -= 1
        else:
            self.speed = self.normal_speed
            if not moving:
                self.stamina += 0.2

        self.stamina = max(0, min(self.stamina, self.max_stamina))

        # self.rect.move_ip(self.speed * sum_mv[0], self.speed * sum_mv[1])

        # if check_bound(self.rect) != (True, True):
        #     self.rect.move_ip(-self.speed * sum_mv[0], -self.speed * sum_mv[1])

        # if moving:
        actually_moved = False  # 実際に移動できたかを追跡する変数

        # めり込み防止チェック------------------------------
        # X方向の移動と衝突判定
        if sum_mv[0] != 0:
            self.rect.x += self.speed * sum_mv[0] # 先に仮移動させる
            if check_bound(self.rect)[0] is False or pg.sprite.spritecollideany(self, obstacles):   #もし画面外に出るか遮蔽物にぶつかるなら
                self.rect.x -= self.speed * sum_mv[0] # 引き戻された
            else:
                actually_moved = True # 引き戻されずに動ける

        # Y方向の移動と衝突判定
        if sum_mv[1] != 0:
            self.rect.y += self.speed * sum_mv[1] # 先に仮移動させる
            if check_bound(self.rect)[1] is False or pg.sprite.spritecollideany(self, obstacles):   #もし画面外に出るか遮蔽物にぶつかるなら
                self.rect.y -= self.speed * sum_mv[1] # 引き戻された
            else:
                actually_moved = True # 引き戻されずに動ける
        #-----------------------------------------------

        # 移動判定（キーが押されていて、かつ実際に動けた場合のみTrue）
        if moving and actually_moved:
            self.move_flag = True
            if not self.walk_se.get_num_channels():
                self.walk_se.play(-1)
        else:
            self.move_flag = False
            # 足音停止
            self.walk_se.stop()


class Obstacle(pg.sprite.Sprite):
    """
    遮蔽物に関するクラス
    """
    WIDTH = 30
    HEIGHT = 120
    BLOCK_IMAGE = None  # 初期化時は空にしておき、mainでロード

    def __init__(self, x: int, y: int):
        super().__init__()
        self.image = Obstacle.BLOCK_IMAGE
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

class Oni(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image_back = pg.image.load("fig/2.png")
        self.image_front = pg.transform.flip(self.image_back, True, False)
        self.image = self.image_back
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH - 50, HEIGHT // 2)

        # 開始時
        self.look_flag = False
        self.next_turn = time.time() + random.uniform(5, 15)

        self.voice = pg.mixer.Sound("sound/sound.mp3")
        self.voice.play(-1)

        # 前回の配置座標を記憶するリスト
        self.prev_positions = []

    def generate_obstacles(self, obstacles_group: pg.sprite.Group):
        """
        ランダムな遮蔽物を生成する
        """
        obstacles_group.empty()  # 古いブロックをすべて消す
        new_positions = []

        # 個数は1〜3個
        num_obstacles = random.randint(1, 3)

        attempts = 0
        while len(new_positions) < num_obstacles and attempts < 100:    #もし100回試しても条件を満たす配置ができない時はあきらめる

            #出現エリアを 200 ～ 900 に制限
            x = random.randint(200, 900 - 30)
            #出現エリアを 50 ～ 480 に制限
            y = random.randint(50, HEIGHT - 120 - 50)

            # 密集・閉じ込め防止
            too_close = False
            for nx, ny in new_positions:
                if abs(nx - x) < 120 and abs(ny - y) < 180: #ブロック同士がxが120px以上,yは180px以上離れている
                    too_close = True
                    break

            # 1つ前の遮蔽物出現場所から120px以上離す
            for px, py in self.prev_positions:
                if abs(px - x) < 120 and abs(py - y) < 120:
                    too_close = True
                    break

            if not too_close:
                new_positions.append((x, y))
                obs = Obstacle(x, y)
                obstacles_group.add(obs)

        # 今回の配置を次回の1つ前の場所として記憶する
        self.prev_positions = new_positions

    def update(self, obstacles_group: pg.sprite.Group, n:int, turn_min:int, turn_max: int):
        """
        鬼更新
        """
        now = time.time()

        if not self.look_flag:
            # ランダム時間経過で振り向く
            if now >= self.next_turn:
                self.look_flag = True
                self.image = self.image_front
                self.voice.stop()
                self.next_turn = now + n #stageごとの難易度
        else:
            if now >= self.next_turn:
                self.look_flag = False
                self.image = self.image_back

                # 後ろを向いたら遮蔽物をリフレッシュ
                self.generate_obstacles(obstacles_group)

                # 音声再生
                self.voice.play(-1)
                self.next_turn = now + random.uniform(turn_min, turn_max) #stageごとの難易度


#爆弾クラスの追加
class Bomb(pg.sprite.Sprite):
    def __init__(self, life:int):
        super().__init__()
        rad = 40
        self.image = pg.Surface((2*rad, 2*rad))
        pg.draw.circle(self.image,(255,0,0),(rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.image.set_alpha(200)
        self.rect = self.image.get_rect()
        centerx = random.randint(0,WIDTH)
        centery = random.randint(0,HEIGHT)
        self.rect.center = centerx, centery
        self.life = life
        
    def update(self, player):
        self.life -= 1
        if self.life <= 0:
            if self.rect.colliderect(player.rect):
                return "boom"
            self.kill()
        elif self.life <= 3:
            self.image.set_alpha(255)
        elif self.life %30 >= 15:
            self.image.set_alpha(0)
        else:
            self.image.set_alpha(120)
            

def check_hidden(player: Player, obstacles: pg.sprite.Group) -> bool:
    """
    隠れ判定のルール（上下35px以上重なっていればセーフ）
    """
    REQUIRED_OVERLAP = 35  # プレイヤーの体のうち、縦に35ピクセル以上が遮蔽物の高さの中に収まっていればセーフ

    for obs in obstacles:
        # プレイヤーが遮蔽物より左側にいる
        if player.rect.right >= obs.rect.left:
            continue

        # 上下の重なり合っている部分の高さを求める
        overlap_top = max(player.rect.top, obs.rect.top)
        overlap_bottom = min(player.rect.bottom, obs.rect.bottom)

        # 重なりの高さを計算（プラスなら重なっている）
        overlap_height = overlap_bottom - overlap_top

        # 指定したピクセル数以上重なっていればセーフ
        if overlap_height >= REQUIRED_OVERLAP:
            return True  # 1つでも条件を満たすブロックがあればセーフ

    return False  # どのブロックの影にも隠れられていなければアウト


def draw_text(
    screen: pg.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    center: tuple[int, int],
):
    """
    文字表示
    """
    font = pg.font.Font(None, size)
    txt = font.render(text, True, color)
    rect = txt.get_rect()
    rect.center = center
    screen.blit(txt, rect)


def gameover(screen):
    fonto = pg.font.Font(None, 80)
    txt = fonto.render("Game Over", True, (255, 0, 0))
    screen.blit(txt, [WIDTH // 2 - 150, HEIGHT // 2])

def clear(screen):
    fonto = pg.font.Font(None, 80)
    txt = fonto.render("Clear!", True, (0, 255, 0))
    screen.blit(txt, [WIDTH // 2 - 150, HEIGHT // 2])

def draw_stamina(screen: pg.Surface, player: Player):
    pg.draw.rect(screen, (255, 255, 255), [20, 20, 200, 20])
    pg.draw.rect(screen, (0, 255, 0), [20, 20, player.stamina * 2, 20])
    pg.draw.rect(screen, (0, 0, 0), [20, 20, 200, 20], 2)
    draw_text(screen, "STAMINA", 30, (255, 255, 255), (120, 55))


n = 3
turn_min = 5
turn_max = 15
def main():
    pg.display.set_caption("こうかとんが転んだ")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()
    bg_img = pg.image.load("fig/pg_bg.jpg")
    loaded_img = pg.image.load("fig/block.png")
    Obstacle.BLOCK_IMAGE = pg.transform.scale(
        loaded_img, (Obstacle.WIDTH, Obstacle.HEIGHT)
    )
    player = Player()
    oni = Oni()
    life = Life(num=3)
    bombs = pg.sprite.Group()
    bomb_time = 0
    muteki_time = 0

    # 時間停止スキル
    stop_time = 0
    cooldown_end = 0
    STOP_DURATION = 3
    COOLDOWN = 5

    start_time = time.time()

    obstacles = pg.sprite.Group()       # 遮蔽物を管理するグループ
    oni.generate_obstacles(obstacles)   # 初回スタート時の遮蔽物生成

    while True:
        dt = clock.tick(50)
        now = pg.time.get_ticks()
        key_lst = pg.key.get_pressed()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_r:
                return "restart"

            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                t = time.time()
                if t >= cooldown_end:
                    stop_time = t + STOP_DURATION
                    cooldown_end = t + COOLDOWN

        screen.blit(bg_img, [0, 0])
        player.update(key_lst, obstacles)
        
        t = time.time()
        if t >= stop_time:
            oni.update(obstacles, n, turn_min, turn_max)

        life.update(dt)

        # 描画
        obstacles.draw(screen)
        screen.blit(player.image, player.rect)
        screen.blit(oni.image, oni.rect)
        
        if n>=4: #1回クリア後、爆弾が現れる
            bomb_time += 1
            if bomb_time %500 == 0:
                for bomb in range(n+2):
                    bombs.add(Bomb(200))
                    pg.display.update()
            
            for bomb in bombs:
                crash = bomb.update(player)
                screen.blit(bomb.image, bomb.rect)
                if crash == "boom":
                    gameover(screen)
                    pg.display.update()
                    time.sleep(3)
                    return

        # 経過時間
        elapsed = int(time.time() - start_time)
        draw_text(screen, f"Time: {elapsed}", 40, (255, 255, 255), (100, 30))

        # クールタイム
        cd = max(0, int(cooldown_end - time.time()))
        draw_text(screen, f"Skill CD: {cd}", 40, (255, 255, 0), (300, 30))

        # 経過時間
        elapsed = int(time.time() - start_time)
        draw_text(screen, f"Time: {elapsed}", 40, (255, 255, 255), (100, 30))

        # クールタイム
        cd = max(0, int(cooldown_end - time.time()))
        draw_text(screen, f"Skill CD: {cd}", 40, (255, 255, 0), (300, 30))
        draw_stamina(screen, player)
        
        if n>=4: #1回クリア後、爆弾が現れる
            bomb_time += 1
            if bomb_time %500 == 0:
                for bomb in range(n+2):
                    bombs.add(Bomb(200))
                    pg.display.update()
            
            for bomb in bombs:
                crash = bomb.update(player)
                screen.blit(bomb.image, bomb.rect)
                if crash == "boom":
                    gameover(screen)
                    pg.display.update()
                    time.sleep(3)
                    return

        # ゲームオーバー判定
        if oni.look_flag and player.move_flag:
            # 遮蔽物の後ろに完全に隠れていればセーフ
            if not check_hidden(player, obstacles):
                if now >= muteki_time:
                    life.decrease()
                    muteki_time = now + 1500

                    if life.num <= 0:
                        life.draw(screen, now)
                        gameover(screen)
                        pg.display.update()
                        time.sleep(3)
                        return

        # クリア判定
        if player.rect.colliderect(oni.rect):
            life.draw(screen, now)
            clear(screen)
            pg.display.update()
            time.sleep(3)
            return "clear"

        life.draw(screen, now)
        pg.display.update()


if __name__ == "__main__":
    pg.init()
    while True:
        ret = main()
        if ret == "clear": #追加
            n += 1
            if turn_min > 1:
                turn_max -= 2
                turn_min -= 1
        elif ret != "restart":
            break
    pg.quit()
    sys.exit()