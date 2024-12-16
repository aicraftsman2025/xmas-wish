import pygame
import random
import sys
import pymunk
import math
from pygame import mixer
import asyncio
import websockets
import json

# Khởi tạo pygame
pygame.init()
mixer.init()

# Thiết lập màn hình
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Christmas Wishes")

# Khởi tạo không gian vật lý
space = pymunk.Space()
space.gravity = (0, 900)  # Điều chỉnh trọng lực

# Màu sắc
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
DARK_BLUE = (0, 20, 60)   # Có thể điều chỉnh giá trị này để có màu xanh đậm khác

# Load hình ảnh
santa = pygame.image.load("assets/santa-g.png")
tree = pygame.image.load("assets/tree.png")
gift = pygame.image.load("assets/gift.png")
star = pygame.image.load("assets/star.png")
pine = pygame.image.load("assets/pine.png")

# Scale images
SANTA_SCALE = 0.4
santa = pygame.transform.scale(santa, 
                             (int(380 * SANTA_SCALE), int(165 * SANTA_SCALE)))
tree = pygame.transform.scale(tree, (200, 300))
gift = pygame.transform.scale(gift, (30, 30))
star = pygame.transform.scale(star, (30, 30))
pine = pygame.transform.scale(pine, (30, 30))

# Vật lý
GROUND_Y = WINDOW_HEIGHT - 50

# Tạo mặt đất tĩnh
ground_body = space.static_body
ground_shape = pymunk.Segment(ground_body, (0, GROUND_Y), (WINDOW_WIDTH, GROUND_Y), 1.0)
ground_shape.friction = 0.7
ground_shape.elasticity = 0.5
space.add(ground_shape)

# Biến global cho WebSocket
pending_wishes = []
current_sender_name = "Anonymous"
current_selected_item = "gift"

# Dictionary cho item images
item_images = {
    "gift": gift,
    "star": star,
    "pine": pine
}

is_fullscreen = False
original_size = (WINDOW_WIDTH, WINDOW_HEIGHT)

class Santa:
    def __init__(self):
        self.x = -100
        self.y = 100
        self.base_y = 100
        self.speed = 3
        self.direction = 1
        self.active = False
        self.has_dropped = False
        self.time = 0
        self.amplitude = 30
        self.frequency = 0.05
        
    def move(self):
        if self.active:
            self.x += self.speed * self.direction
            self.time += 1
            self.y = self.base_y + self.amplitude * math.sin(self.time * self.frequency)
            
            if self.x > WINDOW_WIDTH + 100 or self.x < -100:
                self.active = False
                self.has_dropped = False
                self.time = 0

class FloatingText:
    def __init__(self, text, x, y, color, index=0):
        self.original_text = text
        self.x = x
        self.y = y
        self.target_y = y + (index * 50)
        self.color = color
        self.alpha = 255
        self.scale = 1.0
        self.time = 0
        self.fade_speed = 0.5
        self.display_time = 180
        self.move_speed = 0.1
        try:
            self.font = pygame.font.Font("assets/NotoSans-Regular.ttf", 32)
        except:
            print("Fallback to default font")
            self.font = pygame.font.Font(None, 32)
        
    def update(self):
        self.time += 0.05
        self.scale = 1.0 + 0.1 * math.sin(self.time * 2)
        
        if self.display_time > 0:
            self.display_time -= 1
        else:
            self.alpha = max(0, self.alpha - self.fade_speed)
        
        if abs(self.y - self.target_y) > 0.1:
            self.y += (self.target_y - self.y) * self.move_speed
        
        return self.alpha > 0
        
    def draw(self, screen):
        # Create text with current scale
        size = int(32 * self.scale)
        try:
            font = pygame.font.Font("assets/NotoSans-Regular.ttf", size)
        except:
            font = pygame.font.Font(None, size)
        
        text_surface = font.render(self.original_text, True, self.color)
        text_surface.set_alpha(self.alpha)
        text_rect = text_surface.get_rect(center=(self.x, self.y))
        screen.blit(text_surface, text_rect)

    def set_position(self, new_index):
        self.target_y = 50 + (new_index * 50)

class Item:
    def __init__(self, x, y, item_type, sender_name="Anonymous"):
        self.item_type = item_type
        self.sender_name = sender_name
        
        mass = 1
        size = 15
        moment = pymunk.moment_for_box(mass, (size * 2, size * 2))
        self.body = pymunk.Body(mass, moment)
        self.body.position = x, y
        
        self.body.velocity = (random.uniform(-20, 20), random.uniform(-10, 0))
        self.body.angle = random.uniform(0, math.pi * 2)
        
        self.shape = pymunk.Poly.create_box(self.body, (size * 2, size * 2))
        self.shape.friction = 0.7
        self.shape.elasticity = 0.5
        
        space.add(self.body, self.shape)
        
        self.name_font = pygame.font.Font("assets/NotoSans-Regular.ttf", 14)

    def draw(self, screen, item_image):
        pos = self.body.position
        angle_degrees = math.degrees(self.body.angle)
        rotated_item = pygame.transform.rotate(item_image, angle_degrees)
        screen.blit(rotated_item, 
                   (pos.x - rotated_item.get_width()/2,
                    pos.y - rotated_item.get_height()/2))
        
        name_surface = self.name_font.render(self.sender_name, True, (255, 255, 0))
        name_rect = name_surface.get_rect(center=(pos.x, pos.y + 20))
        screen.blit(name_surface, name_rect)

def create_snow_particles(num_particles=50):
    particles = []
    for _ in range(num_particles):
        x = random.randint(0, WINDOW_WIDTH)
        y = random.randint(0, WINDOW_HEIGHT)
        speed = random.uniform(1, 3)
        particles.append({'x': x, 'y': y, 'speed': speed})
    return particles

def update_snow_particles(particles):
    for particle in particles:
        particle['y'] += particle['speed']
        if particle['y'] > WINDOW_HEIGHT:
            particle['y'] = 0
            particle['x'] = random.randint(0, WINDOW_WIDTH)

def draw_snow_particles(screen, particles):
    for particle in particles:
        pygame.draw.circle(screen, WHITE, 
                         (int(particle['x']), int(particle['y'])), 2)

def draw_gradient_background(screen):
    height = screen.get_height()
    for i in range(height):
        color = (0, 0, min(128 * i/height, 40))
        pygame.draw.line(screen, color, (0, i), (WINDOW_WIDTH, i))

async def websocket_client():
    global pending_wishes
    uri = "ws://localhost:8080"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Connected to WebSocket server")
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Received wish: {data}")
                    pending_wishes.append(data)
        except Exception as e:
            print(f"WebSocket error: {e}")
            await asyncio.sleep(5)

class WishQueue:
    def __init__(self):
        self.wishes = []
        self.current_wish = None
        self.processing = False
    
    def add_wish(self, wish):
        self.wishes.append(wish)
    
    def get_next_wish(self):
        if not self.processing and self.wishes:
            self.current_wish = self.wishes.pop(0)
            self.processing = True
            return self.current_wish
        return None
    
    def mark_completed(self):
        self.processing = False
        self.current_wish = None

class LightParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.color = (255, 255, 100)  # Bright yellow for star
        self.size = random.uniform(1, 3)  # Slightly larger for star points
        self.lifetime = random.randint(40, 100)
        self.alpha = 255
        self.fade_speed = random.uniform(1.5, 3)
        self.angle = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(0.3, 0.6)
        self.rotation = random.uniform(0, 360)
        self.spin_speed = random.uniform(-2, 2)

    def update(self):
        # Move in a slight spiral pattern
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.angle += 0.02
        
        # Rotate the star
        self.rotation += self.spin_speed
        
        # Fade out
        self.alpha = max(0, self.alpha - self.fade_speed)
        self.lifetime -= 1
        
        return self.lifetime > 0

    def draw(self, screen):
        # Create a surface for the star with alpha
        surf = pygame.Surface((int(self.size * 6), int(self.size * 6)), pygame.SRCALPHA)
        center = (int(self.size * 3), int(self.size * 3))
        
        # Draw a 5-pointed star
        points = []
        for i in range(5):
            # Outer points
            angle = math.radians(self.rotation + i * 72)
            points.append((
                center[0] + math.cos(angle) * self.size * 3,
                center[1] + math.sin(angle) * self.size * 3
            ))
            # Inner points
            angle = math.radians(self.rotation + i * 72 + 36)
            points.append((
                center[0] + math.cos(angle) * self.size,
                center[1] + math.sin(angle) * self.size
            ))
        
        # Draw the star with glow effect
        for offset in range(3, 0, -1):
            alpha = int(self.alpha * (offset / 3))
            pygame.draw.polygon(
                surf,
                (*self.color, alpha),
                points,
                max(1, offset)
            )
        
        screen.blit(surf, (
            int(self.x - self.size * 3),
            int(self.y - self.size * 3)
        ))

async def game_loop():
    global screen, GROUND_Y, WINDOW_WIDTH, WINDOW_HEIGHT, ground_shape
    global current_sender_name, current_selected_item, is_fullscreen

    clock = pygame.time.Clock()
    santa_obj = Santa()
    items = []
    floating_texts = []
    snow_particles = create_snow_particles()
    wish_queue = WishQueue()
    light_particles = []
    tree_rect = pygame.Rect(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT - 350, 200, 300)
    last_particle_time = 0
    PARTICLE_SPAWN_DELAY = 120  # ms
    active_wish_count = 0
    MAX_VISIBLE_WISHES = 3
    
    running = True
    while running:
        # Thêm wishes vào queue
        if pending_wishes:
            wish = pending_wishes.pop(0)
            wish_queue.add_wish(wish)

        # Xử lý wish tiếp theo nếu Santa không active
        if not santa_obj.active and active_wish_count < MAX_VISIBLE_WISHES:
            next_wish = wish_queue.get_next_wish()
            if next_wish:
                current_sender_name = next_wish['name']
                current_selected_item = next_wish['item']
                
                santa_obj.active = True
                santa_obj.x = -100 if random.choice([True, False]) else WINDOW_WIDTH + 100
                santa_obj.direction = 1 if santa_obj.x < 0 else -1
                santa_obj.has_dropped = False
                santa_obj.time = 0
                
                floating_texts.append(
                    FloatingText(
                        f"{next_wish['name']}: {next_wish['message']}", 
                        WINDOW_WIDTH//2, 
                        50, 
                        (255, 0, 0),
                        len(floating_texts)
                    )
                )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        WINDOW_WIDTH = screen.get_width()
                        WINDOW_HEIGHT = screen.get_height()
                        GROUND_Y = WINDOW_HEIGHT - 50
                        
                        # Cập nhật ground shape
                        space.remove(ground_shape)
                        ground_shape = pymunk.Segment(ground_body, 
                                                    (0, GROUND_Y), 
                                                    (WINDOW_WIDTH, GROUND_Y), 
                                                    1.0)
                        ground_shape.friction = 0.7
                        ground_shape.elasticity = 0.5
                        space.add(ground_shape)
                        
                        # Cập nhật vị trí tree_rect cho particles
                        tree_rect = pygame.Rect(WINDOW_WIDTH//2 - 100, 
                                              WINDOW_HEIGHT - 350, 
                                              200, 300)
                        
                        # Xóa particles cũ và tạo mới theo kích thước mới
                        light_particles.clear()
                        
                    else:
                        screen = pygame.display.set_mode(original_size)
                        WINDOW_WIDTH, WINDOW_HEIGHT = original_size
                        GROUND_Y = WINDOW_HEIGHT - 50
                        
                        # Cập nhật ground shape
                        space.remove(ground_shape)
                        ground_shape = pymunk.Segment(ground_body, 
                                                    (0, GROUND_Y), 
                                                    (WINDOW_WIDTH, GROUND_Y), 
                                                    1.0)
                        ground_shape.friction = 0.7
                        ground_shape.elasticity = 0.5
                        space.add(ground_shape)
                        
                        # Cập nhật vị trí tree_rect cho particles
                        tree_rect = pygame.Rect(WINDOW_WIDTH//2 - 100, 
                                              WINDOW_HEIGHT - 350, 
                                              200, 300)
                        
                        # Xóa particles cũ và tạo mới theo kích thước mới
                        light_particles.clear()

        draw_gradient_background(screen)
        pygame.draw.rect(screen, DARK_BLUE, (0, GROUND_Y, WINDOW_WIDTH, WINDOW_HEIGHT))
        screen.blit(tree, (WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT - 350))
        
        update_snow_particles(snow_particles)
        draw_snow_particles(screen, snow_particles)
        
        space.step(1/60.0)

        if santa_obj.active:
            santa_obj.move()
            angle = math.sin(santa_obj.time * santa_obj.frequency) * 10
            rotated_santa = pygame.transform.rotate(
                pygame.transform.flip(santa, santa_obj.direction == 1, False),
                angle * santa_obj.direction
            )
            rect = rotated_santa.get_rect(center=(santa_obj.x + santa.get_width()/2, 
                                                santa_obj.y + santa.get_height()/2))
            screen.blit(rotated_santa, rect.topleft)
            
            if WINDOW_WIDTH//2 - 50 <= santa_obj.x <= WINDOW_WIDTH//2 + 50 and not santa_obj.has_dropped:
                random_x = santa_obj.x + random.randint(-30, 30)
                random_y = santa_obj.y + 50
                items.append(Item(random_x, random_y, current_selected_item, current_sender_name))
                santa_obj.has_dropped = True

            if santa_obj.x > WINDOW_WIDTH + 100 or santa_obj.x < -100:
                wish_queue.mark_completed()

        for item in items:
            item.draw(screen, item_images[item.item_type])
        
        new_floating_texts = []
        for i, text in enumerate(floating_texts):
            if text.update():
                text.set_position(i)
                new_floating_texts.append(text)
        floating_texts = new_floating_texts

        # Cập nhật và vẽ light particles
        current_time = pygame.time.get_ticks()
        if current_time - last_particle_time > PARTICLE_SPAWN_DELAY:
            # Tạo particle mới xung quanh cây thông với vị trí tương đối
            for _ in range(2):
                # Tính toán vị trí dựa trên tree_rect hiện tại
                x = random.randint(tree_rect.left + 20, tree_rect.right - 20)
                y = random.randint(tree_rect.top + 50, tree_rect.bottom - 50)
                light_particles.append(LightParticle(x, y))
            last_particle_time = current_time

        # Cập nhật và vẽ các particles
        light_particles = [p for p in light_particles if p.update()]
        for particle in light_particles:
            particle.draw(screen)

        # After updating floating texts
        for text in floating_texts:
            text.draw(screen)

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

async def main():
    await asyncio.gather(
        websocket_client(),
        game_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())