from __future__ import annotations
from typing import Callable
import pygame

import logging

import client
import settings
import packets

pygame.init()

RESOLUTION = (1280, 720)
FPS_TARGET = 60
TILESIZE = 16


class Player:
    def __init__(self) -> None:
        self.position = pygame.Vector2(0,0)
        self.velocity = [0.,.0]
        self.base_acceleration = .25
        self.acceleration = self.base_acceleration
        self.max_velocity = .5
        self.speed = 55


    @staticmethod
    def infer_from_data(position: tuple[int | float, int | float]) -> Player:
        p = Player()
        p.position = pygame.Vector2(position)
        return p


    def update_position(self, x: float, y: float) -> None:
        self.position.x = x
        self.position.y = y


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


        self.update_position(self.position.x + delta_x, self.position.y + delta_y)

        if broadcast_hook is not None and any([delta_x, delta_y]):
            # sends broadcast hook if it is given, and if there is change in position
            broadcast_hook()


class World:
    def __init__(self) -> None:
        self.world_data: list[list[str]]


    def update_world_data(self, data: list[list[str]]) -> None:
        self.world_data = data


    def render(self, target_surf: pygame.surface.Surface) -> None:
        for y, array in enumerate(self.world_data):
            for x, tile in enumerate(array):
                surf = pygame.surface.Surface((TILESIZE, TILESIZE))
                surf.fill((233,13,34) if tile == "#" else (23,1,244))
                target_surf.blit(surf, (x * TILESIZE, y * TILESIZE))


class Game:
    def __init__(self) -> None:
        self.display = pygame.display.set_mode(RESOLUTION)
        self.player = Player()
        self.world = World()
        self.client = client.Client(
            settings.HOST,
            settings.TCP_PORT,
            settings.UDP_PORT,
            "Jae"
        )

        self.deltatime = 0
        self.clock = pygame.time.Clock()
        self.running = True


    @property
    def other_players(self) -> list[Player]:
        return [Player.infer_from_data(x[1]) for x in self.client.others.items()]


    def _send_position(self) -> None:
        if self.client.authenticated:
            self.client.send_packet(
                packets.Packet(
                    packets.PacketType.MOVE,
                    self.client.auth_id,
                    packets.PayloadFormat.MOVE.pack(
                        self.client.id,
                        int(self.player.position.x),
                        int(self.player.position.y)
            )))


    def render_entities(self, entities: list[Player]) -> None:
        surf = pygame.surface.Surface((20, 20))
        surf.fill((0,0,255))
        [self.display.blit(surf, entity.position) for entity in entities]


    def render_player(self) -> None:
        surf = pygame.surface.Surface((20, 20))
        surf.fill((0,255,0))
        self.display.blit(surf, self.player.position)


    def run(self) -> None:
        self.client.start()

        while self.running:
            self.deltatime = self.clock.tick(FPS_TARGET)
            for event in pygame.event.get():
                if event == pygame.QUIT:
                    self.running = False


            if self.client.map_has_changed:
                self.world.update_world_data(self.client.map)

            keys = pygame.key.get_pressed()
            self.player.handle_movement(keys, self.deltatime, self._send_position)

            self.world.render(self.display)
            self.render_entities(self.other_players.copy())
            self.render_player()

            pygame.display.flip()
            self.display.fill(0)

if __name__ == "__main__":
    game = Game()
    try:
        game.run()
    except KeyboardInterrupt:
        game.client.disconnect(packets.DisconnectEnum.EXPECTED)
    except Exception as e:
        game.client.disconnect()
        raise e
