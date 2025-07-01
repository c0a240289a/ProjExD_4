import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"  # 無敵状態かどうかを示す
        self.hyper_life = -1   # 無敵状態の残り時間

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        if key_lst[pg.K_LSHIFT]:
            self.speed = 20
        else:
            self.speed = 10
        if key_lst[pg.K_LSHIFT]:
            self.speed = 20
        else:
            self.speed = 10
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)    # 無敵状態の画像
            self.hyper_life -= 1    # 無敵状態の残り時間を1フレーム分減少
            if self.hyper_life < 0:   # 無敵状態の時間が0未満になったかチェック
                self.state = "normal"    # 状態を通常状態に戻す
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"  # 爆弾の状態

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    """
    • Beamクラスのイニシャライザの引数に回転角度angle0（デフォルトで0）を追加し，ビームの回転角度に加算する
    """
    def __init__(self, bird: Bird,angle0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.angle0 = angle0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle+self.angle0, 1.0)
        self.vx = math.cos(math.radians(angle+self.angle0))
        self.vy = -math.sin(math.radians(angle+self.angle0))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam:
    """
    NeoBeamクラスのイニシャライザの引数を，こうかとんbirdとビーム数numとする

    """
    def __init__(self, bird: Bird,num):
        self.beams= []
        self.beamnum=num
        self.bird =bird

    def gen_beams(self):
        """
        NeoBeamクラスのgen_beamsメソッドで，‐50°～+51°の角度の範囲で指定ビーム数の分だけBeamインスタンスを生成し，リストにappendする → リストを返す
        """
        for i in range(-50, +51, int(100/(self.beamnum-1))):
            beam = Beam(self.bird,i)
            self.beams.append(beam)
        return self.beams
class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class EMP:  # 追加部分
    """
    発動時に存在する敵機と爆弾を無効可するクラス
    敵機:爆弾投下できなくなる
    爆弾:動きが鈍くなる/ぶつかったら起爆せずに消滅する
    """
    def __init__(self,emys,bombs,screen:pg.Surface):
        for emy in emys:
            emy.interval = math.inf  # 爆弾投下不可
            emy.image = pg.transform.laplacian(emy.image)  # 見た目変更
        for bomb in bombs:    
            bomb.speed = bomb.speed/2  # スピード減速
            bomb.state = "inactive"  # 爆弾非活性化
        emp_img = pg.Surface((WIDTH, HEIGHT))  # 見た目：画面全体に透明度のある黄色の矩形を0.05秒表示
        pg.draw.rect(emp_img,(255,255,0),(0,0,WIDTH,HEIGHT))
        emp_img.set_alpha(100)
        screen.blit(emp_img,[0,0])
        pg.display.update()
        time.sleep(0.05)  # 0.05秒表示


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 10000 #初期値

        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Shield(pg.sprite.Sprite):
    """
    追加機能5:防御壁を出現させ、着弾を防ぐ
    """
    def __init__(self, bird: Bird, life=400):
        super().__init__()
        self.bird = bird
        self.life = life
        self.image = pg.Surface((20, bird.rect.height * 2))  # 幅と高さの設定
        pg.draw.rect(self.image, (0, 0, 255),pg.Rect(0, 0, 20, bird.rect.height * 2))  # 防御壁の設定

        self.vx, self.vy = self.bird.dire  # 向き
        angle = math.degrees(math.atan2(-self.vy, self.vx))  # 角度の設定
        self.image = pg.transform.rotozoom(self.image, angle, 1.0)  # 回転
        self.rect = self.image.get_rect()
        tejun6 = pg.Vector2(self.vx, self.vy) * self.bird.rect.width
        self.rect.center = self.bird.rect.center + tejun6

        self.image.set_colorkey((0, 0, 0))
        self.image = self.image.copy()


    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    shields = pg.sprite.Group()
    print(type(shields))

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:

                """
                発動条件が満たされたら，NeoBeamクラスのイニシャライザにこうかとんとビーム数を渡し，戻り値のリストをBeamグループに追加する
                """
                if key_lst[pg.K_LSHIFT] == True:
                    beams.add(NeoBeam(bird, 5).gen_beams())
                else:
                    beams.add(Beam(bird ,0))

            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if score.value >= 20:
                    EMP(emys, bombs, screen)
                    score.value -= 20
                
            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT:    #右Shiftキーが押された
                if score.value > 100 and bird.state == "normal":   # # スコア100以上と通常状態か確認
                    bird.state = "hyper"        # 無敵状態に移行
                    bird.hyper_life = 500       # 無敵状態の持続時間
                    score.value -= 100           # スコアを100消費
            if event.type == pg.KEYDOWN and event.key == pg.K_s and score.value > 50 and len(shields) == 0:  # sキーを押す かつ スコアより50大 かつ 防御壁が一つもないとき
                shield = Shield(bird)
                shields.add(shield)
                score.value -= 50
                
        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if bomb.state == "inactive":  # 爆弾が非活性か
                continue
            if bird.state == "hyper":  # 無敵状態の場合
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1  # スコア1点追加
            else:  # 通常状態の場合
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return
        
        
        for shield in pg.sprite.groupcollide(shields, bombs , True , True):  # 爆弾と衝突した防御壁リスト
            exps.add(Explosion(shield, 50))  # 爆発エフェクト


        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
 

        shields.update()
        shields.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
