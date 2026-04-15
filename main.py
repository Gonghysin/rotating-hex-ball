import sys
import math
import pygame
from pygame import Vector2

pygame.init()

WIDTH, HEIGHT = 800, 800
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rotating Hexagon Bouncing Ball")
clock = pygame.time.Clock()

# Colors
COLOR_BG = (20, 20, 30)
COLOR_HEX = (0, 200, 255)
COLOR_BALL = (255, 80, 80)
COLOR_TRAIL = (255, 120, 120)
COLOR_SLIDER_BG = (60, 60, 70)
COLOR_SLIDER_FILL = (0, 200, 255)
COLOR_SLIDER_KNOB = (255, 255, 255)

GRAVITY = Vector2(0, 0.4)  # pixels/frame^2


def rotate_point(point: Vector2, angle: float, center: Vector2 = Vector2(0, 0)) -> Vector2:
    s = math.sin(angle)
    c = math.cos(angle)
    px = point.x - center.x
    py = point.y - center.y
    return Vector2(
        center.x + px * c - py * s,
        center.y + px * s + py * c,
    )


class Hexagon:
    def __init__(self, center: Vector2, radius: float, omega: float):
        self.center = center
        self.radius = radius
        self.omega = omega  # radians per frame
        self.angle = 0.0
        self.vertices = self._compute_vertices()

    def _compute_vertices(self) -> list[Vector2]:
        verts = []
        for i in range(6):
            theta = math.radians(60 * i)
            x = self.center.x + self.radius * math.cos(theta)
            y = self.center.y + self.radius * math.sin(theta)
            verts.append(Vector2(x, y))
        return verts

    def update(self):
        self.angle += self.omega
        self.vertices = [rotate_point(v, self.angle, self.center) for v in self._compute_vertices()]

    def draw(self, surface):
        pygame.draw.polygon(surface, COLOR_HEX, self.vertices, width=3)


class Slider:
    def __init__(self, x: float, y: float, width: float, height: float,
                 min_val: float, max_val: float, initial: float, label: str):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial
        self.label = label
        self.dragging = False

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.dragging = True
            self._update_from_mouse(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_from_mouse(event.pos[0])

    def _update_from_mouse(self, mouse_x: float):
        ratio = (mouse_x - self.rect.x) / self.rect.width
        ratio = max(0.0, min(1.0, ratio))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)

    def draw(self, surface: pygame.Surface):
        # Background track
        pygame.draw.rect(surface, COLOR_SLIDER_BG, self.rect, border_radius=4)

        # Filled portion
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        fill_width = self.rect.width * ratio
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(surface, COLOR_SLIDER_FILL, fill_rect, border_radius=4)

        # Knob
        knob_x = self.rect.x + fill_width
        knob_y = self.rect.centery
        pygame.draw.circle(surface, COLOR_SLIDER_KNOB, (int(knob_x), knob_y), int(self.rect.height / 1.5))

        # Label
        font = pygame.font.SysFont("monospace", 16)
        text = font.render(f"{self.label}: {self.value:.2f}", True, (200, 200, 200))
        surface.blit(text, (self.rect.x, self.rect.y - 22))


class Ball:
    def __init__(self, pos: Vector2, vel: Vector2, radius: float, restitution: float = 1.0):
        self.pos = pos
        self.vel = vel
        self.radius = radius
        self.restitution = restitution
        self.trail: list[Vector2] = []
        self.max_trail = 80

    def update(self, hexagon: Hexagon):
        steps = 4
        dt = 1.0 / steps
        for _ in range(steps):
            self.vel += GRAVITY * dt
            self.pos += self.vel * dt
            self._handle_collision(hexagon)

        self.trail.append(Vector2(self.pos))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)

    def _handle_collision(self, hexagon: Hexagon):
        for i in range(6):
            a = hexagon.vertices[i]
            b = hexagon.vertices[(i + 1) % 6]

            edge = b - a
            edge_len_sq = edge.length_squared()
            if edge_len_sq == 0:
                continue

            t = max(0.0, min(1.0, (self.pos - a).dot(edge) / edge_len_sq))
            closest = a + edge * t

            diff = self.pos - closest
            dist = diff.length()

            if dist < self.radius and dist > 0:
                normal = -diff / dist
                to_center = hexagon.center - closest
                if normal.dot(to_center) < 0:
                    normal = -normal

                rel = closest - hexagon.center
                v_wall = Vector2(-rel.y, rel.x) * hexagon.omega

                v_rel = self.vel - v_wall

                if v_rel.dot(normal) > 0:
                    continue

                # Reflect with energy loss (restitution)
                v_rel_new = v_rel - (1 + self.restitution) * v_rel.dot(normal) * normal
                self.vel = v_wall + v_rel_new

                penetration = self.radius - dist
                self.pos += normal * penetration

    def draw(self, surface):
        if len(self.trail) > 1:
            for i in range(len(self.trail) - 1):
                color = (COLOR_TRAIL[0], COLOR_TRAIL[1], COLOR_TRAIL[2])
                pygame.draw.line(surface, color, self.trail[i], self.trail[i + 1], 2)
        pygame.draw.circle(surface, COLOR_BALL, self.pos, self.radius)


def main():
    center = Vector2(WIDTH / 2, HEIGHT / 2)
    hex_radius = 280
    hex_omega = math.radians(1.5)

    hexagon = Hexagon(center, hex_radius, hex_omega)

    initial_speed = 5.0
    ball = Ball(
        pos=center + Vector2(-80, -120),
        vel=Vector2(initial_speed, initial_speed * 0.5),
        radius=10,
        restitution=0.95,
    )

    restitution_slider = Slider(
        x=WIDTH - 220,
        y=HEIGHT - 80,
        width=200,
        height=12,
        min_val=0.0,
        max_val=1.0,
        initial=0.95,
        label="Restitution",
    )

    energy_slider = Slider(
        x=WIDTH - 220,
        y=HEIGHT - 40,
        width=200,
        height=12,
        min_val=0.0,
        max_val=15.0,
        initial=initial_speed,
        label="Init Speed",
    )

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    speed = energy_slider.value
                    ball.pos = center + Vector2(-80, -120)
                    ball.vel = Vector2(speed, speed * 0.5)
                    ball.trail.clear()
                if event.key == pygame.K_UP:
                    hexagon.omega += math.radians(0.5)
                if event.key == pygame.K_DOWN:
                    hexagon.omega -= math.radians(0.5)

            restitution_slider.handle_event(event)
            energy_slider.handle_event(event)

        ball.restitution = restitution_slider.value

        hexagon.update()
        ball.update(hexagon)

        screen.fill(COLOR_BG)
        hexagon.draw(screen)
        ball.draw(screen)

        # UI text (two lines to avoid overflow)
        font = pygame.font.SysFont("monospace", 16)
        line1 = font.render(
            f"Omega: {math.degrees(hexagon.omega):.1f} deg/frame | Gravity: {GRAVITY.y} px/f^2",
            True,
            (200, 200, 200),
        )
        line2 = font.render(
            "UP/DOWN: change omega | SPACE: reset ball",
            True,
            (200, 200, 200),
        )
        screen.blit(line1, (10, 10))
        screen.blit(line2, (10, 30))

        restitution_slider.draw(screen)
        energy_slider.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
