#!/usr/bin/env python3
"""
AC KONDO'S MINECRAFT — PY PORT 1.x INFDEV
Zero-shot 3D Voxel Engine: Infdev feature pack, chunked infinite terrain,
DDA raycasting, software rasterizer.

Infdev systems (ported / reimplemented from public Classic–Infdev algorithms
& Minecraft Wiki feature lists — ClassiCube NotchyGen caves/ores/flood style):
  * Infinite chunked terrain | multi-octave heightmap | sea level lakes
  * Worm caves + coal/iron/gold/diamond veins | water & lava springs
  * Dynamic fluids | falling sand/gravel | grass spread | water swimming
  * Brick pyramids | obsidian walls | oak trees | monster rooms (dungeons)
  * Ladders | doors | 3D clouds | day/night | fancy/fast graphics
  * Hotbar blocks matching Infdev creative kit

  * import math + pygame-ce only (import pygame)
  * files = off — zero external assets; procedural audio in RAM
  * Math OST: procedural "Sweden"-style ambient (sine/pad synth, no audio files)
  * WASD Move | SPACE Jump | F Fly | G Fancy | N mute OST | Click Break/Place

© AC Kondo 1999–2026 / A.C Holdings. All rights reserved.
Run: python3 "cat'skondomine4k.py"
"""

from __future__ import annotations

import array
import math
import random
import sys
from collections import deque

import pygame

# ---------------------------------------------------------------------------
# Engine Constants & Identity
# ---------------------------------------------------------------------------
TITLE = "AC KONDO'S MINECRAFT — PY PORT 1.x INFDEV"
SUBTITLE = "AC Kondo Infdev | full algo pack | procedural textures | files=off"
COPYRIGHT = "© AC Kondo / A.C Holdings 1999–2026"
BRAND = "AC KONDO"

SCREEN_W, SCREEN_H = 960, 600
HALF_W, HALF_H = SCREEN_W // 2, SCREEN_H // 2
FPS = 60
FOV = 480.0
NEAR_Z = 0.15
RENDER_DIST = 16.5

CHUNK = 16
LOAD_R = 2          # chunks around player (5×5 loaded)
WORLD_Y = 32
SEA_LEVEL = 10
BEDROCK_Y = 0

# Xbox 360 Edition TU0 / Demo Tutorial World — seed is RAM-only (files = off).
# Public seed from Legacy Console Edition TU0 tutorial world (Minecraft Wiki).
# Spawn: X 3, Z -37 facing south (4J tutorial compound recreated procedurally).
XBOX_DEMO_SEED = 1171544198849424676
XBOX_SPAWN_X = 3.5
XBOX_SPAWN_Z = -36.5
XBOX_SPAWN_YAW = 0.0   # +Z = south in this engine
FAR_LANDS = 420          # scaled Infdev Far Lands (real ~±12,550,824)
TEX = 16                 # procedural texture size (files=off, no Mojang assets)

WALK_SPEED = 6.2
SPRINT_SPEED = 9.8
FLY_SPEED = 14.0
SWIM_SPEED = 3.8
JUMP_FORCE = 8.4
GRAVITY = 23.5
MOUSE_SENS = 0.0028

# Block IDs — Infdev / Indev catch-up palette
AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
COBBLESTONE = 4
WOOD = 5
LEAVES = 6
SAND = 7
GRAVEL = 8
WATER = 9
LAVA = 10
BRICK = 11
PLANKS = 12
GLASS = 13
COAL_ORE = 14
IRON_ORE = 15
GOLD_ORE = 16
DIAMOND_ORE = 17
GOLD = 18
OBSIDIAN = 19
BEDROCK = 20
SAPLING = 21
LADDER = 22
DOOR = 23
FLOWER = 24
MOSSY = 25
CHEST = 26
TORCH = 27
FIRE = 28
RAIL = 29
TNT = 30
BOOKSHELF = 31
IRON = 32
MUSHROOM = 33
FARMLAND = 34
WHEAT = 35
SPONGE = 36
SIGN = 37
STAIRS_W = 38
STAIRS_C = 39
SPAWNER = 40
FURNACE = 41
BUCKET = 42          # empty bucket (place uses water/lava from inv)

BLOCK_NAMES = {
    GRASS: "GRASS BLOCK", DIRT: "DIRT", STONE: "STONE", COBBLESTONE: "COBBLESTONE",
    WOOD: "OAK LOG", LEAVES: "OAK LEAVES", SAND: "SAND", GRAVEL: "GRAVEL",
    WATER: "WATER", LAVA: "LAVA", BRICK: "BRICK", PLANKS: "OAK PLANKS",
    GLASS: "GLASS", COAL_ORE: "COAL ORE", IRON_ORE: "IRON ORE", GOLD_ORE: "GOLD ORE",
    DIAMOND_ORE: "DIAMOND ORE", GOLD: "GOLD BLOCK", OBSIDIAN: "OBSIDIAN",
    BEDROCK: "BEDROCK", SAPLING: "SAPLING", LADDER: "LADDER", DOOR: "DOOR",
    FLOWER: "FLOWER", MOSSY: "MOSSY COBBLE", CHEST: "CHEST", TORCH: "TORCH",
    FIRE: "FIRE", RAIL: "RAIL", TNT: "TNT", BOOKSHELF: "BOOKSHELF",
    IRON: "IRON BLOCK", MUSHROOM: "MUSHROOM", FARMLAND: "FARMLAND",
    WHEAT: "WHEAT", SPONGE: "SPONGE", SIGN: "SIGN",
    STAIRS_W: "WOOD STAIRS", STAIRS_C: "COBBLE STAIRS", SPAWNER: "MONSTER SPAWNER",
    FURNACE: "FURNACE", BUCKET: "BUCKET",
}

HOTBAR_BLOCKS = [
    TORCH, TNT, RAIL, STAIRS_C, WOOD, PLANKS, FURNACE, BUCKET, SAND, WATER,
]

# UI states
ST_MENU = "menu"
ST_PLAY = "play"
ST_CRAFT = "craft"
ST_INV = "inv"
ST_ABOUT = "about"
ST_HELP = "help"

MENU_ITEMS = [
    ("Single Player — Xbox Demo", ST_PLAY),
    ("Crafting", ST_CRAFT),
    ("Inventory", ST_INV),
    ("About AC Kondo", ST_ABOUT),
    ("Help", ST_HELP),
    ("Exit", "exit"),
]

# Infdev workbench recipes (files=off)
CRAFT_RECIPES = [
    ("Oak Planks ×4", [(WOOD, 1)], PLANKS, 4),
    ("Ladder", [(PLANKS, 2)], LADDER, 2),
    ("Door", [(PLANKS, 6)], DOOR, 1),
    ("Chest", [(PLANKS, 8)], CHEST, 1),
    ("Torch ×4", [(COAL_ORE, 1), (PLANKS, 1)], TORCH, 4),
    ("TNT", [(SAND, 4), (GRAVEL, 1)], TNT, 1),
    ("Rails ×8", [(IRON_ORE, 1), (PLANKS, 1)], RAIL, 8),
    ("Wood Stairs ×4", [(PLANKS, 6)], STAIRS_W, 4),
    ("Cobble Stairs ×4", [(COBBLESTONE, 6)], STAIRS_C, 4),
    ("Furnace", [(COBBLESTONE, 8)], FURNACE, 1),
    ("Bucket", [(IRON_ORE, 3)], BUCKET, 1),
    ("Bookshelf", [(PLANKS, 6), (LEAVES, 3)], BOOKSHELF, 1),
    ("Iron Block", [(IRON_ORE, 9)], IRON, 1),
    ("Gold Block", [(GOLD_ORE, 9)], GOLD, 1),
    ("Glass (smelt)", [(SAND, 1)], GLASS, 1),
    ("Sign", [(PLANKS, 6)], SIGN, 1),
    ("Sponge", [(LEAVES, 8)], SPONGE, 1),
    ("Mossy Cobble", [(COBBLESTONE, 1), (LEAVES, 1)], MOSSY, 1),
]

# Furnace smelt table (Infdev catch-up)
SMELT = {
    SAND: GLASS,
    COBBLESTONE: STONE,
    GOLD_ORE: GOLD,
    IRON_ORE: IRON,
    WOOD: COAL_ORE,  # charcoal stand-in
}

INV_STARTER = {
    WOOD: 16, COBBLESTONE: 32, STONE: 32, DIRT: 16, SAND: 16, GRAVEL: 8,
    PLANKS: 16, GLASS: 4, BRICK: 4, LEAVES: 8, COAL_ORE: 8, IRON_ORE: 8,
    GOLD_ORE: 4, WATER: 4, LAVA: 2, SAPLING: 4, FLOWER: 4, TORCH: 16,
    TNT: 4, RAIL: 24, SPONGE: 2, MUSHROOM: 4, BUCKET: 2, FURNACE: 1,
    STAIRS_W: 8, STAIRS_C: 8,
}

# Top / Side / Bottom
BLOCK_COLORS = {
    GRASS:       ((88, 195, 58),   (126, 92, 58),  (110, 78, 48)),
    DIRT:        ((134, 96, 67),   (120, 85, 58),  (100, 70, 48)),
    STONE:       ((130, 130, 136), (115, 115, 122), (95, 95, 102)),
    COBBLESTONE: ((105, 105, 110), (90, 90, 95),   (75, 75, 80)),
    WOOD:        ((165, 132, 82),  (102, 78, 44),  (165, 132, 82)),
    LEAVES:      ((52, 148, 42),   (44, 128, 34),  (36, 108, 28)),
    SAND:        ((220, 210, 150), (205, 195, 135), (190, 180, 120)),
    GRAVEL:      ((140, 135, 130), (120, 115, 110), (100, 95, 90)),
    WATER:       ((40, 90, 200),   (35, 80, 185),  (30, 70, 170)),
    LAVA:        ((220, 90, 20),   (200, 70, 10),  (160, 40, 0)),
    BRICK:       ((160, 70, 55),   (145, 60, 48),  (120, 50, 40)),
    PLANKS:      ((190, 154, 95),  (170, 135, 80), (150, 118, 70)),
    GLASS:       ((180, 210, 230), (160, 190, 210), (140, 170, 190)),
    COAL_ORE:    ((90, 90, 95),    (70, 70, 75),   (55, 55, 60)),
    IRON_ORE:    ((160, 140, 120), (140, 120, 100), (110, 95, 80)),
    GOLD_ORE:    ((180, 160, 70),  (160, 140, 55), (130, 110, 40)),
    DIAMOND_ORE: ((90, 180, 200),  (70, 150, 170), (50, 120, 140)),
    GOLD:        ((255, 230, 66),  (230, 195, 42), (195, 160, 28)),
    OBSIDIAN:    ((25, 15, 40),    (18, 10, 30),   (12, 6, 20)),
    BEDROCK:     ((55, 55, 60),    (45, 45, 50),   (35, 35, 40)),
    SAPLING:     ((40, 160, 40),   (30, 120, 30),  (20, 80, 20)),
    LADDER:      ((150, 110, 60),  (130, 95, 50),  (110, 80, 40)),
    DOOR:        ((140, 100, 55),  (120, 85, 45),  (100, 70, 35)),
    FLOWER:      ((255, 80, 120),  (40, 160, 40),  (30, 120, 30)),
    MOSSY:       ((90, 110, 80),   (75, 95, 65),   (60, 75, 50)),
    CHEST:       ((170, 120, 50),  (140, 95, 40),  (110, 75, 30)),
    TORCH:       ((255, 200, 80),  (120, 80, 40),  (90, 60, 30)),
    FIRE:        ((255, 140, 30),  (220, 60, 10),  (180, 30, 0)),
    RAIL:        ((120, 120, 130), (90, 70, 40),   (70, 55, 30)),
    TNT:         ((200, 60, 60),   (220, 220, 220), (180, 40, 40)),
    BOOKSHELF:   ((160, 120, 70),  (120, 80, 45),  (100, 70, 40)),
    IRON:        ((210, 210, 220), (180, 180, 190), (150, 150, 160)),
    MUSHROOM:    ((200, 60, 50),   (180, 160, 140), (100, 80, 60)),
    FARMLAND:    ((120, 80, 50),   (110, 70, 45),  (90, 60, 40)),
    WHEAT:       ((180, 200, 60),  (120, 160, 40),  (80, 100, 30)),
    SPONGE:      ((200, 200, 70),  (180, 180, 55),  (150, 150, 40)),
    SIGN:        ((170, 130, 70),  (140, 100, 50),  (110, 80, 40)),
    STAIRS_W:    ((190, 154, 95),  (150, 118, 70),  (130, 100, 60)),
    STAIRS_C:    ((105, 105, 110), (90, 90, 95),    (75, 75, 80)),
    SPAWNER:     ((40, 60, 40),    (30, 45, 30),    (20, 30, 20)),
    FURNACE:     ((90, 90, 95),    (70, 70, 75),    (55, 55, 60)),
    BUCKET:      ((160, 160, 170), (120, 120, 130), (90, 90, 100)),
}

SOLID = {
    GRASS, DIRT, STONE, COBBLESTONE, WOOD, LEAVES, SAND, GRAVEL, BRICK, PLANKS,
    GLASS, COAL_ORE, IRON_ORE, GOLD_ORE, DIAMOND_ORE, GOLD, OBSIDIAN, BEDROCK,
    DOOR, MOSSY, CHEST, TNT, BOOKSHELF, IRON, FARMLAND, SPONGE, SIGN,
    STAIRS_W, STAIRS_C, SPAWNER, FURNACE,
}
FLUID = {WATER, LAVA}
FALLING = {SAND, GRAVEL}
FLAMMABLE = {WOOD, LEAVES, PLANKS, BOOKSHELF, TNT, FLOWER, SAPLING, WHEAT, STAIRS_W, SIGN}
TRANSPARENT = {
    WATER, LAVA, GLASS, LEAVES, SAPLING, LADDER, FLOWER, TORCH, FIRE, RAIL,
    MUSHROOM, WHEAT, SIGN, BUCKET,
}
REPLACEABLE = {AIR, WATER, SAPLING, FLOWER, LADDER, TORCH, FIRE, RAIL, MUSHROOM, WHEAT}

CUBE_FACES = [
    (0, 1, 0,  [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)], 1.00, True, False),
    (0, -1, 0, [(0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0)], 0.50, False, True),
    (0, 0, 1,  [(1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1)], 0.84, False, False),
    (0, 0, -1, [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)], 0.80, False, False),
    (1, 0, 0,  [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)], 0.70, False, False),
    (-1, 0, 0, [(0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0)], 0.66, False, False),
]


# ---------------------------------------------------------------------------
# Procedural Infdev textures (files=off — original math patterns, no Mojang assets)
# ---------------------------------------------------------------------------
def _clamp_rgb(c):
    return (max(0, min(255, int(c[0]))), max(0, min(255, int(c[1]))), max(0, min(255, int(c[2]))))


def _tex_noise(x, y, salt=0):
    n = (x * 374761393 + y * 668265263 + salt * 982451653) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 255) / 255.0


class TexAtlas:
    """16×16 RAM textures per block face — Infdev-look procedural, not copied art."""

    def __init__(self):
        self.faces = {}  # bid -> (top, side, bot) each TEX*TEX RGB tuples
        for bid, cols in BLOCK_COLORS.items():
            self.faces[bid] = (
                self._make(bid, cols[0], "top"),
                self._make(bid, cols[1], "side"),
                self._make(bid, cols[2], "bot"),
            )
        self.surfs = {}
        for bid, (t, s, b) in self.faces.items():
            self.surfs[bid] = (self._to_surf(t), self._to_surf(s), self._to_surf(b))

    def _to_surf(self, pixels):
        surf = pygame.Surface((TEX, TEX))
        for y in range(TEX):
            for x in range(TEX):
                surf.set_at((x, y), pixels[y * TEX + x])
        return surf

    def _make(self, bid, base, face):
        out = []
        br, bg, bb = base
        for y in range(TEX):
            for x in range(TEX):
                n = _tex_noise(x, y, bid * 17 + (0 if face == "top" else 3 if face == "side" else 7))
                n2 = _tex_noise(x * 2, y * 2, bid + 99)
                r, g, b = br, bg, bb
                # Block-specific procedural patterns (original)
                if bid == STONE:
                    v = 0.85 + 0.2 * n
                    if n2 > 0.82:
                        v *= 0.7
                    r = g = b = int(br * v)
                elif bid == COBBLESTONE or bid == MOSSY:
                    cell = ((x // 4) ^ (y // 4)) & 1
                    v = 0.75 + 0.25 * n + 0.1 * cell
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                    if bid == MOSSY and n > 0.55:
                        g = min(255, int(g * 1.35))
                elif bid == GRASS and face == "top":
                    v = 0.9 + 0.2 * n
                    r, g, b = int(br * v), int(bg * (0.95 + 0.1 * n2)), int(bb * v)
                    if n > 0.9:
                        r = min(255, r + 20)
                elif bid == DIRT or bid == FARMLAND:
                    v = 0.85 + 0.25 * n
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                    if bid == FARMLAND and y < 3:
                        r, g, b = int(r * 0.7), int(g * 0.7), int(b * 0.85)
                elif bid == WOOD and face == "side":
                    # bark stripes
                    v = 0.7 + 0.35 * abs(math.sin(x * 0.9 + n))
                    ring = 0.15 * math.sin(y * 0.8)
                    r, g, b = int(br * (v + ring)), int(bg * (v + ring)), int(bb * v)
                elif bid == WOOD:
                    # end rings
                    cx, cy = x - 7.5, y - 7.5
                    ring = math.sin(math.hypot(cx, cy) * 1.2) * 0.15
                    v = 0.85 + ring + 0.1 * n
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                elif bid == LEAVES:
                    if n < 0.35:
                        r, g, b = int(br * 0.5), int(bg * 0.5), int(bb * 0.5)
                    else:
                        v = 0.85 + 0.2 * n2
                        r, g, b = int(br * v), int(bg * v), int(bb * v)
                elif bid == SAND or bid == GRAVEL:
                    v = 0.88 + 0.2 * n
                    speck = 30 if n2 > 0.85 else 0
                    r, g, b = int(br * v) - speck, int(bg * v) - speck, int(bb * v) - speck // 2
                elif bid == WATER:
                    v = 0.75 + 0.25 * math.sin(x * 0.7 + y * 0.5) * n
                    r, g, b = int(br * v), int(bg * (0.9 + 0.1 * n)), int(min(255, bb * (1.05 - 0.1 * n)))
                elif bid == LAVA or bid == FIRE:
                    v = 0.7 + 0.4 * n
                    r = min(255, int(255 * v))
                    g = int(bg * (0.5 + 0.5 * n2))
                    b = int(20 + 40 * n)
                elif bid == BRICK:
                    mortar = (y % 4 == 0) or (x % 8 == (0 if (y // 4) & 1 else 4))
                    if mortar:
                        r, g, b = 180, 170, 160
                    else:
                        v = 0.9 + 0.15 * n
                        r, g, b = int(br * v), int(bg * v), int(bb * v)
                elif bid == PLANKS or bid == BOOKSHELF or bid == CHEST or bid == SIGN:
                    seam = (x % 8 == 0) or (y % 4 == 0 and bid != BOOKSHELF)
                    v = 0.85 + 0.2 * n
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                    if seam:
                        r, g, b = int(r * 0.65), int(g * 0.65), int(b * 0.65)
                    if bid == BOOKSHELF and 2 <= x <= 13 and y % 5 < 3:
                        r, g, b = int(90 + 40 * n), int(40 + 20 * n2), int(30 + 10 * n)
                elif bid in (COAL_ORE, IRON_ORE, GOLD_ORE, DIAMOND_ORE):
                    v = 0.85 + 0.15 * n
                    r = g = b = int(100 * v)
                    if n2 > 0.72:
                        r, g, b = br, bg, bb
                elif bid == GOLD or bid == IRON:
                    v = 0.9 + 0.15 * math.sin(x * 0.8) * math.cos(y * 0.8)
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                    if (x + y) % 4 == 0:
                        r, g, b = min(255, r + 25), min(255, g + 25), min(255, b + 25)
                elif bid == OBSIDIAN or bid == BEDROCK:
                    v = 0.6 + 0.5 * n
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                elif bid == TNT:
                    band = 4 <= y <= 11
                    r, g, b = (220, 220, 220) if band else (int(br * (0.9 + 0.1 * n)), int(bg * 0.9), int(bb * 0.9))
                    if 6 <= y <= 9 and 5 <= x <= 10:
                        r, g, b = 40, 40, 40
                elif bid == RAIL:
                    if y in (3, 4, 11, 12) or x in (2, 13):
                        r, g, b = 140, 140, 150
                    else:
                        r, g, b = int(br * 0.8), int(bg * 0.8), int(bb * 0.8)
                elif bid == GLASS:
                    v = 0.7 + 0.3 * n
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                    if x in (0, 15) or y in (0, 15):
                        r, g, b = min(255, r + 40), min(255, g + 40), min(255, b + 40)
                elif bid == SPONGE:
                    v = 0.85 + 0.2 * n
                    hole = n2 > 0.78
                    r, g, b = (40, 40, 20) if hole else (int(br * v), int(bg * v), int(bb * v))
                elif bid == TORCH:
                    if 6 <= x <= 9 and y >= 4:
                        r, g, b = (255, 220, 80) if y < 8 else (120, 80, 40)
                    else:
                        r, g, b = (30, 30, 30)
                else:
                    v = 0.88 + 0.2 * n
                    r, g, b = int(br * v), int(bg * v), int(bb * v)
                out.append(_clamp_rgb((r, g, b)))
        return out

    def sample(self, bid, face, u, v):
        """u,v in 0..1 → RGB from procedural atlas."""
        faces = self.faces.get(bid)
        if not faces:
            return (128, 128, 128)
        pix = faces[0 if face == "top" else 2 if face == "bot" else 1]
        x = int(max(0, min(TEX - 1, u * (TEX - 1))))
        y = int(max(0, min(TEX - 1, v * (TEX - 1))))
        return pix[y * TEX + x]


ATLAS = None  # built after pygame.init


def get_atlas():
    global ATLAS
    if ATLAS is None:
        ATLAS = TexAtlas()
    return ATLAS


# ---------------------------------------------------------------------------
# Infdev mobs (simple entities — original cube models, files=off)
# ---------------------------------------------------------------------------
class Mob:
    __slots__ = ("kind", "x", "y", "z", "yaw", "timer", "hp", "saddled")

    def __init__(self, kind, x, y, z):
        self.kind = kind  # pig | sheep | creeper
        self.x, self.y, self.z = float(x), float(y), float(z)
        self.yaw = random.random() * math.pi * 2
        self.timer = random.random() * 3
        self.hp = 10 if kind != "creeper" else 20
        self.saddled = False

    def color(self):
        if self.kind == "pig":
            return (255, 160, 170)
        if self.kind == "sheep":
            return (240, 240, 240)
        return (40, 180, 40)  # creeper


class Minecart:
    """Infdev minecart — rides rails (Seecret Friday vibe), files=off entity."""
    __slots__ = ("x", "y", "z", "vx", "vz", "yaw")

    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)
        self.vx = self.vz = 0.0
        self.yaw = 0.0


# ---------------------------------------------------------------------------
# Procedural Audio (files = off)
# Math OST: ambient "Sweden"-style loop — original sine/pad synth from note math.
# No copyrighted audio assets; melody intervals are public educational note names.
# ---------------------------------------------------------------------------
def _midi_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


# Soft piano-ish motif (D major / B dorian ambient) — beat units at ~88 BPM
# Format: (midi_or_None, duration_in_beats)
_SWEDEN_MELODY = [
    # phrase A
    (59, 2), (66, 2), (61, 2), (64, 2),
    (59, 1), (69, 1), (71, 1), (66, 1), (62, 1), (64, 1), (0, 2),
    (61, 1), (66, 1), (69, 1), (64, 1), (0, 4),
    # phrase B
    (59, 1), (74, 1), (71, 1), (69, 1), (66, 1), (62, 1), (64, 1), (0, 1),
    (61, 1), (69, 1), (66, 1), (64, 1), (0, 4),
    (59, 1), (69, 1), (71, 1), (74, 1), (62, 1), (64, 1), (0, 2),
    (73, 1), (74, 1), (73, 1), (69, 1), (0, 4),
    # phrase A′
    (59, 1), (71, 1), (69, 1), (66, 1), (62, 1), (64, 1), (0, 2),
    (61, 1), (66, 1), (69, 1), (64, 1), (0, 4),
    (59, 1), (69, 1), (71, 1), (66, 1), (62, 1), (64, 1), (0, 2),
    (61, 1), (66, 1), (69, 1), (64, 1), (0, 4),
    # lift
    (59, 1), (69, 1), (71, 1), (74, 1), (74, 1), (76, 1), (0, 2),
    (73, 1), (78, 1), (66, 1), (69, 1), (64, 1), (0, 3),
    (66, 1), (71, 1), (69, 1), (68, 1), (64, 1), (62, 1), (0, 2),
    (61, 1), (62, 1), (64, 1), (59, 1), (0, 4),
]

# Pad chords (root midi triad), 8 beats each — Bm / F#m / G / D loop feel
_SWEDEN_PADS = [
    (47, 51, 54),  # B2 D3 F#3
    (42, 46, 49),  # F#2 A#2 C#3 (soft)
    (43, 47, 50),  # G2 B2 D3
    (38, 42, 45),  # D2 F#2 A2
]


class SoundEngine:
    def __init__(self):
        self.enabled = True
        self.sr = 22050
        self.music_on = True
        self.music = None
        self.music_ch = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(self.sr, -16, 1, 1024)
            self.sr = pygame.mixer.get_init()[0] or 22050
            pygame.mixer.set_num_channels(16)
            self.music_ch = pygame.mixer.Channel(0)
        except pygame.error:
            self.enabled = False
        self.sfx = {}
        if self.enabled:
            self.sfx["place"] = self._thud(180, 320, 0.06, 0.35)
            self.sfx["break"] = self._crunch(0.11, 0.4)
            self.sfx["step"] = self._crunch(0.035, 0.14)
            self.sfx["jump"] = self._thud(140, 260, 0.07, 0.22)
            self.sfx["select"] = self._thud(640, 720, 0.02, 0.18)
            self.sfx["splash"] = self._thud(90, 160, 0.09, 0.28)
            self.sfx["door"] = self._thud(220, 180, 0.05, 0.25)
            self.music = self._build_sweden_ost()
            self.start_music()

    def _buf(self, samples: array.array) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _thud(self, f0, f1, dur, vol):
        n = max(1, int(self.sr * dur))
        amp = int(28000 * vol)
        data = array.array("h")
        phase = 0.0
        for i in range(n):
            t = i / n
            freq = f0 + (f1 - f0) * t
            phase += 2.0 * math.pi * freq / self.sr
            env = 1.0 - t
            data.append(int(amp * env * (1.0 if math.sin(phase) >= 0 else -1.0)))
        return self._buf(data)

    def _crunch(self, dur, vol):
        n = max(1, int(self.sr * dur))
        amp = int(25000 * vol)
        data = array.array("h")
        last = 0
        for i in range(n):
            env = (1.0 - i / n) ** 1.4
            if i % 3 == 0:
                last = random.randint(-amp, amp)
            data.append(int(last * env))
        return self._buf(data)

    def _env_adsr(self, i: int, n: int, a=0.08, d=0.18, s=0.55, r=0.35) -> float:
        if n <= 1:
            return 0.0
        t = i / n
        if t < a:
            return t / a
        if t < a + d:
            return 1.0 - (1.0 - s) * ((t - a) / d)
        if t < 1.0 - r:
            return s
        return s * max(0.0, (1.0 - t) / r)

    def _build_sweden_ost(self) -> pygame.mixer.Sound:
        """Procedural ambient loop — math-only synth, files=off."""
        bpm = 88.0
        beat = 60.0 / bpm
        # Mix buffer as floats
        total_beats = sum(d for _, d in _SWEDEN_MELODY)
        # pad one extra bar for loop seam
        total_beats = max(total_beats, 64)
        n = int(self.sr * beat * total_beats)
        buf = [0.0] * n

        # Soft low pad bed
        pad_beats = 8.0
        pad_len = int(self.sr * beat * pad_beats)
        t0 = 0
        pi = 0
        while t0 < n:
            chord = _SWEDEN_PADS[pi % len(_SWEDEN_PADS)]
            slen = min(pad_len, n - t0)
            for j, midi in enumerate(chord):
                hz = _midi_hz(midi)
                phase = 0.0
                det = 1.0 + (j - 1) * 0.0015
                for i in range(slen):
                    env = self._env_adsr(i, slen, 0.25, 0.2, 0.7, 0.35)
                    # warm sine + quiet 2nd partial
                    s = math.sin(phase) + 0.18 * math.sin(phase * 2.0)
                    buf[t0 + i] += s * env * 0.09
                    phase += 2.0 * math.pi * hz * det / self.sr
            t0 += pad_len
            pi += 1

        # Lead melody — soft sine “piano”
        cursor = 0.0
        for midi, beats in _SWEDEN_MELODY:
            start = int(cursor * self.sr * beat)
            length = int(beats * self.sr * beat)
            if midi and length > 0:
                hz = _midi_hz(midi)
                phase = 0.0
                phase2 = 0.0
                for i in range(length):
                    if start + i >= n:
                        break
                    env = self._env_adsr(i, length, 0.02, 0.12, 0.45, 0.4)
                    # gentle bell-ish partials
                    s = (
                        math.sin(phase)
                        + 0.35 * math.sin(phase2)
                        + 0.08 * math.sin(phase * 3.01)
                    )
                    # soft velocity swell across phrase
                    buf[start + i] += s * env * 0.22
                    phase += 2.0 * math.pi * hz / self.sr
                    phase2 += 2.0 * math.pi * (hz * 2.003) / self.sr
            cursor += beats

        # Very quiet shimmer / air
        for i in range(n):
            t = i / self.sr
            buf[i] += 0.012 * math.sin(2.0 * math.pi * 0.07 * t) * math.sin(2.0 * math.pi * 220.0 * t)

        # Normalize + soft clip
        peak = max(1e-6, max(abs(x) for x in buf))
        gain = 0.55 * 28000.0 / peak
        data = array.array("h")
        for x in buf:
            v = int(max(-32000, min(32000, x * gain)))
            data.append(v)
        snd = self._buf(data)
        snd.set_volume(0.38)
        return snd

    def start_music(self):
        if not self.enabled or not self.music or not self.music_ch:
            return
        self.music_on = True
        self.music_ch.play(self.music, loops=-1)
        self.music_ch.set_volume(0.38)

    def stop_music(self):
        self.music_on = False
        if self.music_ch:
            self.music_ch.stop()

    def toggle_music(self):
        if not self.enabled or not self.music:
            return
        if self.music_on:
            self.stop_music()
        else:
            self.start_music()

    def play(self, name: str):
        if self.enabled and name in self.sfx:
            # sfx on free channels (1+)
            self.sfx[name].play()


# ---------------------------------------------------------------------------
# Noise helpers (Infdev-style layered height)
# ---------------------------------------------------------------------------
def _hash2(x: int, z: int, seed: int) -> float:
    n = (x * 374761393 + z * 668265263 + seed * 982451653) & 0x7FFFFFFF
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0x7FFFFFFF) / 2147483647.0


def _smooth_noise(x: float, z: float, seed: int) -> float:
    xi, zi = int(math.floor(x)), int(math.floor(z))
    xf, zf = x - xi, z - zi
    u = xf * xf * (3 - 2 * xf)
    v = zf * zf * (3 - 2 * zf)
    n00 = _hash2(xi, zi, seed)
    n10 = _hash2(xi + 1, zi, seed)
    n01 = _hash2(xi, zi + 1, seed)
    n11 = _hash2(xi + 1, zi + 1, seed)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def _fbm(x: float, z: float, seed: int, octaves: int = 4) -> float:
    amp, freq, total, norm = 1.0, 1.0, 0.0, 0.0
    for i in range(octaves):
        total += _smooth_noise(x * freq, z * freq, seed + i * 1013) * amp
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


# ---------------------------------------------------------------------------
# Infdev Chunked World
# ---------------------------------------------------------------------------
class VoxelWorld:
    def __init__(self, seed: int = XBOX_DEMO_SEED):
        # Seed is always an in-memory int — never read/written from disk (files=off).
        self.seed = int(seed) & 0x7FFFFFFFFFFFFFFF
        self.blocks: dict[tuple[int, int, int], int] = {}
        self.meta: dict[tuple[int, int, int], int] = {}  # fluid level / door open
        self.loaded: set[tuple[int, int]] = set()
        self.chunk_faces: dict[tuple[int, int], list] = {}
        self.exposed_faces: list = []
        self.fluid_q: deque = deque()
        self.fall_q: deque = deque()
        self.fire_q: deque = deque()
        self.tnt_fuse: list = []  # (pos, time_left)
        self.mobs: list = []
        self.carts: list = []
        self.furnaces: dict = {}  # pos -> smelt progress
        self.tick_acc = 0.0
        self.grass_acc = 0.0
        self.life_acc = 0.0
        self.xbox_demo_stamped = False

    def get(self, pos) -> int:
        return self.blocks.get(pos, AIR)

    def solid_at(self, pos) -> bool:
        b = self.get(pos)
        if b == DOOR and self.meta.get(pos, 0):
            return False
        return b in SOLID

    def fluid_at(self, pos) -> int:
        b = self.get(pos)
        return b if b in FLUID else AIR

    def _chunk_key(self, x: int, z: int) -> tuple[int, int]:
        return x >> 4, z >> 4

    def ensure_around(self, px: float, pz: float):
        cx, cz = int(math.floor(px)) >> 4, int(math.floor(pz)) >> 4
        needed = {(cx + dx, cz + dz)
                  for dx in range(-LOAD_R, LOAD_R + 1)
                  for dz in range(-LOAD_R, LOAD_R + 1)}
        dirty = False
        for c in needed - self.loaded:
            self._gen_chunk(c[0], c[1])
            dirty = True
        for c in list(self.loaded - needed):
            self._unload_chunk(c[0], c[1])
            dirty = True
        if dirty:
            self._rebuild_all_faces()

    def _unload_chunk(self, cx: int, cz: int):
        x0, z0 = cx * CHUNK, cz * CHUNK
        for x in range(x0, x0 + CHUNK):
            for z in range(z0, z0 + CHUNK):
                for y in range(WORLD_Y):
                    pos = (x, y, z)
                    self.blocks.pop(pos, None)
                    self.meta.pop(pos, None)
        self.loaded.discard((cx, cz))
        self.chunk_faces.pop((cx, cz), None)
        self.mobs = [m for m in self.mobs
                     if not (x0 <= int(m.x) < x0 + CHUNK and z0 <= int(m.z) < z0 + CHUNK)]
        self.carts = [c for c in self.carts
                      if not (x0 <= int(c.x) < x0 + CHUNK and z0 <= int(c.z) < z0 + CHUNK)]
        # Demo compound lives near (0,-3); allow re-stamp if those chunks unload
        if cx in (-1, 0, 1) and cz in (-4, -3, -2):
            self.xbox_demo_stamped = False

    def _height(self, x: int, z: int) -> int:
        # Infdev / early Alpha-ish dual height blend (Notchy-style)
        n1 = _fbm(x * 0.02, z * 0.02, self.seed, 5)
        n2 = _fbm(x * 0.06 + 40, z * 0.06 - 20, self.seed + 7, 3)
        h = SEA_LEVEL + (n1 - 0.45) * 18.0 + (n2 - 0.5) * 6.0
        # Flatten Xbox demo tutorial bowl around published spawn (3, -37)
        dx = x - 3
        dz = z + 37
        if dx * dx + dz * dz < 22 * 22:
            h = SEA_LEVEL + 2 + int((n1 - 0.5) * 1.5)
        # Far Lands — overflow-style terrain breakdown (scaled Infdev algorithm)
        ax, az = abs(x), abs(z)
        if ax > FAR_LANDS or az > FAR_LANDS:
            # Classic Far Lands: noise amplitude explodes / wraps
            overflow = ((x * 0.002 + 1e6) % 1.0) + ((z * 0.002 + 1e6) % 1.0)
            wall = math.sin(x * 0.31) * math.cos(z * 0.29) * 40.0
            h = SEA_LEVEL + 8 + wall + overflow * 25.0 * math.sin(x * 0.07 + z * 0.05)
            h += (n1 - 0.5) * 50.0
        return max(2, min(WORLD_Y - 2, int(h)))

    def _gen_chunk(self, cx: int, cz: int):
        rnd = random.Random((self.seed * 73856093) ^ (cx * 19349663) ^ (cz * 83492791))
        x0, z0 = cx * CHUNK, cz * CHUNK
        heights = {}

        # Heightmap + strata (Classic/Notchy surface stack)
        for lx in range(CHUNK):
            for lz in range(CHUNK):
                x, z = x0 + lx, z0 + lz
                h = self._height(x, z)
                heights[(x, z)] = h
                self.blocks[(x, BEDROCK_Y, z)] = BEDROCK
                for y in range(1, h + 1):
                    if y == h:
                        if h < SEA_LEVEL - 1:
                            self.blocks[(x, y, z)] = SAND if rnd.random() < 0.7 else GRAVEL
                        else:
                            self.blocks[(x, y, z)] = GRASS
                    elif y >= h - 3:
                        self.blocks[(x, y, z)] = DIRT
                    else:
                        self.blocks[(x, y, z)] = STONE
                # Sea flood
                for y in range(h + 1, SEA_LEVEL + 1):
                    if (x, y, z) not in self.blocks:
                        self.blocks[(x, y, z)] = WATER
                        self.meta[(x, y, z)] = 0

        # Caves — ClassiCube NotchyGen_CarveCaves worm (scaled per chunk)
        vol = CHUNK * CHUNK * WORLD_Y
        caves = max(1, vol // 9000)
        for _ in range(caves):
            cave_x = x0 + rnd.random() * CHUNK
            cave_y = rnd.random() * (WORLD_Y - 4) + 2
            cave_z = z0 + rnd.random() * CHUNK
            cave_len = int((rnd.random() + rnd.random()) * 40)
            theta = rnd.random() * math.pi * 2
            phi = rnd.random() * math.pi * 2
            d_theta = d_phi = 0.0
            cave_r = rnd.random() * rnd.random()
            for j in range(cave_len):
                cave_x += math.sin(theta) * math.cos(phi)
                cave_z += math.cos(theta) * math.cos(phi)
                cave_y += math.sin(phi)
                theta += d_theta * 0.2
                d_theta = d_theta * 0.9 + rnd.random() - rnd.random()
                phi = phi * 0.5 + d_phi * 0.25
                d_phi = d_phi * 0.75 + rnd.random() - rnd.random()
                if rnd.random() < 0.25:
                    continue
                radius = 1.0 + cave_r * 2.2
                radius *= math.sin(j * math.pi / max(1, cave_len))
                self._carve_sphere(int(cave_x), int(cave_y), int(cave_z), radius, rnd)

        # Ore veins — NotchyGen_CarveOreVeins abundances
        self._ore_veins(x0, z0, rnd, COAL_ORE, 0.9)
        self._ore_veins(x0, z0, rnd, IRON_ORE, 0.7)
        self._ore_veins(x0, z0, rnd, GOLD_ORE, 0.5)
        self._ore_veins(x0, z0, rnd, DIAMOND_ORE, 0.35)

        # Underground gravel/dirt pockets (Infdev cave variety)
        for _ in range(8):
            px = x0 + rnd.randint(1, CHUNK - 2)
            pz = z0 + rnd.randint(1, CHUNK - 2)
            py = rnd.randint(2, SEA_LEVEL - 2)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    for dz in range(-1, 2):
                        pos = (px + dx, py + dy, pz + dz)
                        if self.get(pos) == STONE and rnd.random() < 0.55:
                            self.blocks[pos] = GRAVEL if rnd.random() < 0.5 else DIRT

        # Surface springs (Infdev water/lava)
        if rnd.random() < 0.35:
            sx = x0 + rnd.randint(2, CHUNK - 3)
            sz = z0 + rnd.randint(2, CHUNK - 3)
            sy = heights.get((sx, sz), SEA_LEVEL)
            if sy > 3 and self.get((sx, sy, sz)) in (STONE, DIRT, GRASS):
                self.blocks[(sx, sy, sz)] = WATER if rnd.random() < 0.85 else LAVA
                self.meta[(sx, sy, sz)] = 0
                self.fluid_q.append((sx, sy, sz))

        # Trees on grass above sea
        for _ in range(3):
            tx = x0 + rnd.randint(2, CHUNK - 3)
            tz = z0 + rnd.randint(2, CHUNK - 3)
            ty = heights.get((tx, tz), 0)
            if ty > SEA_LEVEL and self.get((tx, ty, tz)) == GRASS:
                self._grow_tree(tx, ty, tz, rnd)

        # Flowers / saplings
        for _ in range(4):
            fx = x0 + rnd.randint(1, CHUNK - 2)
            fz = z0 + rnd.randint(1, CHUNK - 2)
            fy = heights.get((fx, fz), 0)
            if fy > SEA_LEVEL and self.get((fx, fy, fz)) == GRASS and self.get((fx, fy + 1, fz)) == AIR:
                self.blocks[(fx, fy + 1, fz)] = FLOWER if rnd.random() < 0.7 else SAPLING

        # Mushrooms in dark / under leaves (Indev→Infdev flora)
        for _ in range(2):
            mx = x0 + rnd.randint(1, CHUNK - 2)
            mz = z0 + rnd.randint(1, CHUNK - 2)
            my = heights.get((mx, mz), 0)
            if my > 1 and self.get((mx, my + 1, mz)) == AIR and rnd.random() < 0.5:
                self.blocks[(mx, my + 1, mz)] = MUSHROOM

        # Early Infdev brick pyramids — fixed lattice independent of seed
        self._maybe_brick_pyramid(cx, cz)
        # Obsidian wall markers along X multiples of 256 (Infdev test structure vibe)
        self._maybe_obsidian_wall(cx, cz)
        # Monster room / dungeon
        if rnd.random() < 0.08:
            self._place_dungeon(x0, z0, rnd)

        # Surface mobs (Infdev-era animals / creeper)
        if rnd.random() < 0.45:
            mx = x0 + rnd.randint(2, CHUNK - 3)
            mz = z0 + rnd.randint(2, CHUNK - 3)
            my = heights.get((mx, mz), SEA_LEVEL) + 1
            kind = rnd.choice(("pig", "sheep", "pig", "sheep", "creeper"))
            if my < WORLD_Y - 2 and my > SEA_LEVEL:
                self.mobs.append(Mob(kind, mx + 0.5, my, mz + 0.5))

        self.loaded.add((cx, cz))

    def _carve_sphere(self, cx, cy, cz, radius, rnd):
        r = int(radius) + 1
        r2 = radius * radius
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if dx * dx + dy * dy * 1.4 + dz * dz > r2:
                        continue
                    x, y, z = cx + dx, cy + dy, cz + dz
                    if y <= BEDROCK_Y or y >= WORLD_Y:
                        continue
                    pos = (x, y, z)
                    b = self.get(pos)
                    if b in (STONE, DIRT, GRASS, GRAVEL, COAL_ORE, IRON_ORE, GOLD_ORE, DIAMOND_ORE):
                        del self.blocks[pos]
                        self.meta.pop(pos, None)

    def _ore_veins(self, x0, z0, rnd, block, abundance):
        vol = CHUNK * CHUNK * WORLD_Y
        n = max(1, int(vol * abundance / 14000))
        for _ in range(n):
            vx = x0 + rnd.random() * CHUNK
            vy = 2 + rnd.random() * (SEA_LEVEL + 4)
            vz = z0 + rnd.random() * CHUNK
            length = int(rnd.random() * rnd.random() * 28 * abundance) + 2
            theta = rnd.random() * math.pi * 2
            phi = rnd.random() * math.pi * 2
            d_theta = d_phi = 0.0
            for j in range(length):
                vx += math.sin(theta) * math.cos(phi)
                vz += math.cos(theta) * math.cos(phi)
                vy += math.sin(phi)
                theta = d_theta * 0.2
                d_theta = d_theta * 0.9 + rnd.random() - rnd.random()
                phi = phi * 0.5 + d_phi * 0.25
                d_phi = d_phi * 0.9 + rnd.random() - rnd.random()
                radius = abundance * math.sin(j * math.pi / max(1, length)) + 1.0
                ir = int(radius)
                for dx in range(-ir, ir + 1):
                    for dy in range(-ir, ir + 1):
                        for dz in range(-ir, ir + 1):
                            if dx * dx + dy * dy + dz * dz > radius * radius:
                                continue
                            pos = (int(vx) + dx, int(vy) + dy, int(vz) + dz)
                            if self.get(pos) == STONE:
                                self.blocks[pos] = block

    def _grow_tree(self, tx, ty, tz, rnd):
        h = rnd.randint(4, 6)
        if ty + h + 2 >= WORLD_Y:
            return
        self.blocks[(tx, ty, tz)] = DIRT
        for y in range(1, h):
            self.blocks[(tx, ty + y, tz)] = WOOD
        for ly in range(h - 2, h + 1):
            rad = 1 if ly >= h - 1 else 2
            for lx in range(-rad, rad + 1):
                for lz in range(-rad, rad + 1):
                    if abs(lx) == rad and abs(lz) == rad and (ly == h or rnd.random() < 0.45):
                        continue
                    pos = (tx + lx, ty + ly, tz + lz)
                    if self.get(pos) == AIR:
                        self.blocks[pos] = LEAVES

    def _maybe_brick_pyramid(self, cx, cz):
        # Predetermined Infdev lattice (~every 8 chunks)
        if cx % 8 != 2 or cz % 8 != 2:
            return
        bx, bz = cx * CHUNK + 8, cz * CHUNK + 8
        base_y = max(SEA_LEVEL, self._height(bx, bz))
        size = 12
        for y in range(size):
            s = size - y
            for dx in range(-s, s + 1):
                for dz in range(-s, s + 1):
                    if abs(dx) == s or abs(dz) == s or y == 0:
                        py = base_y + y
                        if py < WORLD_Y:
                            pos = (bx + dx, py, bz + dz)
                            if self.get(pos) in (AIR, WATER, LEAVES, SAPLING, FLOWER):
                                self.blocks[pos] = BRICK
                                self.meta.pop(pos, None)

    def _maybe_obsidian_wall(self, cx, cz):
        # Thin Infdev-style obsidian wall along world X = 0 plane segments
        if cx != 0:
            return
        x = 0
        z0 = cz * CHUNK
        for z in range(z0, z0 + CHUNK):
            for y in range(1, min(WORLD_Y - 1, SEA_LEVEL + 8)):
                if self.get((x, y, z)) in (AIR, WATER):
                    self.blocks[(x, y, z)] = OBSIDIAN

    def _place_dungeon(self, x0, z0, rnd):
        dx = x0 + rnd.randint(3, CHUNK - 6)
        dz = z0 + rnd.randint(3, CHUNK - 6)
        dy = rnd.randint(3, max(4, SEA_LEVEL - 4))
        for x in range(dx, dx + 5):
            for y in range(dy, dy + 4):
                for z in range(dz, dz + 5):
                    edge = (x in (dx, dx + 4) or y in (dy, dy + 3) or z in (dz, dz + 4))
                    if edge:
                        self.blocks[(x, y, z)] = MOSSY if rnd.random() < 0.4 else COBBLESTONE
                    else:
                        self.blocks.pop((x, y, z), None)
                        self.meta.pop((x, y, z), None)
        # Monster spawner + chest loot (Infdev dungeon)
        self.blocks[(dx + 2, dy + 1, dz + 2)] = SPAWNER
        self.blocks[(dx + 3, dy + 1, dz + 2)] = CHEST
        self.blocks[(dx + 3, dy + 2, dz + 2)] = GOLD

    def _surface_y(self, x: int, z: int) -> int:
        for y in range(WORLD_Y - 1, 0, -1):
            if self.solid_at((x, y, z)):
                return y
        return SEA_LEVEL

    def _fill(self, pos, btype: int):
        x, y, z = pos
        if y <= BEDROCK_Y or y >= WORLD_Y:
            return
        if btype == AIR:
            self.blocks.pop(pos, None)
            self.meta.pop(pos, None)
        else:
            self.blocks[pos] = btype
            self.meta.pop(pos, None)

    def stamp_xbox_demo_spawn(self):
        """
        Procedural Xbox 360 TU0 / Demo tutorial compound (files=off).
        Recreates the enclosed starter bowl + incomplete miner shelter near
        published spawn (3, -37), facing the south exit — no map files used.
        """
        if self.xbox_demo_stamped:
            return
        self.xbox_demo_stamped = True
        ox, oz = 3, -37
        # Ensure chunks covering the compound (RAM gen only — files=off)
        for cx in range(-2, 2):
            for cz in range(-4, -1):
                if (cx, cz) not in self.loaded:
                    self._gen_chunk(cx, cz)
        base = self._surface_y(ox, oz)
        # Flatten pad
        for dx in range(-10, 11):
            for dz in range(-10, 11):
                x, z = ox + dx, oz + dz
                sy = self._surface_y(x, z)
                for y in range(sy + 1, base + 8):
                    self._fill((x, y, z), AIR)
                for y in range(1, base):
                    if not self.solid_at((x, y, z)):
                        self._fill((x, y, z), STONE if y < base - 2 else DIRT)
                self._fill((x, base, z), GRASS)
                self._fill((x, base + 1, z), AIR)

        # Natural enclosure wall (tutorial cage)
        for dx in range(-9, 10):
            for dz in range(-9, 10):
                if max(abs(dx), abs(dz)) != 9:
                    continue
                x, z = ox + dx, oz + dz
                # South gate opening
                if dz == 9 and abs(dx) <= 1:
                    continue
                for y in range(base + 1, base + 5):
                    self._fill((x, y, z), STONE if (dx + dz + y) & 1 else DIRT)
                self._fill((x, base + 5, z), GRASS)

        # Incomplete miner's shelter (classic Xbox demo vibe)
        hx, hz = ox - 3, oz - 2
        for dx in range(0, 5):
            for dz in range(0, 5):
                self._fill((hx + dx, base, hz + dz), COBBLESTONE)
                # walls — leave south face open / incomplete
                edge = dx in (0, 4) or dz == 0
                if edge and not (dz == 4 and 1 <= dx <= 3):
                    self._fill((hx + dx, base + 1, hz + dz), COBBLESTONE)
                    if not (dx == 4 and dz == 2):  # missing wall section
                        self._fill((hx + dx, base + 2, hz + dz), WOOD if dx == 0 else COBBLESTONE)
                # partial roof
                if not (dx == 2 and dz == 2):
                    self._fill((hx + dx, base + 3, hz + dz), PLANKS)
                else:
                    self._fill((hx + dx, base + 3, hz + dz), AIR)  # hole in roof

        # Interior props: chest, furnace stand-in, crafting table stand-in, ladder
        self._fill((hx + 1, base + 1, hz + 1), CHEST)
        self._fill((hx + 1, base + 2, hz + 1), GOLD)          # "loot" marker
        self._fill((hx + 3, base + 1, hz + 1), BRICK)         # furnace
        self._fill((hx + 2, base + 1, hz + 1), PLANKS)        # crafting table
        self._fill((hx + 4, base + 1, hz + 3), LADDER)
        self._fill((hx + 4, base + 2, hz + 3), LADDER)

        # Tutorial path to south gate
        for z in range(oz - 1, oz + 10):
            self._fill((ox, base, z), GRAVEL)
            self._fill((ox, base + 1, z), AIR)

        # Torches as gold pillars at gate
        self._fill((ox - 2, base + 1, oz + 8), WOOD)
        self._fill((ox - 2, base + 2, oz + 8), GOLD)
        self._fill((ox + 2, base + 1, oz + 8), WOOD)
        self._fill((ox + 2, base + 2, oz + 8), GOLD)

        # Small farm patch
        for dx in range(2, 6):
            for dz in range(-6, -3):
                self._fill((ox + dx, base, oz + dz), DIRT)
                if (dx + dz) & 1:
                    self._fill((ox + dx, base + 1, oz + dz), FLOWER)

        # Twin oak trees inside enclosure (TU forest feel)
        for tx, tz in ((ox + 5, oz + 3), (ox - 6, oz - 5)):
            self._fill((tx, base, tz), DIRT)
            for y in range(1, 5):
                self._fill((tx, base + y, tz), WOOD)
            for lx in range(-2, 3):
                for ly in range(3, 6):
                    for lz in range(-2, 3):
                        if abs(lx) == 2 and abs(lz) == 2 and ly == 5:
                            continue
                        pos = (tx + lx, base + ly, tz + lz)
                        if self.get(pos) == AIR:
                            self._fill(pos, LEAVES)

        # Mini lighthouse stub east of compound (TU1 tutorial landmark tease)
        lx, lz = ox + 18, oz + 4
        ly0 = self._surface_y(lx, lz)
        for y in range(ly0 + 1, ly0 + 8):
            self._fill((lx, y, lz), BRICK)
            self._fill((lx + 1, y, lz), BRICK)
            self._fill((lx, y, lz + 1), BRICK)
            self._fill((lx + 1, y, lz + 1), BRICK)
        self._fill((lx, ly0 + 8, lz), GOLD)
        self._fill((lx + 1, ly0 + 8, lz), GOLD)

        self._rebuild_all_faces()

    def _rebuild_chunk_faces(self, cx: int, cz: int):
        faces = []
        x0, z0 = cx * CHUNK, cz * CHUNK
        blocks = self.blocks
        atlas = get_atlas()
        for x in range(x0, x0 + CHUNK):
            for z in range(z0, z0 + CHUNK):
                for y in range(WORLD_Y):
                    pos = (x, y, z)
                    btype = blocks.get(pos)
                    if not btype or btype == AIR:
                        continue
                    if btype == DOOR and self.meta.get(pos, 0):
                        continue
                    tint = 0.96 if (x + y + z) & 1 else 1.02
                    for nx, ny, nz, verts, shade, is_top, is_bot in CUBE_FACES:
                        npos = (x + nx, y + ny, z + nz)
                        nb = blocks.get(npos, AIR)
                        if nb == DOOR and self.meta.get(npos, 0):
                            nb = AIR
                        if nb in SOLID and nb not in TRANSPARENT:
                            continue
                        if btype in FLUID and nb == btype:
                            continue
                        face = "top" if is_top else ("bot" if is_bot else "side")
                        # Procedural atlas sample (4 taps averaged) — Infdev texture look
                        tc = [0, 0, 0]
                        for u, v in ((0.2, 0.2), (0.8, 0.2), (0.2, 0.8), (0.8, 0.8)):
                            s = atlas.sample(btype, face, u, v)
                            tc[0] += s[0]; tc[1] += s[1]; tc[2] += s[2]
                        tc = (tc[0] // 4, tc[1] // 4, tc[2] // 4)
                        mul = shade * tint
                        if btype in FLUID:
                            mul *= 0.85
                        if btype in (TORCH, FIRE):
                            mul *= 1.25
                        col = (
                            min(255, int(tc[0] * mul)),
                            min(255, int(tc[1] * mul)),
                            min(255, int(tc[2] * mul)),
                        )
                        w_verts = [(x + vx, y + vy, z + vz) for vx, vy, vz in verts]
                        faces.append((
                            x + 0.5 + nx * 0.5, y + 0.5 + ny * 0.5, z + 0.5 + nz * 0.5,
                            nx, ny, nz, w_verts, col, pos, btype,
                        ))
        self.chunk_faces[(cx, cz)] = faces

    def _rebuild_all_faces(self):
        for cx, cz in self.loaded:
            self._rebuild_chunk_faces(cx, cz)
        self._concat_faces()

    def _concat_faces(self):
        out = []
        for faces in self.chunk_faces.values():
            out.extend(faces)
        self.exposed_faces = out

    def _dirty_near(self, pos):
        cx, cz = self._chunk_key(pos[0], pos[2])
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                key = (cx + dx, cz + dz)
                if key in self.loaded:
                    self._rebuild_chunk_faces(*key)
        self._concat_faces()

    def set_block(self, pos, btype: int) -> bool:
        x, y, z = pos
        if y <= BEDROCK_Y or y >= WORLD_Y:
            return False
        if btype == AIR:
            cur = self.get(pos)
            if cur == BEDROCK or cur == AIR:
                return False
            # Door toggle on punch? break instead
            del self.blocks[pos]
            self.meta.pop(pos, None)
            # Schedule fluid/fall updates
            for n in ((x, y + 1, z), (x + 1, y, z), (x - 1, y, z), (x, y, z + 1), (x, y, z - 1), (x, y - 1, z)):
                if self.get(n) in FLUID:
                    self.fluid_q.append(n)
                if self.get(n) in FALLING:
                    self.fall_q.append(n)
            self.fall_q.append((x, y + 1, z))
            self._dirty_near(pos)
            return True

        if self.get(pos) not in REPLACEABLE and self.get(pos) != AIR:
            return False
        self.blocks[pos] = btype
        if btype in FLUID:
            self.meta[pos] = 0
            self.fluid_q.append(pos)
        elif btype in FALLING:
            self.fall_q.append(pos)
        elif btype == FIRE:
            self.fire_q.append(pos)
            self.meta.pop(pos, None)
        elif btype == TNT:
            self.meta.pop(pos, None)
            self.tnt_fuse.append([pos[0], pos[1], pos[2], 3.0])  # auto-prime on place
        elif btype == SPONGE:
            self.meta.pop(pos, None)
            self._sponge_soak(pos)
        elif btype == DIRT:
            # hoe vibe: dirt under air near water → farmland chance later
            self.meta.pop(pos, None)
        else:
            self.meta.pop(pos, None)
        self._dirty_near(pos)
        return True

    def _sponge_soak(self, pos):
        # Classic sponge: clear nearby water
        x, y, z = pos
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for dz in range(-3, 4):
                    p = (x + dx, y + dy, z + dz)
                    if self.get(p) == WATER:
                        self.blocks.pop(p, None)
                        self.meta.pop(p, None)
        self._dirty_near(pos)

    def ignite(self, pos) -> bool:
        """Start fire or prime TNT (Infdev fire / TNT)."""
        b = self.get(pos)
        if b == TNT:
            self.tnt_fuse.append([pos[0], pos[1], pos[2], 2.5])
            return True
        if b in FLAMMABLE or b == AIR:
            above = (pos[0], pos[1] + 1, pos[2])
            if self.get(above) == AIR:
                self.blocks[above] = FIRE
                self.fire_q.append(above)
                self._dirty_near(above)
                return True
            if b in FLAMMABLE:
                self.blocks[pos] = FIRE
                self.fire_q.append(pos)
                self._dirty_near(pos)
                return True
        return False

    def explode(self, pos, radius: float = 3.2):
        x, y, z = pos
        r = int(radius) + 1
        r2 = radius * radius
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if dx * dx + dy * dy + dz * dz > r2:
                        continue
                    p = (x + dx, y + dy, z + dz)
                    b = self.get(p)
                    if b in (BEDROCK, AIR):
                        continue
                    self.blocks.pop(p, None)
                    self.meta.pop(p, None)
                    if random.random() < 0.15 and b in FLAMMABLE:
                        self.blocks[p] = FIRE
                        self.fire_q.append(p)
        self._dirty_near(pos)

    def toggle_door(self, pos) -> bool:
        if self.get(pos) != DOOR:
            return False
        self.meta[pos] = 0 if self.meta.get(pos, 0) else 1
        self._dirty_near(pos)
        return True

    def tick(self, dt: float):
        self.tick_acc += dt
        # ~10 fluid ticks / sec (Infdev pending tile ticks vibe)
        while self.tick_acc >= 0.1:
            self.tick_acc -= 0.1
            self._tick_fluids(48)
            self._tick_falling(24)
            self._tick_fire(20)

        self.grass_acc += dt
        if self.grass_acc >= 1.2:
            self.grass_acc = 0.0
            self._tick_grass(12)
            self._tick_saplings(6)
            self._tick_wheat(8)

        # TNT fuse
        alive = []
        for item in self.tnt_fuse:
            item[3] -= dt
            if item[3] <= 0:
                pos = (item[0], item[1], item[2])
                if self.get(pos) == TNT:
                    self.blocks.pop(pos, None)
                    self.explode(pos, 3.4)
            else:
                alive.append(item)
        self.tnt_fuse = alive

        self.life_acc += dt
        if self.life_acc >= 0.2:
            self.life_acc = 0.0
            self._tick_mobs(0.2)
            self._tick_carts(0.2)
            self._tick_spawners()
            self._tick_furnaces()

    def _tick_fluids(self, budget: int):
        # Simplified Infdev liquid: fall down, then spread horizontally with level
        seen = set()
        for _ in range(budget):
            if not self.fluid_q:
                break
            pos = self.fluid_q.popleft()
            if pos in seen:
                continue
            seen.add(pos)
            b = self.get(pos)
            if b not in FLUID:
                continue
            level = self.meta.get(pos, 0)
            x, y, z = pos
            below = (x, y - 1, z)
            bb = self.get(below)
            # Lava + water → stone / cobble / obsidian (Infdev)
            if b == WATER and bb == LAVA:
                self.blocks[below] = OBSIDIAN if self.meta.get(below, 0) == 0 else COBBLESTONE
                self.meta.pop(below, None)
                self._dirty_near(below)
                continue
            if b == LAVA and bb == WATER:
                self.blocks[below] = STONE
                self.meta.pop(below, None)
                self._dirty_near(below)
                continue
            if bb in REPLACEABLE or bb == AIR:
                if bb != AIR:
                    self.blocks.pop(below, None)
                self.blocks[below] = b
                self.meta[below] = 0 if level == 0 else min(7, level + 1)
                self.fluid_q.append(below)
                self._dirty_near(below)
                continue
            max_spread = 7 if b == WATER else 3
            if level >= max_spread:
                continue
            for nx, nz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                npos = (x + nx, y, z + nz)
                nb = self.get(npos)
                # fluid contact reactions sideways
                if b == WATER and nb == LAVA:
                    self.blocks[npos] = COBBLESTONE
                    self.meta.pop(npos, None)
                    self._dirty_near(npos)
                    continue
                if b == LAVA and nb == WATER:
                    self.blocks[npos] = STONE
                    self.meta.pop(npos, None)
                    self._dirty_near(npos)
                    continue
                if nb in REPLACEABLE or nb == AIR:
                    if nb not in (AIR,):
                        if nb in FLUID and nb == b:
                            continue
                        self.blocks.pop(npos, None)
                    self.blocks[npos] = b
                    self.meta[npos] = level + 1
                    self.fluid_q.append(npos)
                    self._dirty_near(npos)

    def _tick_falling(self, budget: int):
        for _ in range(budget):
            if not self.fall_q:
                break
            pos = self.fall_q.popleft()
            b = self.get(pos)
            if b not in FALLING:
                continue
            x, y, z = pos
            below = (x, y - 1, z)
            if self.get(below) in (AIR,) or self.get(below) in REPLACEABLE and self.get(below) != LADDER:
                if self.get(below) not in (AIR,):
                    # crush flowers/saplings/water lightly
                    if self.get(below) in FLUID:
                        pass
                    else:
                        self.blocks.pop(below, None)
                        self.meta.pop(below, None)
                if self.get(below) in FLUID or self.get(below) == AIR:
                    del self.blocks[pos]
                    self.meta.pop(pos, None)
                    if self.get(below) in FLUID:
                        # sand falls into fluid → sits as block replacing? keep fluid displacement
                        self.blocks.pop(below, None)
                        self.meta.pop(below, None)
                    self.blocks[below] = b
                    self.fall_q.append(below)
                    self.fall_q.append((x, y + 1, z))
                    self._dirty_near(pos)
                    self._dirty_near(below)

    def _tick_grass(self, n: int):
        if not self.blocks:
            return
        keys = list(self.blocks.keys())
        for _ in range(min(n, len(keys))):
            pos = random.choice(keys)
            if self.get(pos) != DIRT:
                continue
            x, y, z = pos
            if self.get((x, y + 1, z)) not in (AIR, FLOWER, SAPLING):
                continue
            # Infdev grass spread from neighbor grass
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
                if self.get((x + dx, y, z + dz)) == GRASS:
                    self.blocks[pos] = GRASS
                    self._dirty_near(pos)
                    break
            # Dirt + hoe vibe: near water → farmland
            if self.get(pos) == DIRT and random.random() < 0.08:
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get((x + dx, y, z + dz)) == WATER or self.get((x + dx, y + 1, z + dz)) == WATER:
                        self.blocks[pos] = FARMLAND
                        self._dirty_near(pos)
                        break

    def _tick_fire(self, budget: int):
        # Infdev fire spread to flammable neighbors
        for _ in range(budget):
            if not self.fire_q:
                # also scan a few random fires
                break
            pos = self.fire_q.popleft()
            if self.get(pos) != FIRE:
                continue
            x, y, z = pos
            # extinguish randomly / no fuel
            if random.random() < 0.18:
                self.blocks.pop(pos, None)
                self._dirty_near(pos)
                continue
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0),
                               (1, 1, 0), (-1, 1, 0), (0, 1, 1), (0, 1, -1)):
                npos = (x + dx, y + dy, z + dz)
                nb = self.get(npos)
                if nb in FLAMMABLE and random.random() < 0.35:
                    self.blocks[npos] = FIRE
                    self.fire_q.append(npos)
                    self._dirty_near(npos)
                elif nb == AIR and random.random() < 0.08:
                    below = (npos[0], npos[1] - 1, npos[2])
                    if self.get(below) in FLAMMABLE:
                        self.blocks[npos] = FIRE
                        self.fire_q.append(npos)
                        self._dirty_near(npos)
            self.fire_q.append(pos)

    def _tick_saplings(self, n: int):
        keys = [p for p, b in self.blocks.items() if b == SAPLING]
        if not keys:
            return
        for _ in range(min(n, len(keys))):
            pos = random.choice(keys)
            if random.random() > 0.12:
                continue
            x, y, z = pos
            below = self.get((x, y - 1, z))
            if below not in (GRASS, DIRT, FARMLAND):
                continue
            self.blocks.pop(pos, None)
            rnd = random.Random(x * 31 + z * 17 + self.seed)
            self._grow_tree(x, y - 1, z, rnd)
            self._dirty_near(pos)

    def _tick_wheat(self, n: int):
        # Grow wheat on farmland; plant seeds by placing wheat on farmland
        keys = [p for p, b in self.blocks.items() if b in (FARMLAND, WHEAT)]
        if not keys:
            return
        for _ in range(min(n, len(keys))):
            pos = random.choice(keys)
            x, y, z = pos
            if self.get(pos) == FARMLAND and self.get((x, y + 1, z)) == AIR and random.random() < 0.1:
                self.blocks[(x, y + 1, z)] = WHEAT
                self.meta[(x, y + 1, z)] = 0
                self._dirty_near((x, y + 1, z))
            elif self.get(pos) == WHEAT:
                stage = self.meta.get(pos, 0)
                if stage < 3 and random.random() < 0.15:
                    self.meta[pos] = stage + 1
                    self._dirty_near(pos)

    def _tick_mobs(self, dt: float):
        for m in self.mobs:
            m.timer -= dt
            if m.timer <= 0:
                m.timer = 1.0 + random.random() * 2.5
                m.yaw += (random.random() - 0.5) * 1.5
            spd = 1.6 if m.kind != "creeper" else 1.2
            nx = m.x + math.sin(m.yaw) * spd * dt
            nz = m.z + math.cos(m.yaw) * spd * dt
            # stay on ground
            gy = None
            for y in range(WORLD_Y - 2, 0, -1):
                if self.solid_at((int(nx), y, int(nz))):
                    gy = y + 1.0
                    break
            if gy is not None and not self.solid_at((int(nx), int(gy), int(nz))):
                m.x, m.z, m.y = nx, nz, gy
            # gravity snap
            if self.solid_at((int(m.x), int(m.y - 0.1), int(m.z))):
                pass
            else:
                m.y = max(1.0, m.y - 8.0 * dt)

    def _tick_carts(self, dt: float):
        for c in self.carts:
            bx, bz = int(math.floor(c.x)), int(math.floor(c.z))
            by = int(math.floor(c.y - 0.05))
            on_rail = self.get((bx, by, bz)) == RAIL or self.get((bx, by - 1, bz)) == RAIL
            if on_rail:
                # Follow rail neighbors (axis-aligned Infdev rails)
                if abs(c.vx) + abs(c.vz) < 0.05:
                    c.vx = math.sin(c.yaw) * 3.5
                    c.vz = math.cos(c.yaw) * 3.5
                # Prefer continuing along connected rails
                nx, nz = c.x + c.vx * dt, c.z + c.vz * dt
                if self.get((int(nx), by, int(nz))) == RAIL or self.get((int(nx), by - 1, int(nz))) == RAIL:
                    c.x, c.z = nx, nz
                else:
                    # try turn
                    c.vx, c.vz = -c.vz, c.vx
                    c.yaw = math.atan2(c.vx, c.vz)
                c.y = float(by + 1.05) if self.get((bx, by, bz)) == RAIL else float(by + 0.05)
            else:
                c.vx *= 0.9
                c.vz *= 0.9
                c.y = max(1.0, c.y - 6.0 * dt)

    def _tick_spawners(self):
        # Infdev monster spawner — occasional creeper near cage
        if len(self.mobs) > 40:
            return
        for pos, b in list(self.blocks.items()):
            if b != SPAWNER:
                continue
            if random.random() > 0.04:
                continue
            x, y, z = pos
            sx = x + random.choice((-2, -1, 1, 2))
            sz = z + random.choice((-2, -1, 1, 2))
            if self.get((sx, y, sz)) == AIR and self.solid_at((sx, y - 1, sz)):
                self.mobs.append(Mob("creeper", sx + 0.5, y, sz + 0.5))

    def _tick_furnaces(self):
        # Smelt one item from world inventory isn't global — furnaces auto-convert
        # adjacent sand/ore ABOVE them into output in-place (Infdev-simple).
        for pos, b in list(self.blocks.items()):
            if b != FURNACE:
                continue
            above = (pos[0], pos[1] + 1, pos[2])
            src = self.get(above)
            if src in SMELT and random.random() < 0.12:
                self.blocks[above] = SMELT[src]
                self._dirty_near(above)

    def spawn_cart(self, x, y, z):
        self.carts.append(Minecart(x + 0.5, y + 0.2, z + 0.5))


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, world: VoxelWorld):
        self.x = self.y = self.z = 0.0
        self.vx = self.vy = self.vz = 0.0
        self.yaw = 0.0
        self.pitch = -0.15
        self.on_ground = False
        self.flying = False
        self.sprinting = False
        self.in_water = False
        self.step_timer = 0.0
        self.radius = 0.3
        self.height = 1.72
        self.eye_h = 1.56
        self.hp = 20
        self.max_hp = 20
        self.hurt_cd = 0.0
        self.fall_start = None
        self.riding = None  # Mob | Minecart
        self.respawn(world)

    def respawn(self, world: VoxelWorld):
        # Xbox 360 demo / TU0 tutorial spawn (files=off — coords baked in code)
        # Stand on the gravel path just outside the incomplete shelter, facing south gate.
        self.x = float(XBOX_SPAWN_X)
        self.z = float(XBOX_SPAWN_Z)
        self.yaw = float(XBOX_SPAWN_YAW)   # face south (+Z)
        self.pitch = -0.12
        world.ensure_around(self.x, self.z)
        world.stamp_xbox_demo_spawn()
        sx, sz = int(math.floor(self.x)), int(math.floor(self.z))
        self.y = float(SEA_LEVEL + 3)
        for y in range(1, WORLD_Y - 3):
            if world.solid_at((sx, y, sz)) and not world.solid_at((sx, y + 1, sz)) \
                    and not world.solid_at((sx, y + 2, sz)):
                # Prefer gravel path / grass pads (skip shelter roof planks)
                ground = world.get((sx, y, sz))
                if ground in (GRAVEL, GRASS, DIRT, COBBLESTONE, SAND):
                    self.y = float(y + 1.05)
                    break
        self.vy = 0.0
        self.flying = False
        self.hp = self.max_hp
        self.hurt_cd = 0.0
        self.fall_start = None
        self.riding = None

    def hurt(self, amount: int):
        if self.hurt_cd > 0 or self.flying:
            return
        self.hp = max(0, self.hp - amount)
        self.hurt_cd = 0.6

    def collides(self, world: VoxelWorld, px, py, pz) -> bool:
        min_x = int(math.floor(px - self.radius))
        max_x = int(math.floor(px + self.radius))
        min_y = int(math.floor(py))
        max_y = int(math.floor(py + self.height))
        min_z = int(math.floor(pz - self.radius))
        max_z = int(math.floor(pz + self.radius))
        for bx in range(min_x, max_x + 1):
            for by in range(min_y, max_y + 1):
                for bz in range(min_z, max_z + 1):
                    if world.solid_at((bx, by, bz)):
                        return True
        return False


# ---------------------------------------------------------------------------
# Main Infdev Game
# ---------------------------------------------------------------------------
class MinecraftInfdev:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        get_atlas()  # bake procedural Infdev textures into RAM (files=off)
        self.sound = SoundEngine()
        self.font = pygame.font.SysFont("Courier", 14, bold=True)
        self.font_md = pygame.font.SysFont("Courier", 18, bold=True)
        self.font_lg = pygame.font.SysFont("Courier", 28, bold=True)
        self.font_xl = pygame.font.SysFont("Courier", 36, bold=True)

        self.state = ST_MENU
        self.menu_sel = 0
        self.craft_sel = 0
        self.inv_sel = 0
        self.inventory = dict(INV_STARTER)
        self.menu_btns: list[tuple[pygame.Rect, str]] = []
        self.craft_btns: list[tuple[pygame.Rect, int]] = []
        self.panel_btns: list[tuple[pygame.Rect, str]] = []

        self.world = None
        self.player = None
        self.hotbar_idx = 0
        self.paused = False
        self.show_debug = True
        self.fancy = True
        self.day_time = 0.25
        self.swing_t = 0.0
        self.target_hit = None
        self.clouds = []
        self.menu_t = 0.0
        self.ui_from_play = False  # ESC/Back returns to game, not main menu
        self._lock_mouse(False)

    def _start_singleplayer(self, new_world: bool = True):
        if new_world or self.world is None:
            # Always Xbox 360 demo / TU0 tutorial seed — baked constant, files=off
            self.world = VoxelWorld(seed=XBOX_DEMO_SEED)
            self.clouds = self._make_clouds()
            self.player = Player(self.world)
        self.state = ST_PLAY
        self.paused = False
        self._lock_mouse(True)
        self.sound.play("select")

    def _return_menu(self):
        self.state = ST_MENU
        self.paused = False
        self.ui_from_play = False
        self._lock_mouse(False)
        self.sound.play("select")

    def _close_panel(self):
        """Leave inventory/crafting/about/help — back to game if opened in-play."""
        if self.ui_from_play and self.player is not None and self.world is not None:
            self.state = ST_PLAY
            self.paused = False
            self.ui_from_play = False
            self._lock_mouse(True)
            self.sound.play("select")
            return
        self._return_menu()

    def _make_clouds(self):
        seed = self.world.seed if self.world else 2026
        rnd = random.Random(seed ^ 0xC10D)
        clouds = []
        for _ in range(18):
            clouds.append([
                rnd.uniform(-40, 80),
                WORLD_Y - 2 + rnd.uniform(0, 3),
                rnd.uniform(-40, 80),
                rnd.uniform(4, 10),
                rnd.uniform(3, 8),
                rnd.uniform(0.4, 1.2),
            ])
        return clouds

    def _lock_mouse(self, lock: bool):
        pygame.mouse.set_visible(not lock)
        pygame.event.set_grab(lock)
        if lock:
            pygame.mouse.get_rel()

    def _inv_count(self, bid: int) -> int:
        return self.inventory.get(bid, 0)

    def _inv_add(self, bid: int, n: int):
        self.inventory[bid] = self._inv_count(bid) + n

    def _inv_take(self, bid: int, n: int) -> bool:
        if self._inv_count(bid) < n:
            return False
        self.inventory[bid] = self._inv_count(bid) - n
        if self.inventory[bid] <= 0:
            del self.inventory[bid]
        return True

    def _can_craft(self, idx: int) -> bool:
        _, inputs, _, _ = CRAFT_RECIPES[idx]
        return all(self._inv_count(b) >= n for b, n in inputs)

    def _do_craft(self, idx: int):
        name, inputs, out_id, out_n = CRAFT_RECIPES[idx]
        if not self._can_craft(idx):
            return
        for b, n in inputs:
            self._inv_take(b, n)
        self._inv_add(out_id, out_n)
        self.sound.play("place")

    def raycast(self, max_dist: float = 5.5):
        ox = self.player.x
        oy = self.player.y + self.player.eye_h
        oz = self.player.z
        cp = math.cos(self.player.pitch)
        dx = math.sin(self.player.yaw) * cp
        dy = math.sin(self.player.pitch)
        dz = math.cos(self.player.yaw) * cp
        step = 0.05
        dist = 0.0
        prev = (int(math.floor(ox)), int(math.floor(oy)), int(math.floor(oz)))
        while dist < max_dist:
            rx = ox + dx * dist
            ry = oy + dy * dist
            rz = oz + dz * dist
            bpos = (int(math.floor(rx)), int(math.floor(ry)), int(math.floor(rz)))
            b = self.world.get(bpos)
            if b == DOOR:
                return bpos, prev, True
            if b != AIR and b not in (WATER,):
                if b in (SAPLING, FLOWER, TORCH, FIRE, RAIL, MUSHROOM, WHEAT, SIGN, LADDER):
                    return bpos, prev, False
                if self.world.solid_at(bpos) or b in (LAVA, GLASS, LEAVES):
                    return bpos, prev, False
            prev = bpos
            dist += step
        return None

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.menu_t += dt
            self._handle_events()
            if self.state == ST_PLAY and not self.paused:
                self._update(dt)
            self._render()
            pygame.display.flip()

    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if self.state == ST_MENU:
                self._menu_event(ev)
            elif self.state in (ST_CRAFT, ST_INV, ST_ABOUT, ST_HELP):
                self._panel_event(ev)
            elif self.state == ST_PLAY:
                self._play_event(ev)

    def _menu_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.menu_sel = (self.menu_sel - 1) % len(MENU_ITEMS)
                self.sound.play("select")
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_sel = (self.menu_sel + 1) % len(MENU_ITEMS)
                self.sound.play("select")
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_menu(MENU_ITEMS[self.menu_sel][1])
            elif ev.key == pygame.K_n:
                self.sound.toggle_music()
            elif ev.key == pygame.K_ESCAPE:
                self._activate_menu("exit")
        elif ev.type == pygame.MOUSEMOTION:
            for i, (rect, _) in enumerate(self.menu_btns):
                if rect.collidepoint(ev.pos):
                    self.menu_sel = i
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, (rect, action) in enumerate(self.menu_btns):
                if rect.collidepoint(ev.pos):
                    self.menu_sel = i
                    self._activate_menu(action)
                    break

    def _activate_menu(self, action: str):
        if action == "exit":
            pygame.quit()
            sys.exit(0)
        if action == ST_PLAY:
            self._start_singleplayer(True)
            return
        self.ui_from_play = False
        self.state = action
        self.craft_sel = 0
        self.inv_sel = 0
        self._lock_mouse(False)
        self.sound.play("select")

    def _panel_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE or (ev.key in (pygame.K_e, pygame.K_i) and self.state == ST_INV) \
                    or (ev.key == pygame.K_c and self.state == ST_CRAFT):
                self._close_panel()
                return
            if self.state == ST_CRAFT:
                if ev.key in (pygame.K_UP, pygame.K_w):
                    self.craft_sel = (self.craft_sel - 1) % len(CRAFT_RECIPES)
                    self.sound.play("select")
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    self.craft_sel = (self.craft_sel + 1) % len(CRAFT_RECIPES)
                    self.sound.play("select")
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._do_craft(self.craft_sel)
            elif self.state == ST_INV:
                items = sorted(self.inventory.keys())
                if items:
                    if ev.key in (pygame.K_LEFT, pygame.K_a):
                        self.inv_sel = (self.inv_sel - 1) % len(items)
                        self.sound.play("select")
                    elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                        self.inv_sel = (self.inv_sel + 1) % len(items)
                        self.sound.play("select")
                    elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        bid = items[self.inv_sel]
                        if bid in HOTBAR_BLOCKS:
                            self.hotbar_idx = HOTBAR_BLOCKS.index(bid)
                            self.sound.play("select")
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for rect, action in self.panel_btns:
                if rect.collidepoint(ev.pos):
                    if action == "back":
                        self._close_panel()
                    elif action == "craft" and self.state == ST_CRAFT:
                        self._do_craft(self.craft_sel)
                    elif action.startswith("recipe:"):
                        self.craft_sel = int(action.split(":")[1])
                        self._do_craft(self.craft_sel)
                    elif action.startswith("inv:"):
                        self.inv_sel = int(action.split(":")[1])
                        items = sorted(self.inventory.keys())
                        if 0 <= self.inv_sel < len(items) and items[self.inv_sel] in HOTBAR_BLOCKS:
                            self.hotbar_idx = HOTBAR_BLOCKS.index(items[self.inv_sel])
                            self.sound.play("select")
                    return
            if self.state == ST_CRAFT:
                for rect, idx in self.craft_btns:
                    if rect.collidepoint(ev.pos):
                        self.craft_sel = idx
                        self.sound.play("select")
                        break

    def _play_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.paused:
                    self._return_menu()
                else:
                    self.paused = True
                    self._lock_mouse(False)
                    self.sound.play("select")
            elif self.paused:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.paused = False
                    self._lock_mouse(True)
                elif ev.key == pygame.K_m:
                    self._return_menu()
            else:
                if ev.key == pygame.K_e or ev.key == pygame.K_i:
                    self.ui_from_play = True
                    self.state = ST_INV
                    self._lock_mouse(False)
                    self.sound.play("select")
                elif ev.key == pygame.K_c:
                    self.ui_from_play = True
                    self.state = ST_CRAFT
                    self._lock_mouse(False)
                    self.sound.play("select")
                elif ev.key == pygame.K_f:
                    self.player.flying = not self.player.flying
                    self.player.vy = 0.0
                elif ev.key == pygame.K_g:
                    self.fancy = not self.fancy
                elif ev.key == pygame.K_n:
                    self.sound.toggle_music()
                elif ev.key == pygame.K_v:
                    self._toggle_ride()
                elif ev.key == pygame.K_b:
                    self._spawn_cart_at_crosshair()
                elif ev.key == pygame.K_r:
                    # Regenerate Xbox demo world (same seed, fresh stamp — files=off)
                    self.world = VoxelWorld(seed=XBOX_DEMO_SEED)
                    self.clouds = self._make_clouds()
                    self.player = Player(self.world)
                elif ev.key == pygame.K_F3:
                    self.show_debug = not self.show_debug
                elif pygame.K_1 <= ev.key <= pygame.K_9:
                    idx = ev.key - pygame.K_1
                    if idx < len(HOTBAR_BLOCKS):
                        self.hotbar_idx = idx
                        self.sound.play("select")
                elif ev.key == pygame.K_0 and len(HOTBAR_BLOCKS) >= 10:
                    self.hotbar_idx = 9
                    self.sound.play("select")
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            if self.paused:
                mx, my = ev.pos
                for rect, action in self.panel_btns:
                    if rect.collidepoint((mx, my)):
                        if action == "resume":
                            self.paused = False
                            self._lock_mouse(True)
                        elif action == "menu":
                            self._return_menu()
                        return
                self.paused = False
                self._lock_mouse(True)
                return
            if ev.button == 4:
                self.hotbar_idx = (self.hotbar_idx - 1) % len(HOTBAR_BLOCKS)
                self.sound.play("select")
            elif ev.button == 5:
                self.hotbar_idx = (self.hotbar_idx + 1) % len(HOTBAR_BLOCKS)
                self.sound.play("select")
            elif ev.button == 1:
                self.swing_t = 1.0
                if self.target_hit:
                    hit_pos, _, is_door = self.target_hit
                    if is_door and self.world.toggle_door(hit_pos):
                        self.sound.play("door")
                    else:
                        dropped = self.world.get(hit_pos)
                        if self.world.set_block(hit_pos, AIR):
                            if dropped not in (AIR, BEDROCK, FIRE, WATER, LAVA):
                                self._inv_add(dropped, 1)
                            self.sound.play("break")
            elif ev.button == 2:  # middle — ignite / prime TNT (flint&steel vibe)
                self.swing_t = 1.0
                if self.target_hit:
                    hit_pos, place_pos, _ = self.target_hit
                    if self.world.ignite(hit_pos) or self.world.ignite(place_pos):
                        self.sound.play("place")
            elif ev.button == 3:
                self.swing_t = 1.0
                if self.target_hit:
                    hit_pos, place_pos, _ = self.target_hit
                    btype = HOTBAR_BLOCKS[self.hotbar_idx]
                    # Infdev bucket: scoop fluids
                    if btype == BUCKET and self.world.get(hit_pos) in FLUID:
                        fluid = self.world.get(hit_pos)
                        if self.world.set_block(hit_pos, AIR):
                            self._inv_add(fluid, 1)
                            self.sound.play("splash")
                        return
                    dest = place_pos
                    if btype == WHEAT and self.world.get(hit_pos) == FARMLAND:
                        dest = (hit_pos[0], hit_pos[1] + 1, hit_pos[2])
                    if btype == BUCKET:
                        return
                    if not self._block_hits_player(dest):
                        if self._inv_count(btype) > 0:
                            if self.world.set_block(dest, btype):
                                self._inv_take(btype, 1)
                                self.sound.play("place")
                        elif self.world.set_block(dest, btype):
                            self.sound.play("place")

    def _block_hits_player(self, bpos) -> bool:
        bx, by, bz = bpos
        p = self.player
        if bx + 1 <= p.x - p.radius or bx >= p.x + p.radius:
            return False
        if by + 1 <= p.y or by >= p.y + p.height:
            return False
        if bz + 1 <= p.z - p.radius or bz >= p.z + p.radius:
            return False
        return True

    def _toggle_ride(self):
        p = self.player
        if p.riding is not None:
            p.riding = None
            self.sound.play("select")
            return
        best, best_d = None, 2.5
        for m in self.world.mobs:
            if m.kind != "pig":
                continue
            d = math.hypot(m.x - p.x, m.z - p.z)
            if d < best_d:
                best, best_d = m, d
        for c in self.world.carts:
            d = math.hypot(c.x - p.x, c.z - p.z)
            if d < best_d:
                best, best_d = c, d
        if best is not None:
            p.riding = best
            if isinstance(best, Mob):
                best.saddled = True
            self.sound.play("jump")

    def _spawn_cart_at_crosshair(self):
        if not self.target_hit:
            return
        hit, place, _ = self.target_hit
        for pos in (hit, place):
            if self.world.get(pos) == RAIL:
                self.world.spawn_cart(pos[0], pos[1], pos[2])
                self.sound.play("place")
                return
            if self.world.get((pos[0], pos[1] - 1, pos[2])) == RAIL:
                self.world.spawn_cart(pos[0], pos[1] - 1, pos[2])
                self.sound.play("place")
                return

    def _update(self, dt: float):
        p = self.player
        self.world.ensure_around(p.x, p.z)
        self.world.tick(dt)

        mx, my = pygame.mouse.get_rel()
        p.yaw = (p.yaw + mx * MOUSE_SENS) % (math.pi * 2.0)
        p.pitch = max(-1.52, min(1.52, p.pitch - my * MOUSE_SENS))

        # Riding pig / minecart (Infdev saddle / cart)
        if p.riding is not None:
            r = p.riding
            if isinstance(r, Minecart):
                r.yaw = p.yaw
                r.vx = math.sin(p.yaw) * 5.5
                r.vz = math.cos(p.yaw) * 5.5
                p.x, p.y, p.z = r.x, r.y + 0.9, r.z
            else:
                r.yaw = p.yaw
                r.x += math.sin(p.yaw) * 4.0 * dt
                r.z += math.cos(p.yaw) * 4.0 * dt
                p.x, p.y, p.z = r.x, r.y + 0.95, r.z
            p.vy = 0.0
            p.on_ground = True
            self.target_hit = self.raycast()
            self.day_time = (self.day_time + dt * 0.004) % 1.0
            return

        keys = pygame.key.get_pressed()
        forward = (1.0 if keys[pygame.K_w] else 0.0) - (1.0 if keys[pygame.K_s] else 0.0)
        strafe = (1.0 if keys[pygame.K_d] else 0.0) - (1.0 if keys[pygame.K_a] else 0.0)

        eye = (int(p.x), int(p.y + p.eye_h * 0.5), int(p.z))
        was_water = p.in_water
        p.in_water = self.world.fluid_at(eye) == WATER or self.world.fluid_at((int(p.x), int(p.y), int(p.z))) == WATER
        if p.in_water and not was_water:
            self.sound.play("splash")

        on_ladder = self.world.get((int(p.x), int(p.y), int(p.z))) == LADDER or \
                    self.world.get((int(p.x), int(p.y + 1), int(p.z))) == LADDER

        p.sprinting = bool(keys[pygame.K_LCTRL] or (keys[pygame.K_w] and keys[pygame.K_LSHIFT] and not p.flying and not p.in_water))
        if p.flying:
            spd = FLY_SPEED
        elif p.in_water:
            spd = SWIM_SPEED
        elif p.sprinting:
            spd = SPRINT_SPEED
        else:
            spd = WALK_SPEED

        length = math.hypot(forward, strafe)
        if length > 0:
            forward /= length
            strafe /= length

        sin_y, cos_y = math.sin(p.yaw), math.cos(p.yaw)
        move_x = (forward * sin_y + strafe * cos_y) * spd
        move_z = (forward * cos_y - strafe * sin_y) * spd

        nx = p.x + move_x * dt
        if not p.collides(self.world, nx, p.y, p.z):
            p.x = nx
        nz = p.z + move_z * dt
        if not p.collides(self.world, p.x, p.y, nz):
            p.z = nz

        if p.flying:
            vy = 0.0
            if keys[pygame.K_SPACE]:
                vy += FLY_SPEED * 0.75
            if keys[pygame.K_LSHIFT]:
                vy -= FLY_SPEED * 0.75
            ny = p.y + vy * dt
            if not p.collides(self.world, p.x, ny, p.z):
                p.y = ny
        elif on_ladder:
            vy = 0.0
            if keys[pygame.K_SPACE] or keys[pygame.K_w]:
                vy = 4.5
            if keys[pygame.K_LSHIFT]:
                vy = -4.5
            ny = p.y + vy * dt
            if not p.collides(self.world, p.x, ny, p.z):
                p.y = ny
            p.vy = 0.0
            p.on_ground = True
        else:
            if keys[pygame.K_SPACE]:
                if p.in_water:
                    p.vy = 4.0
                elif p.on_ground:
                    p.vy = JUMP_FORCE
                    p.on_ground = False
                    self.sound.play("jump")
            if p.in_water:
                p.vy = max(-6.0, p.vy - GRAVITY * 0.25 * dt)
                p.vy *= 0.92
            else:
                p.vy = max(-32.0, p.vy - GRAVITY * dt)
            ny = p.y + p.vy * dt
            if not p.collides(self.world, p.x, ny, p.z):
                p.y = ny
                p.on_ground = False
            else:
                if p.vy < 0:
                    # fall damage (Infdev survival)
                    if p.fall_start is not None:
                        fall = p.fall_start - p.y
                        if fall > 3.5:
                            p.hurt(int(fall - 3.0))
                        p.fall_start = None
                    p.on_ground = True
                p.vy = 0.0

        if not p.on_ground and not p.flying and not p.in_water:
            if p.fall_start is None:
                p.fall_start = p.y
        else:
            if p.on_ground or p.in_water:
                p.fall_start = None

        # Lava / fire damage
        feet = (int(p.x), int(p.y), int(p.z))
        if self.world.get(feet) in (LAVA, FIRE) or self.world.fluid_at(feet) == LAVA:
            p.hurt(2)
        if p.hurt_cd > 0:
            p.hurt_cd -= dt

        # Minecart rails — slide along rail when standing on one
        if self.world.get((int(p.x), int(p.y - 0.05), int(p.z))) == RAIL and not p.flying:
            p.x += math.sin(p.yaw) * 6.0 * dt
            p.z += math.cos(p.yaw) * 6.0 * dt

        # Creeper proximity
        for m in self.world.mobs:
            if m.kind != "creeper":
                continue
            ddx, ddz = m.x - p.x, m.z - p.z
            if ddx * ddx + ddz * ddz < 2.2 * 2.2 and abs(m.y - p.y) < 2.5:
                p.hurt(1)

        if p.hp <= 0 or p.y < -20:
            p.respawn(self.world)

        if p.on_ground and length > 0 and not p.flying:
            p.step_timer += dt * (1.4 if p.sprinting else 1.0)
            if p.step_timer >= 0.38:
                p.step_timer = 0.0
                self.sound.play("step")

        if self.swing_t > 0:
            self.swing_t = max(0.0, self.swing_t - dt * 4.5)

        self.day_time = (self.day_time + dt * 0.004) % 1.0
        # Drift clouds
        for c in self.clouds:
            c[0] += c[5] * dt
            if c[0] > p.x + 90:
                c[0] = p.x - 70
                c[2] = p.z + random.uniform(-50, 50)

        self.target_hit = self.raycast()

    def _project_face(self, w_verts, cam_x, cam_y, cam_z, sin_y, cos_y, sin_p, cos_p):
        cam_verts = []
        for vx, vy, vz in w_verts:
            rx, ry, rz = vx - cam_x, vy - cam_y, vz - cam_z
            tx = rx * cos_y - rz * sin_y
            tz = rx * sin_y + rz * cos_y
            ty = ry * cos_p - tz * sin_p
            cz = ry * sin_p + tz * cos_p
            cam_verts.append((tx, ty, cz))
        clipped = []
        n = len(cam_verts)
        for i in range(n):
            v1, v2 = cam_verts[i], cam_verts[(i + 1) % n]
            in1, in2 = v1[2] >= NEAR_Z, v2[2] >= NEAR_Z
            if in1 and in2:
                clipped.append(v2)
            elif in1 and not in2:
                t = (NEAR_Z - v1[2]) / (v2[2] - v1[2] + 1e-9)
                clipped.append((v1[0] + t * (v2[0] - v1[0]), v1[1] + t * (v2[1] - v1[1]), NEAR_Z))
            elif not in1 and in2:
                t = (NEAR_Z - v1[2]) / (v2[2] - v1[2] + 1e-9)
                clipped.append((v1[0] + t * (v2[0] - v1[0]), v1[1] + t * (v2[1] - v1[1]), NEAR_Z))
                clipped.append(v2)
        if len(clipped) < 3:
            return None
        pts = []
        on = False
        for tx, ty, cz in clipped:
            sc = FOV / cz
            sx, sy = int(HALF_W + tx * sc), int(HALF_H - ty * sc)
            if 0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H:
                on = True
            pts.append((sx, sy))
        return pts if on else None

    def _draw_block_icon(self, btype: int, x: int, y: int, s: int = 28):
        top_c, side_c, _ = BLOCK_COLORS.get(btype, ((200, 200, 200), (150, 150, 150), (100, 100, 100)))
        pygame.draw.rect(self.screen, top_c, (x, y, s, s // 3))
        pygame.draw.rect(self.screen, side_c, (x, y + s // 3, s, s - s // 3))
        pygame.draw.rect(self.screen, (20, 20, 20), (x, y, s, s), 1)

    def _draw_backdrop(self):
        # Procedural dirt/stone Infdev title backdrop
        t = self.menu_t
        for y in range(0, SCREEN_H, 8):
            shade = 40 + int(18 * math.sin(y * 0.04 + t * 0.4))
            col = (shade + 20, shade + 10, shade)
            pygame.draw.rect(self.screen, col, (0, y, SCREEN_W, 8))
        # Floating fake voxel strips
        for i in range(12):
            bx = int((i * 97 + t * 18) % (SCREEN_W + 80)) - 40
            by = 80 + (i * 37) % (SCREEN_H - 160)
            self._draw_block_icon([GRASS, STONE, DIRT, WATER, BRICK, GOLD][i % 6], bx, by, 22)

    def _btn(self, text: str, cx: int, cy: int, w: int, h: int, selected: bool) -> pygame.Rect:
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        bg = (90, 90, 100) if selected else (55, 55, 62)
        bd = (255, 255, 120) if selected else (140, 140, 150)
        pygame.draw.rect(self.screen, bg, rect)
        pygame.draw.rect(self.screen, bd, rect, 3 if selected else 1)
        if selected:
            pulse = 180 + int(50 * math.sin(self.menu_t * 6))
            pygame.draw.rect(self.screen, (pulse, pulse, 80), rect, 2)
        label = self.font_md.render(text, True, (255, 255, 255) if selected else (210, 210, 210))
        self.screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))
        return rect

    def _draw_menu(self):
        self._draw_backdrop()
        brand = self.font_xl.render(BRAND, True, (255, 220, 90))
        title = self.font_lg.render("MINECRAFT — PY PORT 1.x INFDEV", True, (255, 255, 255))
        sub = self.font_md.render("full Infdev algo pack  ·  files=off  ·  A.C Holdings", True, (180, 255, 140))
        self.screen.blit(self.font_xl.render(BRAND, True, (0, 0, 0)), (HALF_W - brand.get_width() // 2 + 3, 42))
        self.screen.blit(brand, (HALF_W - brand.get_width() // 2, 40))
        self.screen.blit(title, (HALF_W - title.get_width() // 2, 88))
        self.screen.blit(sub, (HALF_W - sub.get_width() // 2, 122))

        self.menu_btns = []
        start_y = 170
        for i, (label, action) in enumerate(MENU_ITEMS):
            rect = self._btn(label, HALF_W, start_y + i * 58, 320, 46, i == self.menu_sel)
            self.menu_btns.append((rect, action))

        foot = self.font.render(
            COPYRIGHT + "  |  ↑↓ Enter  ·  N sweden OST  ·  math synth files=off",
            True, (180, 180, 180))
        self.screen.blit(foot, (HALF_W - foot.get_width() // 2, SCREEN_H - 36))

    def _draw_panel_frame(self, title: str):
        self._draw_backdrop()
        panel = pygame.Rect(80, 50, SCREEN_W - 160, SCREEN_H - 100)
        pygame.draw.rect(self.screen, (32, 32, 38), panel)
        pygame.draw.rect(self.screen, (200, 200, 120), panel, 3)
        t = self.font_lg.render(title, True, (255, 255, 140))
        self.screen.blit(t, (panel.centerx - t.get_width() // 2, panel.y + 16))
        self.panel_btns = []
        back_lbl = "Close" if self.ui_from_play else "Back to Menu"
        back = self._btn(back_lbl, HALF_W, SCREEN_H - 78, 240, 40, True)
        self.panel_btns.append((back, "back"))
        return panel

    def _draw_crafting(self):
        panel = self._draw_panel_frame("CRAFTING")
        self.craft_btns = []
        y = panel.y + 70
        for i, (name, inputs, out_id, out_n) in enumerate(CRAFT_RECIPES):
            row = pygame.Rect(panel.x + 24, y + i * 38, panel.width - 48, 34)
            can = self._can_craft(i)
            selected = i == self.craft_sel
            bg = (70, 90, 50) if can and selected else ((50, 50, 58) if selected else (40, 40, 46))
            pygame.draw.rect(self.screen, bg, row)
            pygame.draw.rect(self.screen, (255, 255, 100) if selected else (100, 100, 110), row, 2 if selected else 1)
            self._draw_block_icon(out_id, row.x + 6, row.y + 3, 26)
            req = ", ".join("%dx %s" % (n, BLOCK_NAMES.get(b, "?")) for b, n in inputs)
            line = "%s  →  %dx %s" % (name, out_n, BLOCK_NAMES.get(out_id, "?"))
            col = (220, 255, 180) if can else (160, 120, 120)
            self.screen.blit(self.font.render(line, True, col), (row.x + 42, row.y + 2))
            self.screen.blit(self.font.render(req, True, (160, 160, 160)), (row.x + 42, row.y + 16))
            self.craft_btns.append((row, i))
            self.panel_btns.append((row, "recipe:%d" % i))
        hint = self.font.render("↑↓ select  ·  Enter / click craft  ·  Esc back", True, (180, 180, 180))
        self.screen.blit(hint, (HALF_W - hint.get_width() // 2, panel.bottom - 70))

    def _draw_inventory(self):
        panel = self._draw_panel_frame("INVENTORY")
        items = sorted(self.inventory.keys())
        if not items:
            empty = self.font_md.render("Inventory empty — mine or craft!", True, (200, 200, 200))
            self.screen.blit(empty, (HALF_W - empty.get_width() // 2, HALF_H - 20))
            return
        cols = 8
        slot = 56
        grid_w = cols * slot
        ox = HALF_W - grid_w // 2
        oy = panel.y + 90
        if self.inv_sel >= len(items):
            self.inv_sel = 0
        for i, bid in enumerate(items):
            cx = ox + (i % cols) * slot
            cy = oy + (i // cols) * slot
            rect = pygame.Rect(cx, cy, slot - 6, slot - 6)
            selected = i == self.inv_sel
            pygame.draw.rect(self.screen, (45, 45, 52), rect)
            pygame.draw.rect(self.screen, (255, 255, 100) if selected else (120, 120, 130), rect, 3 if selected else 1)
            self._draw_block_icon(bid, cx + 10, cy + 6, 28)
            n = self.font.render(str(self._inv_count(bid)), True, (255, 255, 255))
            self.screen.blit(n, (cx + 4, cy + 34))
            self.panel_btns.append((rect, "inv:%d" % i))
        bid = items[self.inv_sel]
        info = self.font_md.render("%s  ×%d" % (BLOCK_NAMES.get(bid, "?"), self._inv_count(bid)), True, (255, 255, 160))
        self.screen.blit(info, (HALF_W - info.get_width() // 2, panel.bottom - 100))
        hint = self.font.render(
            "←→ select  ·  Enter set hotbar  ·  Esc / E close" if self.ui_from_play
            else "←→ select  ·  Esc back to menu",
            True, (180, 180, 180))
        self.screen.blit(hint, (HALF_W - hint.get_width() // 2, panel.bottom - 70))

    def _draw_about(self):
        panel = self._draw_panel_frame("ABOUT")
        lines = [
            TITLE,
            SUBTITLE,
            "",
            "Infdev-inspired voxel sandbox.",
            "Default world = Xbox 360 TU0 Demo / Tutorial seed",
            "(1171544198849424676) — baked in RAM, files=off.",
            "Spawn: 3, ~, -37 facing south + tutorial compound.",
            "",
            "AC Kondo Infdev — chunks, caves, ores, fluids,",
            "fire, TNT, rails, minecarts, stairs, furnace,",
            "buckets, spawners, farmland, Far Lands, mobs.",
            "Procedural textures + Sweden math OST — no Mojang assets.",
            "",
            COPYRIGHT,
            "Brand: AC KONDO / A.C Holdings · pygame-ce · files=off",
        ]
        y = panel.y + 80
        for line in lines:
            s = self.font.render(line, True, (230, 230, 230))
            self.screen.blit(s, (HALF_W - s.get_width() // 2, y))
            y += 22

    def _draw_help(self):
        panel = self._draw_panel_frame("HELP")
        lines = [
            "MAIN MENU",
            "  Single Player — generate world & play",
            "  Crafting / Inventory — manage items",
            "  About / Help / Exit",
            "",
            "IN GAME",
            "  WASD move · SPACE jump · F fly · G fancy gfx · N OST",
            "  LMB mine · RMB place · 1-0 hotbar · wheel cycle",
            "  E / I inventory · C crafting · R regen demo · F3 debug",
            "  ESC pause · ESC again main menu · M from pause",
            "",
            "  Middle-click ignite/TNT · V ride pig/cart · B spawn cart",
            "  Bucket scoops water/lava · furnace smelts above it",
            "OST: Sweden-style math synth · Far Lands ~±420",
        ]
        y = panel.y + 72
        for line in lines:
            s = self.font.render(line, True, (220, 220, 220))
            self.screen.blit(s, (panel.x + 48, y))
            y += 20

    def _render(self):
        if self.state == ST_MENU:
            self._draw_menu()
            return
        if self.state == ST_CRAFT:
            self._draw_crafting()
            return
        if self.state == ST_INV:
            self._draw_inventory()
            return
        if self.state == ST_ABOUT:
            self._draw_about()
            return
        if self.state == ST_HELP:
            self._draw_help()
            return

        # --- gameplay ---
        sun = 0.55 + 0.45 * max(0.05, math.sin(self.day_time * math.pi * 2.0))
        sky_col = (int(115 * sun), int(178 * sun), int(255 * sun))
        if sun < 0.35:
            sky_col = (int(20 + 40 * sun), int(20 + 50 * sun), int(40 + 80 * sun))
        self.screen.fill(sky_col)

        p = self.player
        cam_x, cam_y, cam_z = p.x, p.y + p.eye_h, p.z
        sin_y, cos_y = math.sin(p.yaw), math.cos(p.yaw)
        sin_p, cos_p = math.sin(p.pitch), math.cos(p.pitch)
        target_block = self.target_hit[0] if self.target_hit else None
        max_dist_sq = RENDER_DIST * RENDER_DIST
        render_queue = []

        # Nearby torch / fire / lava lights (Infdev torch lighting approx)
        pcx, pcy, pcz = int(cam_x), int(cam_y), int(cam_z)
        lights = []
        for dx in range(-8, 9):
            for dy in range(-5, 6):
                for dz in range(-8, 9):
                    bp = (pcx + dx, pcy + dy, pcz + dz)
                    bt = self.world.get(bp)
                    if bt in (TORCH, FIRE, LAVA):
                        lights.append((bp[0] + 0.5, bp[1] + 0.5, bp[2] + 0.5,
                                       1.0 if bt != LAVA else 0.7))

        for fcx, fcy, fcz, nx, ny, nz, w_verts, col, bpos, btype in self.world.exposed_faces:
            dx, dy, dz = fcx - cam_x, fcy - cam_y, fcz - cam_z
            dist_sq = dx * dx + dy * dy + dz * dz
            if dist_sq > max_dist_sq:
                continue
            if dx * nx + dy * ny + dz * nz >= 0.0:
                continue
            pts = self._project_face(w_verts, cam_x, cam_y, cam_z, sin_y, cos_y, sin_p, cos_p)
            if not pts:
                continue
            # torch light boost
            light = sun
            for lx, ly, lz, stren in lights:
                dd = (fcx - lx) ** 2 + (fcy - ly) ** 2 + (fcz - lz) ** 2
                if dd < 64:
                    light = max(light, sun + stren * (1.0 - dd / 64.0) * 0.85)
            light = min(1.35, light)
            fog = min(1.0, dist_sq / max_dist_sq) ** 1.6
            r = int((col[0] * light) * (1.0 - fog) + sky_col[0] * fog)
            g = int((col[1] * light) * (1.0 - fog) + sky_col[1] * fog)
            b = int((col[2] * light) * (1.0 - fog) + sky_col[2] * fog)
            render_queue.append((dist_sq, pts, (min(255, r), min(255, g), min(255, b)), bpos == target_block, btype in FLUID))

        # Infdev 3D clouds (fancy only)
        if self.fancy:
            for cx, cy, cz, cw, cd, _ in self.clouds:
                dist_sq = (cx - cam_x) ** 2 + (cy - cam_y) ** 2 + (cz - cam_z) ** 2
                if dist_sq > max_dist_sq * 4:
                    continue
                verts = [
                    (cx, cy, cz), (cx + cw, cy, cz), (cx + cw, cy, cz + cd), (cx, cy, cz + cd),
                ]
                pts = self._project_face(verts, cam_x, cam_y, cam_z, sin_y, cos_y, sin_p, cos_p)
                if pts:
                    render_queue.append((dist_sq, pts, (240, 240, 250), False, True))

        # Mobs as textured cubes
        for m in self.world.mobs:
            dx, dy, dz = m.x - cam_x, m.y + 0.5 - cam_y, m.z - cam_z
            dist_sq = dx * dx + dy * dy + dz * dz
            if dist_sq > max_dist_sq:
                continue
            col = m.color()
            hs = 0.35
            for nx, ny, nz, verts, shade, _, _ in CUBE_FACES:
                if dx * nx + dy * ny + dz * nz >= 0:
                    continue
                w_verts = [(m.x - hs + vx * hs * 2, m.y + vy * 0.9, m.z - hs + vz * hs * 2) for vx, vy, vz in verts]
                pts = self._project_face(w_verts, cam_x, cam_y, cam_z, sin_y, cos_y, sin_p, cos_p)
                if pts:
                    c = (min(255, int(col[0] * shade * sun)), min(255, int(col[1] * shade * sun)), min(255, int(col[2] * shade * sun)))
                    render_queue.append((dist_sq, pts, c, False, False))

        # Minecarts (Infdev rails vehicles)
        for cart in self.world.carts:
            dx, dy, dz = cart.x - cam_x, cart.y + 0.3 - cam_y, cart.z - cam_z
            dist_sq = dx * dx + dy * dy + dz * dz
            if dist_sq > max_dist_sq:
                continue
            col = (160, 160, 175)
            hs, hh = 0.4, 0.35
            for nx, ny, nz, verts, shade, _, _ in CUBE_FACES:
                if dx * nx + dy * ny + dz * nz >= 0:
                    continue
                w_verts = [(cart.x - hs + vx * hs * 2, cart.y + vy * hh, cart.z - hs + vz * hs * 2)
                           for vx, vy, vz in verts]
                pts = self._project_face(w_verts, cam_x, cam_y, cam_z, sin_y, cos_y, sin_p, cos_p)
                if pts:
                    c = (min(255, int(col[0] * shade * sun)),) * 3
                    c = (c[0], min(255, int(col[1] * shade * sun)), min(255, int(col[2] * shade * sun)))
                    render_queue.append((dist_sq, pts, c, False, False))

        render_queue.sort(key=lambda item: item[0], reverse=True)
        for _, pts, color, targeted, soft in render_queue:
            pygame.draw.polygon(self.screen, color, pts)
            if targeted:
                pygame.draw.polygon(self.screen, (255, 255, 255), pts, 2)
            elif self.fancy and not soft:
                pygame.draw.polygon(
                    self.screen,
                    (max(0, color[0] - 12), max(0, color[1] - 12), max(0, color[2] - 12)),
                    pts, 1,
                )

        # Underwater tint
        if p.in_water:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((20, 60, 140, 90))
            self.screen.blit(overlay, (0, 0))

        self._draw_hand()
        self._draw_hud()

    def _draw_hand(self):
        btype = HOTBAR_BLOCKS[self.hotbar_idx]
        top_c, side_c, _ = BLOCK_COLORS[btype]
        bob = math.sin(self.player.step_timer * math.pi * 2.5) * 6 if self.player.on_ground else 0
        swing = math.sin(self.swing_t * math.pi) * 45
        hx = int(SCREEN_W - 150 - swing * 0.8)
        hy = int(SCREEN_H - 110 + bob + swing * 0.5)
        top = [(hx, hy - 36), (hx + 48, hy - 18), (hx, hy), (hx - 48, hy - 18)]
        left = [(hx - 48, hy - 18), (hx, hy), (hx, hy + 56), (hx - 48, hy + 38)]
        right = [(hx, hy), (hx + 48, hy - 18), (hx + 48, hy + 38), (hx, hy + 56)]
        pygame.draw.polygon(self.screen, top_c, top)
        pygame.draw.polygon(self.screen, side_c, left)
        pygame.draw.polygon(self.screen, (int(side_c[0] * 0.78), int(side_c[1] * 0.78), int(side_c[2] * 0.78)), right)

    def _draw_hud(self):
        pygame.draw.line(self.screen, (255, 255, 255), (HALF_W - 8, HALF_H), (HALF_W + 8, HALF_H), 2)
        pygame.draw.line(self.screen, (255, 255, 255), (HALF_W, HALF_H - 8), (HALF_W, HALF_H + 8), 2)

        slot_w = 42
        total_w = len(HOTBAR_BLOCKS) * slot_w
        start_x = HALF_W - total_w // 2
        y0 = SCREEN_H - 54
        for i, btype in enumerate(HOTBAR_BLOCKS):
            x = start_x + i * slot_w
            rect = pygame.Rect(x, y0, slot_w - 4, slot_w - 4)
            pygame.draw.rect(self.screen, (30, 30, 36), rect)
            top_c, side_c, _ = BLOCK_COLORS[btype]
            pygame.draw.rect(self.screen, top_c, (x + 7, y0 + 7, 22, 10))
            pygame.draw.rect(self.screen, side_c, (x + 7, y0 + 17, 22, 12))
            border = (255, 255, 80) if i == self.hotbar_idx else (140, 140, 150)
            pygame.draw.rect(self.screen, border, rect, 3 if i == self.hotbar_idx else 1)
            label = "0" if i == 9 else str(i + 1)
            self.screen.blit(self.font.render(label, True, (255, 255, 255)), (x + 3, y0 + 1))

        name = BLOCK_NAMES[HOTBAR_BLOCKS[self.hotbar_idx]]
        lbl = self.font.render(name, True, (255, 255, 160))
        self.screen.blit(lbl, (HALF_W - lbl.get_width() // 2, y0 - 20))

        # Health hearts (Infdev survival)
        for i in range(self.player.max_hp // 2):
            filled = i < (self.player.hp + 1) // 2
            hx = 12 + i * 18
            hy = SCREEN_H - 78
            col = (220, 40, 40) if filled else (60, 30, 30)
            pygame.draw.polygon(self.screen, col, [
                (hx + 8, hy + 3), (hx + 14, hy + 8), (hx + 8, hy + 14), (hx + 2, hy + 8),
            ])

        if self.show_debug:
            fps = self.clock.get_fps()
            p = self.player
            mode = "FLY" if p.flying else ("SWIM" if p.in_water else ("SPRINT" if p.sprinting else "WALK"))
            gfx = "FANCY" if self.fancy else "FAST"
            lines = [
                TITLE,
                f"FPS:{fps:5.1f} | chunks:{len(self.world.loaded)} faces:{len(self.world.exposed_faces)} | {gfx}",
                f"XYZ:{p.x:7.1f}/{p.y:5.1f}/{p.z:7.1f} | {mode} | OST:{'ON' if self.sound.music_on else 'OFF'}",
                "WASD|F fly|G fancy|N sweden OST|E inv|C craft|R regen|ESC|F3",
            ]
            for i, text in enumerate(lines):
                col = (80, 255, 120) if i == 0 else (240, 240, 240)
                self.screen.blit(self.font.render(text, True, (0, 0, 0)), (11, 9 + i * 17))
                self.screen.blit(self.font.render(text, True, col), (10, 8 + i * 17))

        if self.paused:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            t1 = self.font_lg.render("PAUSED", True, (255, 255, 80))
            self.screen.blit(t1, (HALF_W - t1.get_width() // 2, HALF_H - 80))
            self.panel_btns = []
            r1 = self._btn("Resume", HALF_W, HALF_H - 10, 280, 44, True)
            r2 = self._btn("Main Menu", HALF_W, HALF_H + 50, 280, 44, False)
            self.panel_btns.append((r1, "resume"))
            self.panel_btns.append((r2, "menu"))
            t2 = self.font.render("Xbox Demo World  ·  ESC menu  ·  " + COPYRIGHT, True, (200, 200, 200))
            self.screen.blit(t2, (HALF_W - t2.get_width() // 2, HALF_H + 100))


def main():
    print(TITLE)
    print(SUBTITLE)
    print(COPYRIGHT)
    print("World seed (files=off): Xbox 360 TU0 Demo %d" % XBOX_DEMO_SEED)
    print("Spawn: %.1f, ?, %.1f facing south" % (XBOX_SPAWN_X, XBOX_SPAWN_Z))
    MinecraftInfdev().run()


if __name__ == "__main__":
    main()
