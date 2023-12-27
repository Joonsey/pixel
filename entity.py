from __future__ import annotations
from abc import ABC
from typing import Any, Callable

import pygame


class Entity(ABC):
    def __init__(self, pos: tuple[float, float] = (0, 0)) -> None:
        self.position = pos
        self.image: pygame.surface.Surface
        self.rect: pygame.rect.Rect


    def render(self, surf: pygame.surface.Surface, scroll: tuple | None = None) -> None:
        rect = pygame.rect.Rect(self.rect)
        if scroll:
            rect.x += self.position[0] - scroll[0]
            rect.y += self.position[1] - scroll[1]

        surf.blit(self.image, rect)


class Block(Entity):
    def __init__(self,
                 pos: tuple[float, float],
                 width: int,
                 height: int,
                 color: pygame.color.Color
                 ) -> None:
        super().__init__(pos=pos)
        self.width = width
        self.height = height
        self.color = color

        self.image = pygame.Surface([width, height])
        self.image.fill(color)

        self.rect = self.image.get_rect()

    def render(self, surf: pygame.surface.Surface, scroll: tuple | None = None) -> None:
        return super().render(surf, scroll)


class Player(Entity):
    def __init__(self, pos: tuple[float, float]) -> None:
        super().__init__(pos = pos)
        self.velocity = [0.,.0]
        self.base_acceleration = .25
        self.acceleration = self.base_acceleration
        self.max_velocity = .5
        self.speed = 25


    def update_position(self, x: float, y: float) -> None:
        self.position = (x, y)


    def handle_movement(self, keys: pygame.key.ScancodeWrapper, dt: float, broadcast_hook: Callable | None = None):
        normalized_dt = dt/100
        if keys[pygame.K_w]:
            self.velocity[1] = -self.acceleration
        elif keys[pygame.K_s]:
            self.velocity[1] = self.acceleration
        else:
            self.velocity[1] = 0

        if keys[pygame.K_a]:
            self.velocity[0] = -self.acceleration
        elif keys[pygame.K_d]:
            self.velocity[0] = self.acceleration
        else:
            self.velocity[0] = 0

        if self.velocity[0] or self.velocity[1]:
            self.acceleration *= dt / 14
            if self.acceleration >= self.max_velocity:
                self.acceleration = self.max_velocity
        else:
            self.acceleration = self.base_acceleration / 4

        delta_x = self.velocity[0] * self.speed * normalized_dt
        delta_y = self.velocity[1] * self.speed * normalized_dt

        self.update_position(self.position[0] + delta_x, self.position[1] + delta_y)

        if broadcast_hook is not None and any([delta_x, delta_y]):
            # calls broadcast hook if it is given, and if there is change in position
            broadcast_hook()
