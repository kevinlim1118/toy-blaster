# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A collection of self-contained browser games. Each game is a **single HTML file** with embedded CSS and JavaScript — no build tools, no dependencies, no package manager.

To run any game, open the file directly in a browser:
```
start toy-blaster.html
start tictactoe.html
```

## Games

### toy-blaster.html
Top-down retro shooter. Canvas 900×620. Arrow keys/WASD to move, mouse to aim, click to shoot.

- 5 levels × 2–3 waves each, wave-based enemy spawning
- 4 enemy types (`grunt`, `shooter`, `rusher`, `tank`) defined in `ENEMY_DEFS` config map, instantiated as `Enemy` class
- Game states: `menu` → `playing` → `waveTransition` → `levelComplete` → `victory` / `gameover`
- Script sections navigable by searching `// ===`:

| Section | Purpose |
|---|---|
| SETUP | Canvas, constants (`WALL=32`), input state |
| AUDIO | `beep(type)` — procedural sounds via `AudioContext` |
| PARTICLES | Spawn/update/draw particle effects |
| BULLETS | `playerBullets` and `enemyBullets` arrays |
| PLAYER | `player` object — movement, shooting, animation, drawing |
| ENEMY TYPES | `ENEMY_DEFS` config + `Enemy` class |
| LEVEL DATA | `LEVELS` array — wave definitions per level |
| GAME STATE | `spawnWave`, `startGame`, `nextWave` |
| BACKGROUND / HUD / OVERLAYS | Pure draw functions |
| UPDATE / RENDER / LOOP | Main loop via `requestAnimationFrame` |
| INPUT | Keyboard and mouse event listeners |

### tictactoe.html
Two-player Tic Tac Toe. DOM-based (no canvas). Persistent score tracker across games (X / O / Ties). State held in `board[]`, `current`, `gameOver`, `scores`. Win detection iterates `wins[]` — 8 hardcoded winning lines. `init()` resets board without resetting scores.

## Architecture

All games share:
- **Single-file**: HTML + `<style>` + `<script>` in one `.html` file
- **Vanilla JS only**: no frameworks or libraries
- **No assets**: all graphics drawn with Canvas 2D primitives or CSS; sounds generated via Web Audio API

## Conventions

- New games follow the single-file pattern with the retro visual style (dark background, monospace font, bold outlines)
- Canvas coordinates clamped within `WALL` border on all sides
- Audio context resumed on first user interaction to satisfy browser autoplay policy

## Git & GitHub

- Remote: `https://github.com/kevinlim1118/toy-blaster`
- Branch: `master`
- Commit and push after every meaningful change to preserve progress:

```
git add <files>
git commit -m "type: short description"
git push
```
