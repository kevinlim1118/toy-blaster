# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a collection of self-contained browser games. Each game is a **single HTML file** with embedded CSS and JavaScript — no build tools, no dependencies, no package manager.

To run any game, open the file directly in a browser:
```
start toy-blaster.html
start tictactoe.html
```

## Architecture

All games follow the same pattern:

- **Single-file**: HTML + `<style>` + `<script>` in one `.html` file
- **HTML5 Canvas**: rendering via `canvas.getContext('2d')`
- **Vanilla JS**: no frameworks or libraries
- **Web Audio API**: retro chip sound effects generated programmatically (no audio assets)
- **No assets**: all graphics drawn with Canvas 2D primitives (arcs, rects, paths)

### toy-blaster.html structure

The script is organized in labeled sections (search for `// ===`):

| Section | Purpose |
|---|---|
| SETUP | Canvas, constants, input state |
| AUDIO | `beep(type)` — procedural sounds via `AudioContext` |
| PARTICLES | Spawn/update/draw particle effects |
| BULLETS | `playerBullets` and `enemyBullets` arrays |
| PLAYER | `player` object — movement, shooting, drawing |
| ENEMY TYPES | `ENEMY_DEFS` config map + `Enemy` class |
| LEVEL DATA | `LEVELS` array — wave definitions per level |
| GAME STATE | `spawnWave`, `startGame`, `nextWave` |
| BACKGROUND / HUD / OVERLAYS | Pure draw functions |
| UPDATE / RENDER / LOOP | Main game loop via `requestAnimationFrame` |
| INPUT | Keyboard and mouse event listeners |

Enemy types: `grunt`, `shooter`, `rusher`, `tank` — each defined in `ENEMY_DEFS` and instantiated as `Enemy` objects.

Game states: `menu` → `playing` → `waveTransition` → `levelComplete` → `victory` / `gameover`

## Conventions

- All coordinates are in canvas pixels (canvas is fixed at 900×620 for toy-blaster)
- `WALL = 32` is the border wall thickness; entities are clamped within it
- New games should follow the single-file pattern and use the same retro visual style (monospace font, dark background, bold outlines)

## Git & GitHub

- Remote: `https://github.com/kevinlim1118/toy-blaster`
- Branch: `master`
- Commit and push after every meaningful change to preserve progress:

```
git add <files>
git commit -m "descriptive message"
git push
```
