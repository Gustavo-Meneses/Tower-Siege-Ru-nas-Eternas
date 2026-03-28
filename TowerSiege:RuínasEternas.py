import streamlit as st
import random
import math
import json
import time

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tower Siege: Ruínas Eternas",
    page_icon="🏰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
GRID_W, GRID_H = 14, 10
CELL = 52        # px per cell
RULER = 22       # px for the coord ruler strip

TOWER_TYPES = {
    "archer": {
        "name": "Arqueiro",
        "emoji": "🏹",
        "cost": 80,
        "damage": 18,
        "range": 3,
        "fire_rate": 1.2,
        "color": "#8BC34A",
        "desc": "Ataque rápido, alcance médio",
        "pixel_color": "#5D8A23",
    },
    "mage": {
        "name": "Mago",
        "emoji": "🔮",
        "cost": 130,
        "damage": 35,
        "range": 2.5,
        "fire_rate": 0.7,
        "color": "#9C27B0",
        "desc": "Dano em área, lento",
        "pixel_color": "#6A0080",
    },
    "ballista": {
        "name": "Balista",
        "emoji": "⚡",
        "cost": 200,
        "damage": 65,
        "range": 4,
        "fire_rate": 0.5,
        "color": "#FF9800",
        "desc": "Dano perfurante brutal",
        "pixel_color": "#B36000",
    },
    "frost": {
        "name": "Gelo",
        "emoji": "❄️",
        "cost": 110,
        "damage": 12,
        "range": 2,
        "fire_rate": 1.0,
        "color": "#00BCD4",
        "desc": "Lentifica inimigos -40%",
        "pixel_color": "#007A8C",
    },
    "cannon": {
        "name": "Canhão",
        "emoji": "💣",
        "cost": 160,
        "damage": 50,
        "range": 2.5,
        "fire_rate": 0.6,
        "color": "#795548",
        "desc": "Explosão 3x3, lento",
        "pixel_color": "#4E342E",
    },
}

ENEMY_TYPES = {
    "goblin": {
        "name": "Goblin",
        "hp_base": 55,
        "speed": 1.4,
        "reward": 12,
        "color": "#4CAF50",
        "size": "small",
    },
    "orc": {
        "name": "Orc",
        "hp_base": 180,
        "speed": 0.8,
        "reward": 25,
        "color": "#8D6E63",
        "size": "medium",
    },
    "skeleton": {
        "name": "Esqueleto",
        "hp_base": 80,
        "speed": 1.2,
        "reward": 18,
        "color": "#ECEFF1",
        "size": "medium",
    },
    "troll": {
        "name": "Troll",
        "hp_base": 400,
        "speed": 0.5,
        "reward": 55,
        "color": "#33691E",
        "size": "large",
    },
    "wraith": {
        "name": "Espectro",
        "hp_base": 120,
        "speed": 1.8,
        "reward": 35,
        "color": "#7E57C2",
        "size": "small",
    },
    "dragon": {
        "name": "Dragão",
        "hp_base": 900,
        "speed": 0.9,
        "reward": 150,
        "color": "#F44336",
        "size": "boss",
    },
}

ROGUELIKE_UPGRADES = [
    {"id": "iron_arrows", "name": "Flechas de Ferro", "desc": "+25% dano Arqueiros", "type": "passive", "icon": "🔩"},
    {"id": "mana_surge", "name": "Surto de Mana", "desc": "+40% dano Magos", "type": "passive", "icon": "⚗️"},
    {"id": "permafrost", "name": "Permafrost", "desc": "Gelo lentifica -60%", "type": "passive", "icon": "🌨️"},
    {"id": "double_shot", "name": "Tiro Duplo", "desc": "Arqueiros disparam 2x", "type": "passive", "icon": "🏹"},
    {"id": "explosive_tip", "name": "Ponta Explosiva", "desc": "Balista causa splash", "type": "passive", "icon": "💥"},
    {"id": "gold_rush", "name": "Corrida do Ouro", "desc": "+50% ouro de inimigos", "type": "passive", "icon": "💰"},
    {"id": "fortify", "name": "Fortalecer", "desc": "+2 vidas extras", "type": "passive", "icon": "🛡️"},
    {"id": "arcane_nexus", "name": "Nexo Arcano", "desc": "Torres custam -20%", "type": "passive", "icon": "🔮"},
    {"id": "chain_lightning", "name": "Relâmpago em Cadeia", "desc": "Mago atinge 3 alvos", "type": "passive", "icon": "⚡"},
    {"id": "titan_barrel", "name": "Barril Titã", "desc": "+80% dano Canhão", "type": "passive", "icon": "🪣"},
]

# Fixed path as list of (col, row) tuples
BASE_PATH = [
    (0,4),(1,4),(2,4),(2,3),(2,2),(3,2),(4,2),(5,2),(5,3),(5,4),(5,5),
    (5,6),(6,6),(7,6),(8,6),(8,5),(8,4),(8,3),(8,2),(9,2),(10,2),(10,3),
    (10,4),(10,5),(10,6),(10,7),(11,7),(12,7),(13,7),
]

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "screen": "menu",          # menu | game | upgrade | gameover | victory
        "wave": 0,
        "gold": 200,
        "lives": 20,
        "score": 0,
        "towers": {},              # key: "col,row" → tower dict
        "enemies": [],             # list of enemy dicts
        "selected_tower": None,    # type key
        "upgrades": [],            # list of upgrade ids acquired
        "combat_log": [],
        "wave_active": False,
        "enemies_spawned": 0,
        "enemies_to_spawn": 0,
        "last_tick": 0.0,
        "pending_upgrades": [],    # upgrade options shown between waves
        "kills": 0,
        "max_waves": 15,
        "anim_events": [],         # for iframe animation triggers
        "tick_counter": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ══════════════════════════════════════════════════════════════════════════════
# GAME LOGIC HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_wave_enemies(wave):
    pool = []
    if wave <= 3:
        pool = ["goblin"] * 6 + ["skeleton"] * 2
    elif wave <= 6:
        pool = ["goblin"] * 5 + ["skeleton"] * 4 + ["orc"] * 2
    elif wave <= 9:
        pool = ["goblin"] * 3 + ["skeleton"] * 4 + ["orc"] * 4 + ["wraith"] * 2
    elif wave <= 12:
        pool = ["skeleton"] * 3 + ["orc"] * 5 + ["wraith"] * 3 + ["troll"] * 1
    else:
        pool = ["orc"] * 4 + ["wraith"] * 4 + ["troll"] * 2 + ["dragon"] * 1
    count = 8 + wave * 2
    return [random.choice(pool) for _ in range(count)]

def spawn_enemy(etype, wave):
    scale = 1 + (wave - 1) * 0.22
    base = ENEMY_TYPES[etype]
    hp = int(base["hp_base"] * scale)
    speed = base["speed"]
    return {
        "id": random.randint(10000, 99999),
        "type": etype,
        "name": base["name"],
        "hp": hp,
        "hp_max": hp,
        "speed": speed,
        "slow": 1.0,        # multiplier (frost)
        "reward": int(base["reward"] * (1.5 if "gold_rush" in st.session_state.upgrades else 1.0)),
        "path_idx": 0,
        "progress": 0.0,    # 0..1 within current segment
        "color": base["color"],
        "size": base["size"],
        "alive": True,
        "reached_end": False,
        "stun": 0,
    }

def dist(ax, ay, bx, by):
    return math.sqrt((ax - bx)**2 + (ay - by)**2)

def apply_upgrades_to_tower(tower):
    t = tower.copy()
    upgrades = st.session_state.upgrades
    if t["type"] == "archer":
        if "iron_arrows" in upgrades: t["damage"] = int(t["damage"] * 1.25)
        if "double_shot" in upgrades: t["fire_rate"] *= 2
    if t["type"] == "mage":
        if "mana_surge" in upgrades: t["damage"] = int(t["damage"] * 1.40)
        if "chain_lightning" in upgrades: t["extra_targets"] = 3
    if t["type"] == "frost":
        t["slow_amount"] = 0.60 if "permafrost" in upgrades else 0.40
    if t["type"] == "ballista":
        if "explosive_tip" in upgrades: t["splash"] = True
    if t["type"] == "cannon":
        if "titan_barrel" in upgrades: t["damage"] = int(t["damage"] * 1.80)
    return t

def get_tower_cost(ttype):
    base = TOWER_TYPES[ttype]["cost"]
    if "arcane_nexus" in st.session_state.upgrades:
        base = int(base * 0.80)
    return base

def tick_game():
    """Single game tick — move enemies, fire towers, collect gold."""
    ss = st.session_state
    if not ss.wave_active:
        return

    events = []
    path = BASE_PATH
    path_len = len(path) - 1

    # ── Spawn enemies ────────────────────────────────────────────────────────
    if ss.enemies_spawned < ss.enemies_to_spawn:
        ss.tick_counter += 1
        if ss.tick_counter % 4 == 0:
            etype = ss._spawn_queue[ss.enemies_spawned]
            ss.enemies.append(spawn_enemy(etype, ss.wave))
            ss.enemies_spawned += 1

    # ── Move enemies ─────────────────────────────────────────────────────────
    alive_enemies = []
    for e in ss.enemies:
        if not e["alive"]:
            continue
        if e["reached_end"]:
            ss.lives = max(0, ss.lives - 1)
            events.append({"type": "life_lost", "x": 0, "y": 4})
            continue

        speed = e["speed"] * e["slow"]
        e["progress"] += speed * 0.12
        while e["progress"] >= 1.0 and e["path_idx"] < path_len - 1:
            e["progress"] -= 1.0
            e["path_idx"] += 1

        if e["path_idx"] >= path_len - 1 and e["progress"] >= 1.0:
            e["reached_end"] = True
            continue

        # Reset slow each tick (applied fresh by towers)
        e["slow"] = 1.0
        alive_enemies.append(e)

    ss.enemies = alive_enemies

    # ── Fire towers ──────────────────────────────────────────────────────────
    for key, tower in ss.towers.items():
        tc, tr = map(int, key.split(","))
        t = apply_upgrades_to_tower(tower)
        rng = t["range"]
        dmg = t["damage"]
        ttype = t["type"]

        targets = []
        for e in ss.enemies:
            if not e["alive"]: continue
            pi = e["path_idx"]
            ec, er = path[pi]
            if dist(tc, tr, ec, er) <= rng:
                targets.append(e)

        if not targets: continue

        # Pick furthest along path
        targets.sort(key=lambda e: e["path_idx"] + e["progress"], reverse=True)

        hit = targets[0]
        extra = t.get("extra_targets", 1)

        for ti, target in enumerate(targets[:extra]):
            if ttype == "frost":
                target["slow"] = 1.0 - t.get("slow_amount", 0.40)
                actual_dmg = dmg
            elif ttype == "cannon" or (ttype == "mage"):
                # Splash / area
                actual_dmg = dmg
                for nb in ss.enemies:
                    if nb["id"] == target["id"]: continue
                    pi2 = nb["path_idx"]
                    nc, nr = path[pi2]
                    tc2, tr2 = path[target["path_idx"]]
                    if dist(tc2, tr2, nc, nr) <= 1.5:
                        nb["hp"] -= int(dmg * 0.6)
                        if nb["hp"] <= 0:
                            nb["alive"] = False
                            ss.gold += nb["reward"]
                            ss.score += nb["reward"] * 10
                            ss.kills += 1
            else:
                actual_dmg = dmg

            target["hp"] -= actual_dmg
            pi3 = target["path_idx"]
            ec3, er3 = path[pi3]
            events.append({
                "type": "hit",
                "tower_type": ttype,
                "ex": ec3, "ey": er3,
                "tx": tc, "ty": tr,
                "dmg": actual_dmg,
            })

            if target["hp"] <= 0:
                target["alive"] = False
                ss.gold += target["reward"]
                ss.score += target["reward"] * 10
                ss.kills += 1
                events.append({"type": "kill", "x": ec3, "y": er3, "etype": target["type"]})

    # Purge dead
    ss.enemies = [e for e in ss.enemies if e["alive"]]

    # ── Check wave end ───────────────────────────────────────────────────────
    if ss.enemies_spawned >= ss.enemies_to_spawn and len(ss.enemies) == 0:
        ss.wave_active = False
        # Wave clear bonus
        bonus = 40 + ss.wave * 15
        ss.gold += bonus
        ss.score += bonus * 5
        events.append({"type": "wave_clear", "bonus": bonus})
        ss.combat_log.append(f"🏆 Onda {ss.wave} completa! +{bonus}g de bônus")

        if ss.wave >= ss.max_waves:
            ss.screen = "victory"
        else:
            # Pick 3 random upgrades not yet owned
            available = [u for u in ROGUELIKE_UPGRADES if u["id"] not in ss.upgrades]
            ss.pending_upgrades = random.sample(available, min(3, len(available)))
            if ss.pending_upgrades:
                ss.screen = "upgrade"

    # ── Lives check ──────────────────────────────────────────────────────────
    if ss.lives <= 0:
        ss.screen = "gameover"

    ss.anim_events = events

def start_wave():
    ss = st.session_state
    ss.wave += 1
    queue = get_wave_enemies(ss.wave)
    ss._spawn_queue = queue
    ss.enemies_to_spawn = len(queue)
    ss.enemies_spawned = 0
    ss.enemies = []
    ss.wave_active = True
    ss.tick_counter = 0
    ss.combat_log.append(f"⚔️ Onda {ss.wave} iniciada! {len(queue)} inimigos se aproximam...")

def reset_game():
    keys = ["wave","gold","lives","score","towers","enemies","selected_tower",
            "upgrades","combat_log","wave_active","enemies_spawned","enemies_to_spawn",
            "last_tick","pending_upgrades","kills","anim_events","tick_counter"]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
    if "_spawn_queue" in st.session_state:
        del st.session_state["_spawn_queue"]
    init_state()
    st.session_state.screen = "game"

# ══════════════════════════════════════════════════════════════════════════════
# CSS GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
def inject_global_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700;900&family=Cinzel:wght@400;600;700&family=MedievalSharp&display=swap');

    :root {
        --bg-deep:   #0A0A0F;
        --bg-panel:  #12121A;
        --bg-card:   #1A1A2E;
        --gold:      #D4AF37;
        --gold-light:#FFD700;
        --red:       #C0392B;
        --green:     #27AE60;
        --blue:      #2980B9;
        --purple:    #8E44AD;
        --border:    #2A2A3E;
        --text:      #E8DCC8;
        --text-dim:  #7A7A8A;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--bg-deep) !important;
        color: var(--text) !important;
        font-family: 'Cinzel', serif !important;
    }

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    footer { display: none !important; }

    [data-testid="stSidebar"] { display: none !important; }

    /* Remove Streamlit padding */
    .block-container {
        padding: 0.5rem 1rem !important;
        max-width: 100% !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1A1A2E, #2A1A0E) !important;
        color: var(--gold) !important;
        border: 1px solid var(--gold) !important;
        border-radius: 4px !important;
        font-family: 'Cinzel', serif !important;
        font-weight: 700 !important;
        font-size: 0.75rem !important;
        padding: 0.3rem 0.6rem !important;
        transition: all 0.2s !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2A2A4E, #3A2A1E) !important;
        border-color: var(--gold-light) !important;
        box-shadow: 0 0 12px rgba(212,175,55,0.4) !important;
    }

    /* Columns gap */
    [data-testid="column"] { padding: 0 4px !important; }

    /* Divider */
    hr { border-color: var(--border) !important; }

    /* Game title */
    .game-title {
        font-family: 'Cinzel Decorative', cursive;
        font-size: 3.2rem;
        font-weight: 900;
        color: var(--gold);
        text-shadow: 0 0 30px rgba(212,175,55,0.6), 0 2px 4px rgba(0,0,0,0.8);
        text-align: center;
        margin: 0;
        line-height: 1.1;
    }

    .game-subtitle {
        font-family: 'Cinzel', serif;
        font-size: 1rem;
        color: var(--text-dim);
        text-align: center;
        letter-spacing: 0.3em;
        text-transform: uppercase;
    }

    /* HUD */
    .hud-bar {
        display: flex;
        gap: 16px;
        align-items: center;
        background: var(--bg-panel);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 8px 16px;
        margin-bottom: 8px;
    }

    .hud-stat {
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: 'Cinzel', serif;
        font-size: 0.85rem;
        font-weight: 700;
    }

    .hud-stat .val { color: var(--gold-light); font-size: 1rem; }
    .hud-stat.lives .val { color: #E74C3C; }
    .hud-stat.score .val { color: #00E5FF; }

    /* Panel */
    .panel {
        background: var(--bg-panel);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 10px;
    }

    .panel-title {
        font-family: 'Cinzel Decorative', cursive;
        font-size: 0.7rem;
        color: var(--gold);
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 8px;
        border-bottom: 1px solid var(--border);
        padding-bottom: 4px;
    }

    /* Tower card */
    .tower-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 6px 8px;
        margin-bottom: 4px;
        cursor: pointer;
        transition: all 0.15s;
    }
    .tower-card:hover, .tower-card.selected {
        border-color: var(--gold);
        box-shadow: 0 0 8px rgba(212,175,55,0.3);
    }
    .tower-card .tc-name { font-size: 0.75rem; font-weight: 700; color: var(--text); }
    .tower-card .tc-cost { font-size: 0.7rem; color: var(--gold); }
    .tower-card .tc-desc { font-size: 0.62rem; color: var(--text-dim); margin-top: 2px; }

    /* Log */
    .log-box {
        background: #0A0A12;
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 6px 8px;
        height: 140px;
        overflow-y: auto;
        font-size: 0.62rem;
        font-family: 'Cinzel', serif;
        color: var(--text-dim);
    }
    .log-entry { margin-bottom: 3px; }
    .log-entry.kill { color: #E74C3C; }
    .log-entry.gold { color: var(--gold); }
    .log-entry.wave { color: #00E5FF; }

    /* Upgrade card */
    .upg-card {
        background: var(--bg-card);
        border: 2px solid var(--border);
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        transition: all 0.2s;
        cursor: pointer;
    }
    .upg-card:hover {
        border-color: var(--gold);
        box-shadow: 0 0 20px rgba(212,175,55,0.3);
        transform: translateY(-2px);
    }
    .upg-icon { font-size: 2.5rem; display: block; margin-bottom: 8px; }
    .upg-name { font-family: 'Cinzel Decorative', cursive; font-size: 0.9rem; color: var(--gold); }
    .upg-desc { font-size: 0.75rem; color: var(--text-dim); margin-top: 6px; }

    /* Progress bar */
    .prog-bg {
        background: #1A1A2E;
        border-radius: 4px;
        height: 8px;
        width: 100%;
        margin-top: 4px;
        overflow: hidden;
    }
    .prog-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s;
    }

    /* Gameover / victory */
    .end-screen {
        text-align: center;
        padding: 60px 20px;
    }
    .end-title {
        font-family: 'Cinzel Decorative', cursive;
        font-size: 4rem;
        font-weight: 900;
        margin-bottom: 16px;
    }
    .end-sub {
        font-family: 'Cinzel', serif;
        font-size: 1.1rem;
        color: var(--text-dim);
        margin-bottom: 32px;
    }

    </style>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# IFRAME: GAME ARENA (full pixel art rendering)
# ══════════════════════════════════════════════════════════════════════════════
def build_arena_html():
    ss = st.session_state
    path = BASE_PATH
    path_set = set(path)

    COLS = GRID_W
    ROWS = GRID_H
    C = CELL
    R = RULER   # ruler strip size

    # Serialize state for JS
    towers_js = json.dumps({
        k: {"type": v["type"]} for k, v in ss.towers.items()
    })

    enemies_js = []
    for e in ss.enemies:
        pi = min(e["path_idx"], len(path) - 2)
        t = max(0.0, min(1.0, e["progress"]))
        c1, r1 = path[pi]
        c2, r2 = path[min(pi + 1, len(path) - 1)]
        ex = c1 + (c2 - c1) * t
        ey = r1 + (r2 - r1) * t
        enemies_js.append({
            "id": e["id"],
            "type": e["type"],
            "x": ex,
            "y": ey,
            "hp_pct": max(0, e["hp"] / e["hp_max"]),
            "color": e["color"],
            "size": e["size"],
        })
    enemies_js = json.dumps(enemies_js)

    path_js  = json.dumps(path)
    events_js = json.dumps(ss.anim_events)
    selected = ss.selected_tower or ""

    tower_sprites = {
        "archer":   "#5D8A23",
        "mage":     "#6A0080",
        "ballista": "#B36000",
        "frost":    "#007A8C",
        "cannon":   "#4E342E",
    }
    tower_sprite_js = json.dumps(tower_sprites)

    # Total canvas size includes ruler strips on top and left
    CANVAS_W = R + COLS * C
    CANVAS_H = R + ROWS * C

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{
    background: #0A0A0F;
    width: {CANVAS_W}px;
    height: {CANVAS_H}px;
    overflow: hidden;
    font-family: monospace;
    user-select: none;
}}
#wrapper {{
    position: relative;
    width: {CANVAS_W}px;
    height: {CANVAS_H}px;
}}
canvas {{
    display: block;
    position: absolute;
    top: 0; left: 0;
    image-rendering: pixelated;
}}
#overlay {{
    position: absolute;
    pointer-events: none;
    top: {R}px; left: {R}px;
    width: {COLS*C}px; height: {ROWS*C}px;
}}
/* ── animations ── */
.anim-hit {{
    position: absolute; border-radius: 50%;
    pointer-events: none;
    animation: hit-anim 0.4s ease-out forwards;
}}
@keyframes hit-anim {{
    0%   {{ transform:scale(0.2); opacity:1; }}
    100% {{ transform:scale(1.8); opacity:0; }}
}}
.anim-kill {{
    position: absolute; pointer-events: none; font-size: 16px;
    animation: kill-anim 0.8s ease-out forwards;
    text-shadow: 0 0 6px rgba(255,200,0,.8);
}}
@keyframes kill-anim {{
    0%   {{ transform:translateY(0);   opacity:1; }}
    100% {{ transform:translateY(-40px); opacity:0; }}
}}
.dmg-num {{
    position: absolute; color: #FF4444; font-size: 13px;
    font-weight: bold; pointer-events: none;
    text-shadow: 0 0 4px #000;
    animation: dmg-anim 0.6s ease-out forwards;
}}
@keyframes dmg-anim {{
    0%   {{ transform:translateY(0) scale(1);   opacity:1; }}
    100% {{ transform:translateY(-30px) scale(.8); opacity:0; }}
}}
#tooltip {{
    position: absolute;
    background: rgba(10,10,20,.94);
    border: 1px solid #D4AF37; border-radius: 4px;
    padding: 5px 9px; font-size: 11px; color: #E8DCC8;
    pointer-events: none; display: none; z-index: 200;
    white-space: nowrap;
}}
</style>
</head>
<body>
<div id="wrapper">
  <canvas id="c" width="{CANVAS_W}" height="{CANVAS_H}"></canvas>
  <div id="overlay"></div>
  <div id="tooltip"></div>
</div>
<script>
const COLS={COLS}, ROWS={ROWS}, C={C}, R={R};
const CW={CANVAS_W}, CH={CANVAS_H};
// grid origin (after ruler)
const OX=R, OY=R;

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

const PATH      = {path_js};
const PATH_SET  = new Set(PATH.map(p=>p[0]+','+p[1]));
const TOWERS    = {towers_js};
const T_COLORS  = {tower_sprite_js};
let   enemies   = {enemies_js};
const EVENTS    = {events_js};
const SELECTED  = "{selected}";

// ── helpers ──────────────────────────────────────────────────────────────────
function lighten(hex, amt) {{
    const n=parseInt(hex.slice(1),16);
    const r=Math.min(255,((n>>16)&0xff)+amt);
    const g=Math.min(255,((n>>8)&0xff)+amt);
    const b=Math.min(255,(n&0xff)+amt);
    return '#'+((r<<16)|(g<<8)|b).toString(16).padStart(6,'0');
}}
function rnd(a,b){{return Math.floor(Math.random()*(b-a))+a;}}

// ── Ruler strips ─────────────────────────────────────────────────────────────
function drawRulers() {{
    // Background of ruler strips
    ctx.fillStyle = '#12121A';
    ctx.fillRect(0, 0, CW, R);   // top strip
    ctx.fillRect(0, 0, R, CH);   // left strip

    // Corner cell
    ctx.fillStyle = '#1A1A2E';
    ctx.fillRect(0, 0, R, R);
    ctx.fillStyle = '#D4AF37';
    ctx.font = 'bold 9px monospace';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('C\\\\R', R/2, R/2);

    // Column numbers (0-13)
    for (let c=0; c<COLS; c++) {{
        const x = OX + c*C + C/2;
        // alternating bg
        ctx.fillStyle = c%2===0 ? '#1A1A2E' : '#141420';
        ctx.fillRect(OX+c*C, 0, C, R);
        // number
        ctx.fillStyle = '#D4AF37';
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(c, x, R/2);
    }}

    // Row numbers (0-9)
    for (let r=0; r<ROWS; r++) {{
        const y = OY + r*C + C/2;
        ctx.fillStyle = r%2===0 ? '#1A1A2E' : '#141420';
        ctx.fillRect(0, OY+r*C, R, C);
        ctx.fillStyle = '#D4AF37';
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(r, R/2, y);
    }}

    // Ruler borders
    ctx.strokeStyle = '#2A2A4A';
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, CW-1, CH-1);
    ctx.beginPath();
    ctx.moveTo(R, 0); ctx.lineTo(R, CH);
    ctx.moveTo(0, R); ctx.lineTo(CW, R);
    ctx.stroke();
}}

// ── Terrain ───────────────────────────────────────────────────────────────────
function drawTerrain() {{
    for (let r=0; r<ROWS; r++) {{
        for (let c=0; c<COLS; c++) {{
            const key = c+','+r;
            const isPath = PATH_SET.has(key);
            const x = OX+c*C, y = OY+r*C;

            if (isPath) {{
                ctx.fillStyle = '#C8A96E';
                ctx.fillRect(x, y, C, C);
                ctx.fillStyle = 'rgba(100,70,30,.3)';
                for (let px=2;px<C;px+=8) for(let py=2;py<C;py+=8)
                    ctx.fillRect(x+px,y+py,2,2);
                ctx.strokeStyle='rgba(160,120,50,.4)';
                ctx.lineWidth=1;
                ctx.strokeRect(x+.5,y+.5,C-1,C-1);
            }} else {{
                const dark=(c+r)%2===0;
                ctx.fillStyle=dark?'#2D5016':'#345C1A';
                ctx.fillRect(x,y,C,C);
                ctx.fillStyle=dark?'#3A6820':'#416824';
                ctx.fillRect(x+2,y+4,3,2);
                ctx.fillRect(x+C-8,y+C-7,3,2);
                ctx.fillRect(x+C/2-2,y+C/2,3,2);
                ctx.strokeStyle='rgba(0,0,0,.15)'; ctx.lineWidth=1;
                ctx.strokeRect(x+.5,y+.5,C-1,C-1);
            }}
        }}
    }}

    // Path arrows
    ctx.fillStyle='rgba(100,70,20,.45)';
    for (let i=1; i<PATH.length; i++) {{
        const [c1,r1]=PATH[i-1],[c2,r2]=PATH[i];
        const cx=OX+(c1+c2)/2*C+C/2, cy=OY+(r1+r2)/2*C+C/2;
        const ang=Math.atan2(r2-r1,c2-c1);
        ctx.save(); ctx.translate(cx,cy); ctx.rotate(ang);
        ctx.beginPath(); ctx.moveTo(7,0); ctx.lineTo(-5,-5); ctx.lineTo(-5,5);
        ctx.closePath(); ctx.fill(); ctx.restore();
    }}

    // START / END
    const [sc,sr]=PATH[0];
    ctx.fillStyle='rgba(0,200,0,.35)';
    ctx.fillRect(OX+sc*C,OY+sr*C,C,C);
    ctx.fillStyle='#00FF88'; ctx.font='bold 10px monospace';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText('▶ START',OX+sc*C+C/2,OY+sr*C+C/2);

    const [ec,er]=PATH[PATH.length-1];
    ctx.fillStyle='rgba(200,0,0,.35)';
    ctx.fillRect(OX+ec*C,OY+er*C,C,C);
    ctx.fillStyle='#FF4444';
    ctx.fillText('END ✖',OX+ec*C+C/2,OY+er*C+C/2);
}}

// ── Hover highlight ───────────────────────────────────────────────────────────
let hoverC=-1, hoverR=-1;
function drawHover() {{
    if (!SELECTED || hoverC<0) return;
    const key=hoverC+','+hoverR;
    const isPath=PATH_SET.has(key);
    const occupied=TOWERS[key];
    const valid=!isPath&&!occupied;
    ctx.fillStyle=valid?'rgba(212,175,55,.25)':'rgba(200,50,50,.25)';
    ctx.fillRect(OX+hoverC*C,OY+hoverR*C,C,C);
    ctx.strokeStyle=valid?'#D4AF37':'#E74C3C';
    ctx.lineWidth=2;
    ctx.strokeRect(OX+hoverC*C+1,OY+hoverR*C+1,C-2,C-2);
    // Coord label on cell
    ctx.fillStyle=valid?'#D4AF37':'#FF6666';
    ctx.font='bold 10px monospace';
    ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.fillText('('+hoverC+','+hoverR+')',OX+hoverC*C+C/2,OY+hoverR*C+C/2);
}}

// ── Tower sprites ─────────────────────────────────────────────────────────────
function drawPixelTower(cx, cy, ttype) {{
    const color=T_COLORS[ttype]||'#888';
    ctx.fillStyle='#5A4A3A'; ctx.fillRect(cx-10,cy+4,20,8);
    ctx.fillStyle='#6B5B4B'; ctx.fillRect(cx-7,cy-12,14,16);
    ctx.fillStyle='#7A6A5A';
    for(let i=0;i<3;i++) ctx.fillRect(cx-8+i*6,cy-17,4,5);
    ctx.fillStyle=color; ctx.fillRect(cx-4,cy-8,8,10);
    ctx.fillStyle='#0A0A1A'; ctx.fillRect(cx-2,cy-6,4,5);
    const icons={{archer:'🏹',mage:'🔮',ballista:'⚡',frost:'❄️',cannon:'💣'}};
    ctx.font='14px serif'; ctx.textAlign='center'; ctx.textBaseline='alphabetic';
    ctx.fillText(icons[ttype]||'🗼', cx, cy-20);
}}

function drawTowers() {{
    for (const [key,t] of Object.entries(TOWERS)) {{
        const [c,r]=key.split(',').map(Number);
        drawPixelTower(OX+c*C+C/2, OY+r*C+C/2, t.type);
    }}
    if(SELECTED) canvas.style.cursor='crosshair';
    else          canvas.style.cursor='default';
}}

// ── Enemy sprites ─────────────────────────────────────────────────────────────
function drawEnemy(e) {{
    const px=OX+e.x*C+C/2, py=OY+e.y*C+C/2;
    const sz=e.size==='boss'?22:e.size==='large'?18:e.size==='medium'?14:11;
    ctx.save();
    ctx.fillStyle='rgba(0,0,0,.4)';
    ctx.beginPath(); ctx.ellipse(px,py+sz-2,sz*.7,4,0,0,Math.PI*2); ctx.fill();
    ctx.fillStyle=e.color; ctx.fillRect(px-sz/2,py-sz,sz,sz*1.2);
    ctx.fillStyle=lighten(e.color,20); ctx.fillRect(px-sz*.4,py-sz*1.6,sz*.8,sz*.7);
    ctx.fillStyle='#000';
    ctx.fillRect(px-sz*.25,py-sz*1.4,3,3);
    ctx.fillRect(px+sz*.1, py-sz*1.4,3,3);
    ctx.fillStyle='#200000'; ctx.fillRect(px-sz*.8,py-sz*1.9,sz*1.6,5);
    ctx.fillStyle=e.hp_pct>.5?'#27AE60':e.hp_pct>.25?'#F39C12':'#E74C3C';
    ctx.fillRect(px-sz*.8,py-sz*1.9,sz*1.6*e.hp_pct,5);
    ctx.restore();
}}

// ── Main render ───────────────────────────────────────────────────────────────
function render() {{
    ctx.clearRect(0,0,CW,CH);
    drawTerrain();
    drawTowers();
    enemies.forEach(drawEnemy);
    drawHover();   // on top of everything
    drawRulers();  // rulers always on top
}}

// ── Animate events ─────────────────────────────────────────────────────────────
const overlay=document.getElementById('overlay');

function spawnHitFx(ex,ey,ttype){{
    const px=ex*C+C/2, py=ey*C+C/2;
    const el=document.createElement('div'); el.className='anim-hit';
    const cols={{archer:'#8BC34A',mage:'#9C27B0',ballista:'#FF9800',frost:'#00BCD4',cannon:'#795548'}};
    el.style.cssText=`width:20px;height:20px;background:${{cols[ttype]||'#FFF'}};
        left:${{px-10}}px;top:${{py-10}}px;opacity:.8;`;
    overlay.appendChild(el); setTimeout(()=>el.remove(),400);
}}
function spawnKillFx(ex,ey){{
    const px=ex*C+C/2, py=ey*C+C/2;
    const el=document.createElement('div'); el.className='anim-kill';
    el.textContent='💀';
    el.style.cssText=`left:${{px-10}}px;top:${{py-20}}px;`;
    overlay.appendChild(el); setTimeout(()=>el.remove(),800);
}}
function spawnDmgNum(ex,ey,dmg){{
    const px=ex*C+C/2+rnd(-10,10), py=ey*C+C/2;
    const el=document.createElement('div'); el.className='dmg-num';
    el.textContent='-'+dmg;
    el.style.cssText=`left:${{px}}px;top:${{py}}px;`;
    overlay.appendChild(el); setTimeout(()=>el.remove(),600);
}}

EVENTS.forEach(ev=>{{
    if(ev.type==='hit'){{
        spawnHitFx(ev.ex,ev.ey,ev.tower_type);
        spawnDmgNum(ev.ex,ev.ey,ev.dmg);
    }} else if(ev.type==='kill') {{
        spawnKillFx(ev.x,ev.y);
    }} else if(ev.type==='wave_clear') {{
        const fl=document.createElement('div');
        fl.style.cssText='position:absolute;inset:0;background:rgba(212,175,55,.15);animation:hit-anim .5s ease-out forwards;pointer-events:none;';
        overlay.appendChild(fl); setTimeout(()=>fl.remove(),500);
    }}
}});

// ── Mouse interaction ─────────────────────────────────────────────────────────
const tip=document.getElementById('tooltip');

canvas.addEventListener('mousemove', ev=>{{
    const rect=canvas.getBoundingClientRect();
    const mx=(ev.clientX-rect.left)*(CW/rect.width);
    const my=(ev.clientY-rect.top)*(CH/rect.height);
    const c=Math.floor((mx-OX)/C);
    const r=Math.floor((my-OY)/C);
    if(c>=0&&c<COLS&&r>=0&&r<ROWS){{
        hoverC=c; hoverR=r;
        const key=c+','+r;
        const isPath=PATH_SET.has(key);
        const occupied=TOWERS[key];
        let tipText='Col '+c+' · Linha '+r;
        if(occupied)   tipText+=' — Torre: '+occupied.type;
        else if(isPath) tipText+=' — Caminho (bloqueado)';
        else if(SELECTED) tipText+=' — Clique para construir';
        tip.textContent=tipText;
        tip.style.display='block';
        tip.style.left=(ev.clientX-rect.left+12)+'px';
        tip.style.top=(ev.clientY-rect.top+12)+'px';
    }} else {{
        hoverC=-1; hoverR=-1;
        tip.style.display='none';
    }}
    render();
}});

canvas.addEventListener('mouseleave',()=>{{
    hoverC=-1; hoverR=-1;
    tip.style.display='none';
    render();
}});

// ── CLICK TO PLACE — sends col & row via URL hash → Streamlit detects it ─────
canvas.addEventListener('click', ev=>{{
    if(!SELECTED) return;
    const rect=canvas.getBoundingClientRect();
    const mx=(ev.clientX-rect.left)*(CW/rect.width);
    const my=(ev.clientY-rect.top)*(CH/rect.height);
    const c=Math.floor((mx-OX)/C);
    const r=Math.floor((my-OY)/C);
    if(c<0||c>=COLS||r<0||r>=ROWS) return;
    const key=c+','+r;
    if(PATH_SET.has(key)||TOWERS[key]) return;
    // Write into a hidden input that Streamlit can read via query_params
    // We use the parent window location hash as the communication channel
    window.parent.location.hash='place_'+c+'_'+r+'_'+Date.now();
}});

render();
</script>
</body>
</html>"""
    return html

# ══════════════════════════════════════════════════════════════════════════════
# SCREENS
# ══════════════════════════════════════════════════════════════════════════════

def screen_menu():
    inject_global_css()
    st.markdown("""
    <div style='text-align:center;padding:60px 20px 30px;'>
        <div class='game-title'>⚔️ Tower Siege ⚔️</div>
        <div style='font-family:"Cinzel Decorative",cursive;font-size:1rem;color:#8B6914;letter-spacing:.4em;margin-top:4px;'>RUÍNAS ETERNAS</div>
        <div style='margin:24px auto;max-width:500px;font-size:.85rem;color:#7A7A8A;font-family:Cinzel,serif;line-height:1.8;'>
            Erga suas torres nas ruínas de um castelo maldito.<br>
            Defenda o portão sagrado contra hordas de criaturas das trevas.<br>
            Cada onda superada fortalece sua defesa — mas os inimigos também crescem.<br>
            <em style='color:#D4AF37'>Permadeath. Sem segunda chance. Só a estratégia salva.</em>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("⚔️  INICIAR CAMPANHA", use_container_width=True):
            reset_game()
            st.rerun()

    st.markdown("""
    <div style='display:flex;justify-content:center;gap:40px;margin-top:40px;flex-wrap:wrap;'>
    """, unsafe_allow_html=True)

    for ttype, td in TOWER_TYPES.items():
        st.markdown(f"""
        <div style='background:#12121A;border:1px solid #2A2A3E;border-radius:8px;padding:16px;
                    min-width:140px;text-align:center;font-family:Cinzel,serif;'>
            <div style='font-size:2rem;'>{td['emoji']}</div>
            <div style='color:#D4AF37;font-size:.8rem;font-weight:700;margin:4px 0;'>{td['name']}</div>
            <div style='color:#7A7A8A;font-size:.65rem;'>{td['desc']}</div>
            <div style='color:#D4AF37;font-size:.7rem;margin-top:4px;'>💰 {td['cost']}g</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def screen_game():
    inject_global_css()
    ss = st.session_state

    # Auto-tick every render
    if ss.wave_active:
        for _ in range(6):  # multiple ticks per render for speed
            tick_game()
            if not ss.wave_active:
                break

    # ── HUD ──────────────────────────────────────────────────────────────────
    h1, h2, h3, h4, h5, h6 = st.columns([2,2,2,2,2,2])
    with h1:
        st.markdown(f"""<div class='hud-stat'>⚔️ Onda <span class='val'>{ss.wave}/{ss.max_waves}</span></div>""", unsafe_allow_html=True)
    with h2:
        st.markdown(f"""<div class='hud-stat lives'>❤️ Vidas <span class='val'>{ss.lives}</span></div>""", unsafe_allow_html=True)
    with h3:
        st.markdown(f"""<div class='hud-stat'>💰 Ouro <span class='val'>{ss.gold}g</span></div>""", unsafe_allow_html=True)
    with h4:
        st.markdown(f"""<div class='hud-stat score'>🏆 Score <span class='val'>{ss.score:,}</span></div>""", unsafe_allow_html=True)
    with h5:
        st.markdown(f"""<div class='hud-stat'>💀 Kills <span class='val'>{ss.kills}</span></div>""", unsafe_allow_html=True)
    with h6:
        enemies_alive = len(ss.enemies)
        remaining = ss.enemies_to_spawn - ss.enemies_spawned + enemies_alive if ss.wave_active else 0
        st.markdown(f"""<div class='hud-stat'>👾 Restam <span class='val'>{remaining}</span></div>""", unsafe_allow_html=True)

    st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

    # ── Main layout: arena + sidebar ─────────────────────────────────────────
    arena_col, side_col = st.columns([4, 1])

    # ── Read click-to-place from URL hash set by iframe ─────────────────────
    # JS writes window.parent.location.hash = 'place_C_R_timestamp'
    # Streamlit exposes fragment via st.query_params after the '#'
    raw_hash = st.query_params.get("place", "")
    if not raw_hash:
        # Try reading the hash fragment via a JS trick stored in query param
        pass

    # Inject a tiny script that copies hash → query param on every hash change
    # This bridges the iframe → Streamlit gap reliably
    st.markdown("""
    <script>
    (function(){
        function syncHash(){
            const h = window.location.hash.replace('#','');
            if(h.startsWith('place_')){
                const parts = h.split('_');
                if(parts.length>=4){
                    const c=parts[1], r=parts[2];
                    const url = new URL(window.location.href);
                    url.searchParams.set('place', c+'_'+r);
                    window.history.replaceState(null,'', url.toString());
                    // Trigger Streamlit rerun by submitting a tiny form change
                    window.location.href = url.toString();
                }
            }
        }
        window.addEventListener('hashchange', syncHash);
    })();
    </script>
    """, unsafe_allow_html=True)

    # Check query param set by the hash bridge
    place_param = st.query_params.get("place", "")
    if place_param and ss.selected_tower:
        parts = place_param.split("_")
        if len(parts) == 2:
            try:
                pc, pr = int(parts[0]), int(parts[1])
                key = f"{pc},{pr}"
                path_set = set(map(tuple, BASE_PATH))
                if (pc, pr) not in path_set and key not in ss.towers:
                    cost = get_tower_cost(ss.selected_tower)
                    if ss.gold >= cost:
                        ss.towers[key] = {
                            "type": ss.selected_tower,
                            **{k: v for k, v in TOWER_TYPES[ss.selected_tower].items()},
                        }
                        ss.gold -= cost
                        ss.combat_log.append(
                            f"🏰 {TOWER_TYPES[ss.selected_tower]['name']} erguida em ({pc},{pr})")
                        ss.selected_tower = None
                        # Clear the param
                        st.query_params.pop("place")
                        st.rerun()
            except Exception:
                pass

    with arena_col:
        arena_html = build_arena_html()
        from streamlit.components.v1 import html as st_html
        ARENA_H = RULER + GRID_H * CELL + 4
        st_html(arena_html, height=ARENA_H, scrolling=False)

    with side_col:
        # Tower shop
        st.markdown("<div class='panel-title'>🏰 Torres</div>", unsafe_allow_html=True)
        for ttype, td in TOWER_TYPES.items():
            cost = get_tower_cost(ttype)
            can_afford = ss.gold >= cost
            is_sel = ss.selected_tower == ttype
            sel_style = "border-color:#D4AF37;background:#1A1A2E;" if is_sel else ""
            aff_style = "" if can_afford else "opacity:0.4;"
            st.markdown(f"""
            <div class='tower-card' style='{sel_style}{aff_style}'>
                <div class='tc-name'>{td['emoji']} {td['name']}</div>
                <div class='tc-cost'>💰 {cost}g</div>
                <div class='tc-desc'>{td['desc']}</div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"{'✓ Selecionado' if is_sel else 'Selecionar'}", key=f"sel_{ttype}",
                         disabled=not can_afford, use_container_width=True):
                ss.selected_tower = None if is_sel else ttype
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Tower placement panel ─────────────────────────────────────────────
        if ss.selected_tower:
            td = TOWER_TYPES[ss.selected_tower]
            st.markdown(f"""
            <div style='background:#1A1A2E;border:1px solid #D4AF37;border-radius:6px;
                        padding:8px;margin-bottom:6px;text-align:center;'>
                <div style='font-size:.7rem;color:#D4AF37;font-family:Cinzel,serif;
                            font-weight:700;margin-bottom:4px;'>
                    {td['emoji']} {td['name']} selecionado
                </div>
                <div style='font-size:.6rem;color:#7A7A8A;font-family:Cinzel,serif;'>
                    Passe o mouse no mapa para ver as coordenadas e clique para construir,
                    ou use o formulário abaixo.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div class='panel-title'>📍 Construir em</div>", unsafe_allow_html=True)

            # Two compact columns for col/row inputs
            ci1, ci2 = st.columns(2)
            with ci1:
                col_in = st.number_input("Col", 0, GRID_W-1, 3, key="pc",
                                         help="Coluna (0–13) — veja a régua superior do mapa")
            with ci2:
                row_in = st.number_input("Lin", 0, GRID_H-1, 2, key="pr",
                                         help="Linha (0–9) — veja a régua lateral do mapa")

            # Live validity feedback
            key_preview = f"{col_in},{row_in}"
            path_set_preview = set(map(tuple, BASE_PATH))
            is_path_cell = (col_in, row_in) in path_set_preview
            is_occupied  = key_preview in ss.towers
            cell_ok = not is_path_cell and not is_occupied

            if is_path_cell:
                st.markdown("<div style='font-size:.62rem;color:#E74C3C;font-family:Cinzel,serif;'>⛔ Célula no caminho!</div>", unsafe_allow_html=True)
            elif is_occupied:
                st.markdown("<div style='font-size:.62rem;color:#E74C3C;font-family:Cinzel,serif;'>⛔ Já há uma torre!</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='font-size:.62rem;color:#27AE60;font-family:Cinzel,serif;'>✅ Posição livre ({col_in},{row_in})</div>", unsafe_allow_html=True)

            cost_now = get_tower_cost(ss.selected_tower)
            if st.button(f"🔨 Construir — {cost_now}g", use_container_width=True,
                         disabled=not cell_ok or ss.gold < cost_now):
                ss.towers[key_preview] = {
                    "type": ss.selected_tower,
                    **{k: v for k, v in TOWER_TYPES[ss.selected_tower].items()},
                }
                ss.gold -= cost_now
                ss.combat_log.append(
                    f"🏰 {TOWER_TYPES[ss.selected_tower]['name']} erguida em ({col_in},{row_in})")
                ss.selected_tower = None
                st.rerun()

            if st.button("❌ Cancelar", use_container_width=True):
                ss.selected_tower = None
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Wave control
        if not ss.wave_active:
            if ss.wave < ss.max_waves:
                if st.button(f"⚔️ Onda {ss.wave + 1}", use_container_width=True):
                    start_wave()
                    st.rerun()
            else:
                st.success("Vitória!")
        else:
            st.markdown(f"""<div style='text-align:center;color:#E74C3C;font-family:Cinzel,serif;
                font-size:.75rem;'>⚔️ Onda {ss.wave} ativa!</div>""", unsafe_allow_html=True)
            if st.button("🔄 Atualizar", use_container_width=True):
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Upgrades owned
        if ss.upgrades:
            st.markdown("<div class='panel-title'>✨ Melhorias</div>", unsafe_allow_html=True)
            for uid in ss.upgrades:
                u = next((x for x in ROGUELIKE_UPGRADES if x["id"] == uid), None)
                if u:
                    st.markdown(f"""<div style='font-size:.62rem;color:#D4AF37;font-family:Cinzel,serif;
                        margin-bottom:2px;'>{u['icon']} {u['name']}</div>""", unsafe_allow_html=True)

        # Log
        st.markdown("<div class='panel-title' style='margin-top:8px;'>📜 Log</div>", unsafe_allow_html=True)
        log_html = ""
        for entry in reversed(ss.combat_log[-20:]):
            cls = "kill" if "💀" in entry or "mata" in entry else "gold" if "💰" in entry or "ouro" in entry or "Onda" in entry and "completa" in entry else "wave"
            log_html += f"<div class='log-entry {cls}'>{entry}</div>"
        st.markdown(f"<div class='log-box'>{log_html}</div>", unsafe_allow_html=True)

    # Auto-rerun if wave active
    if ss.wave_active and ss.screen == "game":
        time.sleep(0.15)
        st.rerun()


def screen_upgrade():
    inject_global_css()
    ss = st.session_state

    st.markdown(f"""
    <div style='text-align:center;padding:30px 0 20px;'>
        <div style='font-family:"Cinzel Decorative",cursive;font-size:2rem;color:#D4AF37;
                    text-shadow:0 0 20px rgba(212,175,55,0.5);'>✨ Escolha sua Melhoria ✨</div>
        <div style='font-family:Cinzel,serif;font-size:.85rem;color:#7A7A8A;margin-top:8px;'>
            Onda {ss.wave} superada! Ouro total: {ss.gold}g — Score: {ss.score:,}
        </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(len(ss.pending_upgrades))
    for i, (col, upg) in enumerate(zip(cols, ss.pending_upgrades)):
        with col:
            st.markdown(f"""
            <div class='upg-card'>
                <span class='upg-icon'>{upg['icon']}</span>
                <div class='upg-name'>{upg['name']}</div>
                <div class='upg-desc'>{upg['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"🗡️ Escolher", key=f"upg_{i}", use_container_width=True):
                ss.upgrades.append(upg["id"])
                ss.combat_log.append(f"✨ Melhoria: {upg['name']} ({upg['desc']})")
                ss.pending_upgrades = []
                ss.screen = "game"
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if st.button("⏭️ Pular (sem melhoria)", use_container_width=True):
            ss.pending_upgrades = []
            ss.screen = "game"
            st.rerun()


def screen_gameover():
    inject_global_css()
    ss = st.session_state
    st.markdown(f"""
    <div class='end-screen'>
        <div class='end-title' style='color:#C0392B;text-shadow:0 0 40px rgba(192,57,43,0.7);'>
            💀 DERROTADO 💀
        </div>
        <div class='end-sub'>O castelo caiu. As trevas avançaram.</div>
        <div style='font-family:Cinzel,serif;font-size:1rem;color:#D4AF37;margin-bottom:8px;'>
            Onda alcançada: {ss.wave} / {ss.max_waves}
        </div>
        <div style='font-family:Cinzel,serif;font-size:0.9rem;color:#7A7A8A;'>
            Score final: {ss.score:,} · Kills: {ss.kills} · Torres: {len(ss.towers)}
        </div>
    </div>
    """, unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,1])
    with c2:
        if st.button("🔄 Tentar Novamente", use_container_width=True):
            reset_game()
            st.rerun()
        if st.button("🏠 Menu Principal", use_container_width=True):
            reset_game()
            ss.screen = "menu"
            st.rerun()


def screen_victory():
    inject_global_css()
    ss = st.session_state
    st.markdown(f"""
    <div class='end-screen'>
        <div class='end-title' style='color:#D4AF37;text-shadow:0 0 40px rgba(212,175,55,0.8);'>
            🏆 VITÓRIA! 🏆
        </div>
        <div class='end-sub'>O castelo foi defendido. As criaturas das trevas foram derrotadas!</div>
        <div style='font-family:Cinzel,serif;font-size:1.1rem;color:#D4AF37;margin-bottom:8px;'>
            Todas as {ss.max_waves} ondas superadas!
        </div>
        <div style='font-family:Cinzel,serif;font-size:0.9rem;color:#7A7A8A;'>
            Score final: {ss.score:,} · Kills: {ss.kills} · Torres: {len(ss.towers)}
        </div>
        <div style='margin-top:16px;font-size:.8rem;color:#5A5A6A;font-family:Cinzel,serif;'>
            Melhorias obtidas: {len(ss.upgrades)} / {len(ROGUELIKE_UPGRADES)}
        </div>
    </div>
    """, unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,1])
    with c2:
        if st.button("🔄 Jogar Novamente", use_container_width=True):
            reset_game()
            st.rerun()
        if st.button("🏠 Menu Principal", use_container_width=True):
            reset_game()
            ss.screen = "menu"
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
screen = st.session_state.screen
if screen == "menu":
    screen_menu()
elif screen == "game":
    screen_game()
elif screen == "upgrade":
    screen_upgrade()
elif screen == "gameover":
    screen_gameover()
elif screen == "victory":
    screen_victory()
