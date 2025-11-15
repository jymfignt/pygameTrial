import pygame
import math
pygame.init()

#initialize
screen_width, screen_height = 1408, 704
block_size = 64
max_level = 5
screen = pygame.display.set_mode((screen_width, screen_height))
# 使用系统中文字体
font = pygame.font.SysFont('microsoftyahei', 80)  # 分数字体
small_font = pygame.font.SysFont('microsoftyahei', 24)  # 小文字
medium_font = pygame.font.SysFont('microsoftyahei', 32)  # 中等文字
large_font = pygame.font.SysFont('microsoftyahei', 48)  # 大标题
show_score = 0
curr_score = 0

# 游戏状态
class GameState:
    MENU = 0
    PLAYING = 1
    WIN = 2

# 难度设置
class Difficulty:
    BEGINNER = {"name": "新手", "target": 500, "show_tutorial": True}
    EASY = {"name": "初级", "target": 1000, "show_tutorial": False}
    MEDIUM = {"name": "中级", "target": 2000, "show_tutorial": False}
    HARD = {"name": "高级", "target": 5000, "show_tutorial": False}

game_state = GameState.MENU
current_difficulty = None
click_count = 0
start_time = 0
win_sound_played = False  # 标记是否已播放通关音效

# 烟花粒子类
class Firework:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.particles = []
        self.exploded = False
        self.speed_y = -8
        self.gravity = 0.15
        self.color = (255, 255, 255)
        
    def update(self, delta_time):
        if not self.exploded:
            # 上升阶段
            self.speed_y += self.gravity
            self.y += self.speed_y
            
            # 到达顶点时爆炸
            if self.speed_y >= 0:
                self.explode()
        else:
            # 更新粒子
            for particle in self.particles[:]:
                particle['x'] += particle['vx']
                particle['y'] += particle['vy']
                particle['vy'] += 0.1  # 重力
                particle['life'] -= 1
                particle['size'] = max(1, particle['size'] - 0.05)
                
                if particle['life'] <= 0:
                    self.particles.remove(particle)
    
    def explode(self):
        self.exploded = True
        # 随机颜色
        colors = [
            (255, 50, 50),   # 红色
            (50, 255, 50),   # 绿色
            (50, 50, 255),   # 蓝色
            (255, 255, 50),  # 黄色
            (255, 50, 255),  # 紫色
            (50, 255, 255),  # 青色
            (255, 150, 50),  # 橙色
        ]
        import random
        self.color = random.choice(colors)
        
        # 创建更多粒子，更大的爆炸范围
        for i in range(80):
            angle = (i / 80) * 2 * 3.14159
            speed = random.uniform(3, 8)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'vx': speed * math.cos(angle),
                'vy': speed * math.sin(angle),
                'life': random.randint(40, 80),
                'color': self.color,
                'size': random.uniform(3, 6)
            })
    
    def draw(self, screen):
        if not self.exploded:
            # 绘制上升的火箭（更明显）
            pygame.draw.circle(screen, (255, 255, 200), (int(self.x), int(self.y)), 5)
            # 添加尾迹
            pygame.draw.circle(screen, (255, 200, 100), (int(self.x), int(self.y + 10)), 3)
        else:
            # 绘制爆炸粒子
            for particle in self.particles:
                color = particle['color']
                size = max(1, int(particle['size']))
                pos = (int(particle['x']), int(particle['y']))
                pygame.draw.circle(screen, color, pos, size)
    
    def is_finished(self):
        return self.exploded and len(self.particles) == 0

# 烟花列表
fireworks = []
firework_timer = 0

# 新手指引状态
tutorial_step = 0
tutorial_messages = [
    "欢迎！点击屏幕发射方块",
    "按 A/D 键左右移动方块",
    "相同数字合并升级",
    "3个64连成一线可消除！"
]

# 加载并缩放图片
scaled_image = pygame.transform.scale(pygame.image.load('pic/block.png'), (block_size, block_size))
back_image = pygame.transform.scale(pygame.image.load('pic/back.png'), (block_size, block_size))
images = []
for x in [2, 4, 8, 16, 32, 64]:
    image = pygame.transform.scale(pygame.image.load('pic/blocknum/%d.png' % x), (block_size, block_size))
    images.append(image)

# 默认背景图片
default_background = pygame.transform.scale(pygame.image.load('pic/background.png'), (screen_width//2, screen_height))
back_ground = default_background
custom_background_path = None

class MoveState:
    FREE = 0  # 自由落体
    MOVE = 1  # 移动到目标位置 
    STAY = 2  # 静止
    FALL = 3  # 下落状态
    TRIP = 4  # 三消逻辑

class SoundIdx:
    COMBINE = 0
    SHIFT = 1
    SHOOT = 2
    BOMB = 3
    TRIP = 4
    CONGRATULATION = 5
    MAX = 6
SOUNDS = []
for i in range(0, SoundIdx.MAX - 1):  # 0-4 是数字命名的音效
    sound = pygame.mixer.Sound('snd/%d.MP3' % i)
    SOUNDS.append(sound)
# 加载通关音效
try:
    congratulation_sound = pygame.mixer.Sound('snd/congratulation.mp3')
    SOUNDS.append(congratulation_sound)
    print("通关音效加载成功")  # 调试信息
except Exception as e:
    print(f"加载通关音效失败: {e}")
    print("请确保 snd/congratulation.mp3 文件存在")
    SOUNDS.append(None)  # 占位，避免索引错误

class Block:
    def __init__(self, pos, target_pos, level, speed):
        self.level = level
        self.image = images[self.level]
        self.rect = self.image.get_rect(center=pos)
        self.speed = speed
        self.acc = [0, 0.0002]
        self.pos = list(pos)
        self.move_state = MoveState.FREE
        self.locked = False
        
        # 计算初始速度矢量
        rad = self.calc_degree(pos, target_pos)
        self.speed[0] += 0.3 * math.cos(rad)
        self.speed[1] += 0.3 * math.sin(rad)

    def update_movement(self, delta_time):
        if self.move_state == MoveState.FREE:  # 仅活动方块需要更新物理运动
            self.speed[0] += self.acc[0] * delta_time
            self.speed[1] += self.acc[1] * delta_time
            self.pos[0] += self.speed[0] * delta_time
            self.pos[1] += self.speed[1] * delta_time
            self.rect.center = self.pos
        elif self.move_state == MoveState.MOVE:
            self.pos[0] += (self.target_pos[0] - self.pos[0]) / 5
            self.pos[1] += (self.target_pos[1] - self.pos[1]) / 5
            if abs(self.target_pos[0] - self.pos[0]) < 1 and abs(self.target_pos[1] - self.pos[1]) < 1:
                self.pos = self.target_pos
                self.move_state = MoveState.STAY
                self.locked = False
            self.rect.center = self.pos
        elif self.move_state == MoveState.FALL:
            self.pos[0] += (self.target_pos[0] - self.pos[0]) / 5
            self.speed[1] += self.acc[1] * delta_time
            self.pos[1] += self.speed[1] * delta_time
            if self.pos[1] > self.target_pos[1]:
                self.pos = self.target_pos
                self.move_state = MoveState.STAY
                self.locked = False
            self.rect.center = self.pos
        elif self.move_state == MoveState.TRIP:
            self.pos[0] -= delta_time / 10
            self.pos[1] += 5*(2.5-self.run_time)
            self.run_time -= delta_time/1000.0
            
            if self.run_time < 0:
                self.move_state = MoveState.STAY
                self.locked = False
            self.rect.center = self.pos
    
    def set_move_state(self, move_state, grid_pos = None, run_time = None):
        self.move_state = move_state
        self.grid_pos = grid_pos
        self.run_time = run_time
        if grid_pos:
            target_x = grid_pos[1]*block_size+block_size//2 + screen_width//2
            target_y = grid_pos[0]*block_size+block_size//2
            self.target_pos = [target_x, target_y]
        
    def calc_degree(self, ori, tar):
        dx = tar[0] - ori[0]
        dy = tar[1] - ori[1]
        return math.atan2(dy, dx) if dx or dy else math.atan2(1, 0)

    def is_horizontal_collision(self, received):
        dx = min(self.rect.right, received.rect.right) - max(self.rect.left, received.rect.left)
        dy = min(self.rect.bottom, received.rect.bottom) - max(self.rect.top, received.rect.top)
        return dx <= dy

    def set_lock(self, locked):
        self.locked = locked
    
    def level_up(self):
        if self.locked:
            return False
        if self.level < 5:
            self.level += 1
            self.image = images[self.level]
            return True
        return False

def draw_button(text, rect, color, hover_color, mouse_pos):
    is_hover = rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, hover_color if is_hover else color, rect, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), rect, 3, border_radius=10)
    text_surface = medium_font.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    return is_hover

def draw_menu():
    screen.fill((30, 30, 50))
    
    # 标题
    title = large_font.render("选择难度", True, (255, 255, 255))
    title_rect = title.get_rect(center=(screen_width//2, 100))
    screen.blit(title, title_rect)
    
    # 自定义背景按钮
    mouse_pos = pygame.mouse.get_pos()
    bg_button_rect = pygame.Rect(screen_width//2 - 150, 160, 300, 50)
    bg_text = "点击上传自定义背景图" if not custom_background_path else "已上传自定义背景"
    bg_color = (50, 120, 50) if custom_background_path else (60, 60, 100)
    bg_hover_color = (70, 140, 70) if custom_background_path else (80, 80, 120)
    is_bg_hover = draw_button(bg_text, bg_button_rect, bg_color, bg_hover_color, mouse_pos)
    
    # 显示提示文字
    tip_text = small_font.render("支持 PNG, JPG, BMP 格式", True, (180, 180, 180))
    tip_rect = tip_text.get_rect(center=(screen_width//2, 220))
    screen.blit(tip_text, tip_rect)
    
    # 难度按钮
    difficulties = [
        (Difficulty.BEGINNER, (screen_width//2 - 150, 260, 300, 60)),
        (Difficulty.EASY, (screen_width//2 - 150, 340, 300, 60)),
        (Difficulty.MEDIUM, (screen_width//2 - 150, 420, 300, 60)),
        (Difficulty.HARD, (screen_width//2 - 150, 500, 300, 60))
    ]
    
    clicked_difficulty = None
    for diff, rect_tuple in difficulties:
        rect = pygame.Rect(rect_tuple)
        button_text = f"{diff['name']} (目标: {diff['target']}分)"
        is_hover = draw_button(button_text, rect, (60, 60, 100), (80, 80, 120), mouse_pos)
        if is_hover and pygame.mouse.get_pressed()[0]:
            clicked_difficulty = diff
    
    return clicked_difficulty, is_bg_hover

def draw_win_screen():
    # 半透明遮罩
    overlay = pygame.Surface((screen_width, screen_height))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # 胜利窗口
    win_rect = pygame.Rect(screen_width//2 - 300, screen_height//2 - 200, 600, 400)
    pygame.draw.rect(screen, (50, 50, 80), win_rect, border_radius=20)
    pygame.draw.rect(screen, (255, 215, 0), win_rect, 5, border_radius=20)
    
    # 文字
    congrats = large_font.render("恭喜通关！", True, (255, 215, 0))
    congrats_rect = congrats.get_rect(center=(screen_width//2, screen_height//2 - 100))
    screen.blit(congrats, congrats_rect)
    
    score_text = medium_font.render(f"最终分数: {int(show_score)}", True, (255, 255, 255))
    score_rect = score_text.get_rect(center=(screen_width//2, screen_height//2 - 20))
    screen.blit(score_text, score_rect)
    
    click_text = medium_font.render(f"点击次数: {click_count}", True, (255, 255, 255))
    click_rect = click_text.get_rect(center=(screen_width//2, screen_height//2 + 40))
    screen.blit(click_text, click_rect)
    
    # 返回按钮
    mouse_pos = pygame.mouse.get_pos()
    return_rect = pygame.Rect(screen_width//2 - 100, screen_height//2 + 120, 200, 60)
    return draw_button("返回菜单", return_rect, (60, 60, 100), (80, 80, 120), mouse_pos)

def draw_tutorial():
    if tutorial_step >= len(tutorial_messages):
        return
    
    # 提示框
    tip_rect = pygame.Rect(50, screen_height - 100, 500, 80)
    pygame.draw.rect(screen, (50, 50, 80), tip_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 215, 0), tip_rect, 3, border_radius=10)
    
    tip_text = small_font.render(tutorial_messages[tutorial_step], True, (255, 255, 255))
    tip_text_rect = tip_text.get_rect(center=tip_rect.center)
    screen.blit(tip_text, tip_text_rect)

def load_custom_background(filepath):
    """加载自定义背景图片"""
    global back_ground, custom_background_path
    try:
        # 加载图片
        img = pygame.image.load(filepath)
        # 缩放到左侧区域大小
        back_ground = pygame.transform.scale(img, (screen_width//2, screen_height))
        custom_background_path = filepath
        return True
    except Exception as e:
        print(f"加载背景图片失败: {e}")
        return False

def open_file_dialog():
    """打开文件选择对话框"""
    import tkinter as tk
    from tkinter import filedialog
    
    # 创建一个隐藏的tkinter窗口
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    # 打开文件选择对话框
    filepath = filedialog.askopenfilename(
        title="选择背景图片",
        filetypes=[
            ("图片文件", "*.png *.jpg *.jpeg *.bmp"),
            ("PNG文件", "*.png"),
            ("JPG文件", "*.jpg *.jpeg"),
            ("BMP文件", "*.bmp"),
            ("所有文件", "*.*")
        ]
    )
    
    root.destroy()
    return filepath

def reset_game():
    global active_blocks, received_blocks, back_blocks, remove_blocks
    global show_score, curr_score, click_count, tutorial_step, win_sound_played
    global fireworks, firework_timer
    
    active_blocks = []
    received_blocks = {}
    back_blocks = {}
    remove_blocks = {}
    show_score = 0
    curr_score = 0
    click_count = 0
    tutorial_step = 0
    win_sound_played = False  # 重置通关音效标记
    fireworks = []  # 清空烟花
    firework_timer = 0
    
    for i in range(screen_height//block_size):
        for j in range(screen_width//2//block_size):
            rect = pygame.rect.Rect(screen_width//2 + j*block_size, i*block_size, block_size, block_size)
            back_blocks[(i,j)] = rect
            received_blocks[(i, j)] = None

# 初始化游戏
reset_game()
    
running = True
clock = pygame.time.Clock()
delta_time = 0
waiting_for_click_release = False  # 防止按钮连击

while running:
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # 菜单状态
        elif game_state == GameState.MENU:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                selected_diff, is_bg_clicked = draw_menu()
                
                # 点击上传背景按钮
                if is_bg_clicked and not waiting_for_click_release:
                    waiting_for_click_release = True
                    filepath = open_file_dialog()
                    if filepath:
                        load_custom_background(filepath)
                
                # 点击难度按钮
                elif selected_diff and not waiting_for_click_release:
                    current_difficulty = selected_diff
                    game_state = GameState.PLAYING
                    reset_game()
                    start_time = pygame.time.get_ticks()
                    waiting_for_click_release = True
            
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                waiting_for_click_release = False
        
        # 胜利状态
        elif game_state == GameState.WIN:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if draw_win_screen() and not waiting_for_click_release:
                    game_state = GameState.MENU
                    waiting_for_click_release = True
            
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                waiting_for_click_release = False
        
        # 游戏进行中
        elif game_state == GameState.PLAYING:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                import random
                level = random.randint(0, 2)
                SOUNDS[SoundIdx.SHOOT].play()
                click_count += 1
                
                # 新手指引进度
                if current_difficulty["show_tutorial"]:
                    if tutorial_step == 0:
                        tutorial_step = 1
                
                for i in range(10):
                    speed = [0.1 + i/20, -0.3 - i/30]
                    active_blocks.append(Block([0, screen_height], mouse_pos, level, speed))
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d:
                    SOUNDS[SoundIdx.SHIFT].play()
                    
                    # 新手指引进度
                    if current_difficulty["show_tutorial"] and tutorial_step == 1:
                        tutorial_step = 2
                    
                    # 处理右移逻辑
                    max_col = (screen_width // 2) // block_size
                    max_row = screen_height // block_size
                    for i in range(max_row):
                        last_col = max_col-1
                        for j in range(max_col-1, -1, -1):
                            rb = received_blocks.get((i, j))
                            if not rb:
                                continue
                            if j == last_col:
                                last_col -= 1
                                continue
                            rb.set_move_state(MoveState.MOVE, (i, last_col))
                            received_blocks[(i, last_col)] = rb
                            received_blocks[(i, j)] = None
                            last_col -= 1
                            
                elif event.key == pygame.K_a:
                    SOUNDS[SoundIdx.SHIFT].play()
                    
                    # 新手指引进度
                    if current_difficulty["show_tutorial"] and tutorial_step == 1:
                        tutorial_step = 2
                    
                    # 处理左移逻辑
                    max_col = (screen_width // 2) // block_size
                    max_row = screen_height // block_size
                    for i in range(max_row):
                        last_col = 0
                        for j in range(max_col):
                            rb = received_blocks.get((i, j))
                            if not rb:
                                continue
                            if j == last_col:
                                last_col += 1
                                continue
                            rb.set_move_state(MoveState.MOVE, (i, last_col))
                            received_blocks[(i, last_col)] = rb
                            received_blocks[(i, j)] = None
                            last_col += 1

    # 绘制界面
    if game_state == GameState.MENU:
        draw_menu()
    
    elif game_state == GameState.WIN:
        # 继续显示游戏画面
        screen.fill((0, 0, 0))
        screen.blit(back_ground, back_ground.get_rect())
        for (i,j), rect in back_blocks.items():
            screen.blit(back_image, rect)
        for block in active_blocks:
            screen.blit(block.image, block.rect)
        for ij, block in received_blocks.items():
            if block:
                screen.blit(block.image, block.rect)
        for ij, block in remove_blocks.items():
            if block:
                screen.blit(block.image, block.rect)
        
        text_surface = font.render(str(int(show_score)), True, (255,255,255))
        text_rect = text_surface.get_rect()
        text_rect.x = 10
        text_rect.y = 10
        screen.blit(text_surface, text_rect)
        
        # 先绘制通关窗口
        draw_win_screen()
        
        # 更新和绘制烟花（在通关窗口之上）
        import random
        firework_timer += delta_time
        if firework_timer > 500:  # 每500毫秒发射一个烟花
            firework_timer = 0
            x = random.randint(200, screen_width - 200)
            y = screen_height - 50
            fireworks.append(Firework(x, y))
        
        # 更新所有烟花
        for firework in fireworks[:]:
            firework.update(delta_time)
            if firework.is_finished():
                fireworks.remove(firework)
        
        # 绘制烟花（在最上层）
        for firework in fireworks:
            firework.draw(screen)
    
    elif game_state == GameState.PLAYING:
        screen.fill((0, 0, 0))

        # 临时存储需要转移的方块
        to_receive = []
        
        # 更新活动方块
        for block in active_blocks[:]:
            block.update_movement(delta_time)
            
            # 保留原始边界碰撞逻辑
            if block.rect.right > screen_width:
                block.speed[0] = -abs(block.speed[0])
                SOUNDS[SoundIdx.BOMB].play()
            if block.rect.left < 0:
                block.speed[0] = abs(block.speed[0])
            if block.rect.top < 0:
                block.speed[1] = abs(block.speed[1])
                SOUNDS[SoundIdx.BOMB].play()
        
            block_x = (block.rect.center[0]-screen_width//2)//block_size
            block_y = block.rect.center[1]//block_size
            
            # 下边界接收条件（保持原始逻辑）
            if block.rect.bottom > screen_height and block.rect.x > screen_width/2:
                block.set_move_state(MoveState.MOVE, (block_y, block_x))
                to_receive.append(block)
                SOUNDS[SoundIdx.BOMB].play()
            else:
                collid = False
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        bk = received_blocks.get((block_y+dy, block_x+dx), None)
                        if bk and block.rect.colliderect(bk.rect):
                            if block_x >= 0:
                                block.set_move_state(MoveState.MOVE, (block_y, block_x))
                                to_receive.append(block)
                            else:
                                block.speed[0] = 0

        # 转移符合条件的方块
        for block in to_receive:
            if block in active_blocks:
                active_blocks.remove(block)
                received_blocks[block.grid_pos] = block
        
        # 处理下落逻辑
        max_col = (screen_width // 2) // block_size
        max_row = screen_height // block_size
        for j in range(max_col):
            last_row = max_row-1
            for i in range(max_row-1, -1, -1):
                rb = received_blocks.get((i, j))
                if not rb:
                    continue
                if i == last_row:
                    last_row -= 1
                    continue
                if rb.move_state != MoveState.FALL:
                    rb.set_move_state(MoveState.FALL, (last_row, j))
                    received_blocks[(last_row, j)] = rb
                    received_blocks[(i, j)] = None
                    last_row -= 1
        
        # 处理合成逻辑
        for j in range(max_col):
            for i in range(max_row-1, -1, -1):
                rb = received_blocks.get((i, j))
                if not rb:
                    continue
                if rb.move_state != MoveState.STAY:
                    continue
                if rb.locked:
                    continue
                if rb.level == max_level:
                    continue
                for left in [(i-1,j), (i,j-1)]:
                    lrb = received_blocks.get(left)
                    if not lrb:
                        continue
                    if lrb.move_state != MoveState.STAY:
                        continue
                    if lrb.level != rb.level:
                        continue
                    if lrb.locked:
                        continue
                    curr_score += (rb.level+1)
                    SOUNDS[SoundIdx.COMBINE].play()
                    
                    # 新手指引进度
                    if current_difficulty["show_tutorial"] and tutorial_step == 2:
                        tutorial_step = 3
                    
                    lrb.set_lock(True)
                    rb.set_lock(True)
                    lrb.set_move_state(MoveState.MOVE, (i,j))
                    remove_blocks[(i,j)] = lrb
                    received_blocks[left] = None
                    break
        
        # 处理三消逻辑（横向）
        for i in range(max_row):
            for j in range(max_col):
                rb = received_blocks.get((i, j))
                if not rb:
                    continue
                if rb.level != max_level:
                    continue
                if rb.move_state != MoveState.STAY:
                    continue
                cnt = 1
                for k in range(1, max_col-j):
                    kb = received_blocks.get((i, j+k))
                    if not kb:
                        break
                    if kb.level != max_level:
                        break
                    if kb.move_state != MoveState.STAY:
                        break
                    cnt += 1
                if cnt < 3:
                    continue
                curr_score += max_level * cnt * cnt * cnt
                SOUNDS[SoundIdx.TRIP].play()
                for k in range(cnt):
                    kb = received_blocks.get((i, j+k))
                    kb.set_move_state(MoveState.TRIP, run_time = 3)
                    remove_blocks[(i, j+k)] = kb
                    received_blocks[(i, j+k)] = None

        # 处理三消逻辑（纵向）
        for j in range(max_col):
            for i in range(max_row):
                rb = received_blocks.get((i, j))
                if not rb:
                    continue
                if rb.level != max_level:
                    continue
                if rb.move_state != MoveState.STAY:
                    continue
                cnt = 1
                for k in range(1, max_row-i):
                    kb = received_blocks.get((i+k, j))
                    if not kb:
                        break
                    if kb.level != max_level:
                        break
                    if kb.move_state != MoveState.STAY:
                        break
                    cnt += 1
                if cnt < 3:
                    continue
                curr_score += max_level * cnt * cnt * cnt
                SOUNDS[SoundIdx.TRIP].play()
                for k in range(cnt):
                    kb = received_blocks.get((i+k, j))
                    kb.set_move_state(MoveState.TRIP, run_time = 3)
                    remove_blocks[(i+k, j)] = kb
                    received_blocks[(i+k, j)] = None
        
        for ij, block in received_blocks.items():
            if block:
                block.update_movement(delta_time)
        
        rb_list = [(ij, block) for ij, block in remove_blocks.items()]
        for (ij, block) in rb_list:
            if block:
                block.update_movement(delta_time)
                if block.move_state == MoveState.STAY:
                    if received_blocks.get(ij):
                        received_blocks[ij].set_lock(False)
                        received_blocks[ij].level_up()
                    del remove_blocks[ij]

        screen.blit(back_ground, back_ground.get_rect()) 
        for (i,j), rect in back_blocks.items():
            screen.blit(back_image, rect)

        # 绘制所有方块
        for block in active_blocks:
            screen.blit(block.image, block.rect)
        for ij, block in received_blocks.items():
            if block:
                screen.blit(block.image, block.rect)
        for ij, block in remove_blocks.items():
            if block:
                screen.blit(block.image, block.rect)

        show_score += (curr_score - show_score) / 5
        text_surface = font.render(str(int(show_score)), True, (255,255,255))
        text_rect = text_surface.get_rect()
        text_rect.x = 10
        text_rect.y = 10
        screen.blit(text_surface, text_rect)
        
        # 显示目标分数和点击次数
        target_text = small_font.render(f"目标: {current_difficulty['target']}", True, (255, 255, 255))
        screen.blit(target_text, (10, 200))
        
        click_text = small_font.render(f"点击: {click_count}", True, (255, 255, 255))
        screen.blit(click_text, (10, 240))
        
        # 显示新手指引
        if current_difficulty["show_tutorial"]:
            draw_tutorial()
        
        # 检查是否达到目标分数
        if curr_score >= current_difficulty['target'] and game_state != GameState.WIN:
            # 播放通关音效（只播放一次）
            if not win_sound_played:
                if SOUNDS[SoundIdx.CONGRATULATION]:
                    SOUNDS[SoundIdx.CONGRATULATION].play()
                    print("播放通关音效")  # 调试信息
                else:
                    print("通关音效文件未加载")  # 调试信息
                win_sound_played = True
            game_state = GameState.WIN

    pygame.display.flip()
    delta_time = clock.tick(60)

pygame.quit()
