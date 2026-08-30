import pygame, random, time, os, requests, math
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 500, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Subway Runner")

clock = pygame.time.Clock()

# --- PLAYER SETTINGS ---
LANES = [125, 250, 375]
lane_index = 1
player_base_y = 550
player_size = 50
player_x = LANES[lane_index]
target_x = player_x

player_angle = 0
target_angle = 0  # tilt only

# --- OBSTACLES ---
obstacles = []
obstacle_speed = 10
spawn_timer = 0

# --- SCORE ---
score = 0
highscore_file = "highscore.txt"
score_scale = 1.0

# --- CAMERA SHAKE ---
camera_offset = [0, 0]
shake_timer = 0
shake_amount = 0

# --- WEATHER / BACKGROUND ---
current_bg = (0, 0, 0)
target_bg = (0, 0, 0)
weather_condition = "Clear"
rain_intensity = "moderate"
wind_speed = 0.0

# --- WEATHER EFFECTS ---
rain_drops = []
snowflakes = []
clouds_far = []
clouds_near = []
storm_clouds = []
fog_strength = 0.0
lightning_timer = 0
snow_depth = 0

# --- SPEED LINES ---
speed_lines = []

# --- SOUNDS ---
try:
    THUNDER_SOUND = pygame.mixer.Sound("thunder.wav")
except:
    THUNDER_SOUND = None

def load_highscore():
    if not os.path.exists(highscore_file):
        return 0
    with open(highscore_file, "r") as f:
        return int(f.read())

def save_highscore(new_score):
    with open(highscore_file, "w") as f:
        f.write(str(new_score))

highscore = load_highscore()

# ------------- HELPERS / TWEENING ------------- #

def lerp(a, b, t):
    return a + (b - a) * t

def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)

# ------------- WEATHER SYSTEM ------------- #

def get_weather():
    API_KEY = "0b39c6510ead2820ef6e7841b1015f99"  # <- put your real key here
    CITY = "Derby,UK"
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
    try:
        data = requests.get(url, timeout=3).json()
    except Exception as e:
        print("Weather request error:", e)
        return "Clear", "moderate", 0.0

    if "weather" not in data:
        print("Weather API error:", data)
        return "Clear", "moderate", 0.0

    condition = data["weather"][0]["main"]
    desc = data["weather"][0].get("description", "").lower()
    wind = data.get("wind", {}).get("speed", 0.0)

    if "light" in desc:
        intensity = "light"
    elif "heavy" in desc or "intense" in desc:
        intensity = "heavy"
    else:
        intensity = "moderate"

    print("Weather:", condition, "| desc:", desc, "| wind:", wind)
    return condition, intensity, wind

def pick_background_color(condition):
    if condition == "Clear":
        return (135, 206, 235)
    elif condition == "Clouds":
        return (170, 180, 190)
    elif condition == "Rain":
        return (50, 50, 80)
    elif condition == "Snow":
        return (230, 235, 245)
    elif condition in ("Fog", "Mist", "Haze"):
        return (150, 150, 150)
    elif condition == "Thunderstorm":
        return (20, 20, 40)
    else:
        return (30, 30, 30)

def init_weather_effects(condition, wind):
    global rain_drops, snowflakes, clouds_far, clouds_near, storm_clouds
    global fog_strength, lightning_timer, snow_depth, wind_speed

    rain_drops = []
    snowflakes = []
    clouds_far = []
    clouds_near = []
    storm_clouds = []
    lightning_timer = 0
    snow_depth = 0
    wind_speed = wind

    if condition in ("Fog", "Mist", "Haze"):
        fog_strength = 0.5
    else:
        fog_strength = 0.0

    if condition in ("Clouds", "Rain", "Snow", "Thunderstorm"):
        for _ in range(4):
            x = random.randint(0, WIDTH)
            y = random.randint(40, 160)
            speed = random.uniform(0.2, 0.6)
            clouds_far.append([x, y, speed])
        for _ in range(4):
            x = random.randint(0, WIDTH)
            y = random.randint(10, 120)
            speed = random.uniform(0.5, 1.2)
            clouds_near.append([x, y, speed])

    if condition == "Thunderstorm":
        for _ in range(5):
            x = random.randint(0, WIDTH)
            y = random.randint(30, 140)
            speed = random.uniform(0.8, 1.5)
            storm_clouds.append([x, y, speed])

    if condition == "Snow":
        for _ in range(80):
            x = random.randint(0, WIDTH)
            y = random.randint(-HEIGHT, HEIGHT)
            speed = random.uniform(1, 3)
            snowflakes.append([x, y, speed])

# ------------- RAIN / SNOW / CLOUDS / FOG / LIGHTNING ------------- #

def spawn_rain():
    if rain_intensity == "light":
        count = 3
    elif rain_intensity == "heavy":
        count = 12
    else:
        count = 7
    for _ in range(count):
        x = random.randint(0, WIDTH)
        y = random.randint(-50, 0)
        speed = random.randint(10, 20)
        rain_drops.append([x, y, speed])

def draw_rain():
    for drop in rain_drops:
        drop[0] += wind_speed * 0.3
        drop[1] += drop[2]
        pygame.draw.line(
            screen, (180, 180, 255),
            (drop[0] + camera_offset[0], drop[1] + camera_offset[1]),
            (drop[0] + camera_offset[0], drop[1] + 10 + camera_offset[1]),
            2
        )
    rain_drops[:] = [d for d in rain_drops if d[1] < HEIGHT]

def spawn_snow():
    for _ in range(2):
        x = random.randint(0, WIDTH)
        y = random.randint(-50, 0)
        speed = random.uniform(1, 3)
        snowflakes.append([x, y, speed])

def draw_snow():
    global snow_depth
    for flake in snowflakes:
        flake[0] += wind_speed * 0.2 + random.uniform(-0.5, 0.5)
        flake[1] += flake[2]
        if flake[1] >= HEIGHT - 40 - snow_depth:
            snow_depth = min(snow_depth + 0.2, 80)
        else:
            pygame.draw.circle(
                screen, (255, 255, 255),
                (int(flake[0] + camera_offset[0]), int(flake[1] + camera_offset[1])),
                3
            )
    snowflakes[:] = [f for f in snowflakes if f[1] < HEIGHT + 10]

    if snow_depth > 0:
        pygame.draw.rect(
            screen, (245, 245, 245),
            (0, HEIGHT - 40 - snow_depth, WIDTH, snow_depth)
        )

def draw_cloud_layer(layer, color, speed_factor=1.0):
    for cloud in layer:
        cloud[0] += cloud[2] * speed_factor * (1 + wind_speed / 10.0)
        if cloud[0] > WIDTH + 150:
            cloud[0] = -150
        pygame.draw.ellipse(
            screen, color,
            (cloud[0] + camera_offset[0], cloud[1] + camera_offset[1], 140, 70)
        )

def draw_clouds_all():
    draw_cloud_layer(clouds_far, (210, 210, 220), 0.6)
    draw_cloud_layer(clouds_near, (230, 230, 240), 1.0)
    draw_cloud_layer(storm_clouds, (60, 60, 80), 1.4)

def draw_fog():
    if fog_strength <= 0:
        return
    fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fog.fill((200, 200, 200, int(120 * fog_strength)))
    screen.blit(fog, (0, 0))

def update_lightning(condition):
    global lightning_timer
    if condition == "Thunderstorm":
        if lightning_timer <= 0 and random.random() < 0.02:
            lightning_timer = 12
            if THUNDER_SOUND:
                THUNDER_SOUND.play()
            start_camera_shake(12, 15)
        else:
            lightning_timer = max(0, lightning_timer - 1)
    else:
        lightning_timer = 0

def draw_lightning_bolts():
    if lightning_timer <= 0:
        return
    bolt_color = (255, 255, 200)
    segments = random.randint(2, 4)
    for _ in range(2):
        x = random.randint(50, WIDTH - 50)
        y = 0
        for _ in range(segments):
            nx = x + random.randint(-20, 20)
            ny = y + random.randint(40, 80)
            pygame.draw.line(
                screen, bolt_color,
                (x + camera_offset[0], y + camera_offset[1]),
                (nx + camera_offset[0], ny + camera_offset[1]),
                3
            )
            x, y = nx, ny

def draw_lightning_overlay():
    if lightning_timer > 0:
        alpha = int(180 * (lightning_timer / 12))
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        screen.blit(flash, (0, 0))

# ------------- CAMERA SHAKE ------------- #

def start_camera_shake(amount=10, duration=15):
    global shake_timer, shake_amount
    shake_timer = duration
    shake_amount = amount

def update_camera_shake():
    global shake_timer, camera_offset
    if shake_timer > 0:
        camera_offset[0] = random.randint(-shake_amount, shake_amount)
        camera_offset[1] = random.randint(-shake_amount, shake_amount)
        shake_timer -= 1
    else:
        camera_offset = [0, 0]

# ------------- UI ANIMATION ------------- #

def animate_score():
    global score_scale
    score_scale = lerp(score_scale, 1.0, 0.2)

# ------------- SPEED LINES ------------- #

def spawn_speed_lines():
    for _ in range(2):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        length = random.randint(20, 40)
        speed = random.randint(15, 25)
        speed_lines.append([x, y, length, speed])

def draw_speed_lines():
    for line in speed_lines:
        line[1] += line[3]
        pygame.draw.line(
            screen, (255, 255, 255),
            (line[0] + camera_offset[0], line[1] + camera_offset[1]),
            (line[0] + camera_offset[0], line[1] + line[2] + camera_offset[1]),
            2
        )
    speed_lines[:] = [l for l in speed_lines if l[1] < HEIGHT]

# ------------- GAME SYSTEM ------------- #

def spawn_obstacle():
    lane = random.choice(LANES)
    obstacles.append([lane, -100])

def countdown():
    for i in range(3, 0, -1):
        screen.fill((255, 120, 50))
        font = pygame.font.SysFont(None, 120)
        text = font.render(str(i), True, (255, 255, 255))
        screen.blit(text, (230, 300))
        pygame.display.update()
        time.sleep(1)

def game_loop():
    global lane_index, player_x, target_x, obstacles, spawn_timer, score, highscore
    global player_angle, target_angle
    global current_bg, target_bg, weather_condition, rain_intensity, wind_speed
    global obstacle_speed, score_scale

    lane_index = 1
    player_x = LANES[lane_index]
    target_x = player_x
    player_angle = 0
    target_angle = 0

    obstacles = []
    spawn_timer = 0
    score = 0
    score_scale = 1.0
    obstacle_speed = 10

    countdown()

    weather_condition, rain_intensity, wind_speed = get_weather()
    init_weather_effects(weather_condition, wind_speed)
    target_bg = pick_background_color(weather_condition)
    current_bg = target_bg

    running = True
    while running:
        clock.tick(60)

        update_camera_shake()
        update_lightning(weather_condition)

        current_bg = (
            lerp(current_bg[0], target_bg[0], 0.02),
            lerp(current_bg[1], target_bg[1], 0.02),
            lerp(current_bg[2], target_bg[2], 0.02)
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                if event.key == pygame.K_LEFT and lane_index > 0:
                    lane_index -= 1
                    target_x = LANES[lane_index]
                    target_angle = -15
                if event.key == pygame.K_RIGHT and lane_index < 2:
                    lane_index += 1
                    target_x = LANES[lane_index]
                    target_angle = 15

        player_x = lerp(player_x, target_x, 0.2)
        player_angle = lerp(player_angle, target_angle, 0.2)
        if abs(player_x - target_x) < 0.5:
            player_x = target_x
            target_angle = 0

        spawn_timer += 1
        if spawn_timer > 70:
            spawn_obstacle()
            spawn_timer = 0

        for obs in obstacles:
            progress = ease_out_quad(0.12)
            obs[1] += obstacle_speed * progress

        obstacles[:] = [o for o in obstacles if o[1] < HEIGHT + 100]

        player_rect = pygame.Rect(player_x - 25, player_base_y, player_size, player_size)
        for obs in obstacles:
            obs_rect = pygame.Rect(obs[0] - 25, obs[1], 50, 50)
            if player_rect.colliderect(obs_rect):
                start_camera_shake(15, 20)
                return "gameover"

        score += 1
        if score % 300 == 0:
            obstacle_speed += 1

        score_scale = 1.3 if score_scale <= 1.01 else score_scale
        animate_score()

        if obstacle_speed >= 10 and score % 5 == 0:
            spawn_speed_lines()

        screen.fill((int(current_bg[0]), int(current_bg[1]), int(current_bg[2])))

        # WEATHER VISUALS
        if weather_condition in ("Clouds", "Rain", "Thunderstorm"):
            draw_clouds_all()
        if weather_condition in ("Rain", "Thunderstorm"):
            spawn_rain()
            draw_rain()
        if weather_condition == "Snow":
            spawn_snow()
            draw_snow()
        draw_fog()
        draw_lightning_bolts()
        draw_lightning_overlay()

        draw_speed_lines()

        player_surface = pygame.Surface((player_size, player_size), pygame.SRCALPHA)
        pygame.draw.rect(player_surface, (0, 200, 255), (0, 0, player_size, player_size))
        rotated = pygame.transform.rotate(player_surface, player_angle)
        rect = rotated.get_rect(center=(player_x + camera_offset[0],
                                        player_base_y + camera_offset[1]))
        screen.blit(rotated, rect.topleft)

        for obs in obstacles:
            pygame.draw.rect(
                screen, (255, 50, 50),
                (obs[0] - 25 + camera_offset[0],
                 obs[1] + camera_offset[1], 50, 50)
            )

        font_size = int(40 * score_scale)
        font = pygame.font.SysFont(None, font_size)
        score_text = font.render(f"Score: {score}", True, (255, 255, 255))
        high_font = pygame.font.SysFont(None, 40)
        high_text = high_font.render(f"Highscore: {highscore}", True, (255, 255, 0))

        screen.blit(score_text, (10 + camera_offset[0], 10 + camera_offset[1]))
        screen.blit(high_text, (10 + camera_offset[0], 50 + camera_offset[1]))

        pygame.display.update()

def game_over_screen():
    global score, highscore

    if score > highscore:
        highscore = score
        save_highscore(highscore)

    fade = 0
    while True:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return "restart"
                if event.key == pygame.K_ESCAPE:
                    return "quit"

        fade = min(fade + 5, 255)

        screen.fill((fade, 206, fade))
        font = pygame.font.SysFont(None, 80)
        text = font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(text, (100, 250))

        font2 = pygame.font.SysFont(None, 50)
        screen.blit(font2.render(f"Score: {score}", True, (255, 255, 255)), (170, 350))
        screen.blit(font2.render("Press R to Restart", True, (200, 200, 200)), (120, 450))
        screen.blit(font2.render("Press ESC to Quit", True, (200, 200, 200)), (130, 500))

        pygame.display.update()

# --- MAIN LOOP ---
while True:
    result = game_loop()

    if result == "quit":
        break

    if result == "gameover":
        result2 = game_over_screen()
        if result2 == "quit":
            break

pygame.quit()
