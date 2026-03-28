import streamlit as st
import random
import math
import json
import time

# ── Page config ───────────────────────────────────────────────────────────────
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
CELL  = 52
RULER = 22

TOWER_TYPES = {
    "archer":   {"name":"Arqueiro","emoji":"🏹","cost":80,  "damage":18,"range":3,  "fire_rate":1.2,"color":"#8BC34A","desc":"Ataque rápido, alcance médio","pixel_color":"#5D8A23"},
    "mage":     {"name":"Mago",    "emoji":"🔮","cost":130, "damage":35,"range":2.5,"fire_rate":0.7,"color":"#9C27B0","desc":"Dano em área, lento",          "pixel_color":"#6A0080"},
    "ballista": {"name":"Balista", "emoji":"⚡","cost":200, "damage":65,"range":4,  "fire_rate":0.5,"color":"#FF9800","desc":"Dano perfurante brutal",        "pixel_color":"#B36000"},
    "frost":    {"name":"Gelo",    "emoji":"❄️","cost":110, "damage":12,"range":2,  "fire_rate":1.0,"color":"#00BCD4","desc":"Lentifica inimigos -40%",       "pixel_color":"#007A8C"},
    "cannon":   {"name":"Canhão",  "emoji":"💣","cost":160, "damage":50,"range":2.5,"fire_rate":0.6,"color":"#795548","desc":"Explosão 3x3, lento",           "pixel_color":"#4E342E"},
}

# HP buffed ~2.5× vs original — fights last much longer
ENEMY_TYPES = {
    "goblin":   {"name":"Goblin",   "hp_base":140,  "speed":1.4,"reward":12, "color":"#4CAF50","size":"small"},
    "orc":      {"name":"Orc",      "hp_base":480,  "speed":0.8,"reward":25, "color":"#8D6E63","size":"medium"},
    "skeleton": {"name":"Esqueleto","hp_base":220,  "speed":1.2,"reward":18, "color":"#ECEFF1","size":"medium"},
    "troll":    {"name":"Troll",    "hp_base":1100, "speed":0.5,"reward":55, "color":"#33691E","size":"large"},
    "wraith":   {"name":"Espectro", "hp_base":320,  "speed":1.8,"reward":35, "color":"#7E57C2","size":"small"},
    "dragon":   {"name":"Dragão",   "hp_base":2400, "speed":0.9,"reward":150,"color":"#F44336","size":"boss"},
}

ROGUELIKE_UPGRADES = [
    {"id":"iron_arrows",    "name":"Flechas de Ferro",    "desc":"+25% dano Arqueiros",   "icon":"🔩"},
    {"id":"mana_surge",     "name":"Surto de Mana",       "desc":"+40% dano Magos",       "icon":"⚗️"},
    {"id":"permafrost",     "name":"Permafrost",          "desc":"Gelo lentifica -60%",   "icon":"🌨️"},
    {"id":"double_shot",    "name":"Tiro Duplo",          "desc":"Arqueiros disparam 2×", "icon":"🏹"},
    {"id":"explosive_tip",  "name":"Ponta Explosiva",     "desc":"Balista causa splash",  "icon":"💥"},
    {"id":"gold_rush",      "name":"Corrida do Ouro",     "desc":"+50% ouro de inimigos", "icon":"💰"},
    {"id":"fortify",        "name":"Fortalecer",          "desc":"+2 vidas extras",       "icon":"🛡️"},
    {"id":"arcane_nexus",   "name":"Nexo Arcano",         "desc":"Torres custam -20%",    "icon":"🔮"},
    {"id":"chain_lightning","name":"Relâmpago em Cadeia", "desc":"Mago atinge 3 alvos",   "icon":"⚡"},
    {"id":"titan_barrel",   "name":"Barril Titã",         "desc":"+80% dano Canhão",      "icon":"🪣"},
]

# ══════════════════════════════════════════════════════════════════════════════
# RANDOM MAP GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
def generate_path(seed: int):
    """Generate a random snake-path from left edge to right edge."""
    rng  = random.Random(seed)
    COLS = GRID_W
    ROWS = GRID_H

    entry_row = rng.randint(1, ROWS - 2)
    exit_row  = rng.randint(1, ROWS - 2)

    path:    list = []
    visited: set  = set()

    col, row = 0, entry_row
    path.append((col, row))
    visited.add((col, row))

    while col < COLS - 1:
        # Random vertical detour before stepping right
        if rng.random() < 0.45 and col < COLS - 2:
            direction = rng.choice([-1, 1])
            length    = rng.randint(1, 3)
            for _ in range(length):
                nr = row + direction
                if 0 < nr < ROWS - 1 and (col, nr) not in visited:
                    row = nr
                    path.append((col, row))
                    visited.add((col, row))
                else:
                    break
        col += 1
        if (col, row) not in visited:
            path.append((col, row))
            visited.add((col, row))

    # Steer toward exit row
    while row != exit_row:
        direction = 1 if exit_row > row else -1
        nr = row + direction
        if 0 < nr < ROWS - 1 and (col, nr) not in visited:
            row = nr
            path.append((col, row))
            visited.add((col, row))
        else:
            break

    return path

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "screen":           "menu",
        "wave":             0,
        "gold":             200,
        "lives":            20,
        "score":            0,
        "towers":           {},
        "enemies":          [],
        "selected_tower":   None,
        "upgrades":         [],
        "combat_log":       [],
        "wave_active":      False,
        "enemies_spawned":  0,
        "enemies_to_spawn": 0,
        "pending_upgrades": [],
        "kills":            0,
        "max_waves":        15,
        "anim_events":      [],
        "tick_counter":     0,
        "map_seed":         42,
        "pending_place":    "",   # "col,row" — set by click bridge
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def current_path():
    return generate_path(st.session_state.map_seed)

# ══════════════════════════════════════════════════════════════════════════════
# GAME LOGIC
# ══════════════════════════════════════════════════════════════════════════════
def get_wave_enemies(wave):
    if wave <= 3:
        pool = ["goblin"]*6 + ["skeleton"]*2
    elif wave <= 6:
        pool = ["goblin"]*5 + ["skeleton"]*4 + ["orc"]*2
    elif wave <= 9:
        pool = ["goblin"]*3 + ["skeleton"]*4 + ["orc"]*4 + ["wraith"]*2
    elif wave <= 12:
        pool = ["skeleton"]*3 + ["orc"]*5 + ["wraith"]*3 + ["troll"]*1
    else:
        pool = ["orc"]*4 + ["wraith"]*4 + ["troll"]*2 + ["dragon"]*1
    count = 8 + wave * 2
    return [random.choice(pool) for _ in range(count)]


def spawn_enemy(etype, wave):
    scale = 1 + (wave - 1) * 0.15   # +15%/wave — slower than before
    base  = ENEMY_TYPES[etype]
    hp    = int(base["hp_base"] * scale)
    gold_mult = 1.5 if "gold_rush" in st.session_state.upgrades else 1.0
    return {
        "id": random.randint(10000, 99999), "type": etype, "name": base["name"],
        "hp": hp, "hp_max": hp, "speed": base["speed"], "slow": 1.0,
        "reward": int(base["reward"] * gold_mult),
        "path_idx": 0, "progress": 0.0,
        "color": base["color"], "size": base["size"],
        "alive": True, "reached_end": False,
    }


def dist(ax, ay, bx, by):
    return math.sqrt((ax-bx)**2 + (ay-by)**2)


def apply_upgrades_to_tower(tower):
    t = tower.copy()
    upg = st.session_state.upgrades
    if t["type"] == "archer":
        if "iron_arrows"  in upg: t["damage"] = int(t["damage"]*1.25)
        if "double_shot"  in upg: t["fire_rate"] *= 2
    if t["type"] == "mage":
        if "mana_surge"       in upg: t["damage"] = int(t["damage"]*1.40)
        if "chain_lightning"  in upg: t["extra_targets"] = 3
    if t["type"] == "frost":
        t["slow_amount"] = 0.60 if "permafrost" in upg else 0.40
    if t["type"] == "ballista":
        if "explosive_tip" in upg: t["splash"] = True
    if t["type"] == "cannon":
        if "titan_barrel" in upg: t["damage"] = int(t["damage"]*1.80)
    return t


def get_tower_cost(ttype):
    base = TOWER_TYPES[ttype]["cost"]
    return int(base * 0.80) if "arcane_nexus" in st.session_state.upgrades else base


def tick_game():
    ss   = st.session_state
    if not ss.wave_active:
        return
    path     = current_path()
    path_len = len(path) - 1
    events   = []

    # Spawn
    if ss.enemies_spawned < ss.enemies_to_spawn:
        ss.tick_counter += 1
        if ss.tick_counter % 4 == 0:
            etype = ss._spawn_queue[ss.enemies_spawned]
            ss.enemies.append(spawn_enemy(etype, ss.wave))
            ss.enemies_spawned += 1

    # Move
    alive = []
    for e in ss.enemies:
        if not e["alive"]: continue
        if e["reached_end"]:
            ss.lives = max(0, ss.lives - 1)
            continue
        e["progress"] += e["speed"] * e["slow"] * 0.12
        while e["progress"] >= 1.0 and e["path_idx"] < path_len - 1:
            e["progress"] -= 1.0
            e["path_idx"] += 1
        if e["path_idx"] >= path_len - 1 and e["progress"] >= 1.0:
            e["reached_end"] = True
            continue
        e["slow"] = 1.0
        alive.append(e)
    ss.enemies = alive

    # Towers fire
    for key, tower in ss.towers.items():
        tc, tr = map(int, key.split(","))
        t      = apply_upgrades_to_tower(tower)
        targets = [
            e for e in ss.enemies
            if e["alive"] and dist(tc, tr, *path[e["path_idx"]]) <= t["range"]
        ]
        if not targets: continue
        targets.sort(key=lambda e: e["path_idx"] + e["progress"], reverse=True)

        for target in targets[:t.get("extra_targets", 1)]:
            ec, er = path[target["path_idx"]]
            if t["type"] == "frost":
                target["slow"] = 1.0 - t.get("slow_amount", 0.40)
                dmg = t["damage"]
            elif t["type"] in ("cannon", "mage"):
                dmg = t["damage"]
                for nb in ss.enemies:
                    nc, nr = path[nb["path_idx"]]
                    if nb["id"] != target["id"] and dist(ec, er, nc, nr) <= 1.5:
                        nb["hp"] -= int(dmg * 0.6)
                        if nb["hp"] <= 0:
                            nb["alive"] = False
                            ss.gold += nb["reward"]; ss.score += nb["reward"]*10; ss.kills += 1
            else:
                dmg = t["damage"]

            target["hp"] -= dmg
            events.append({"type":"hit","tower_type":t["type"],"ex":ec,"ey":er,"dmg":dmg})
            if target["hp"] <= 0:
                target["alive"] = False
                ss.gold += target["reward"]; ss.score += target["reward"]*10; ss.kills += 1
                events.append({"type":"kill","x":ec,"y":er})

    ss.enemies = [e for e in ss.enemies if e["alive"]]

    # Wave end
    if ss.enemies_spawned >= ss.enemies_to_spawn and len(ss.enemies) == 0:
        ss.wave_active = False
        bonus = 40 + ss.wave * 15
        ss.gold += bonus; ss.score += bonus * 5
        events.append({"type":"wave_clear"})
        ss.combat_log.append(f"🏆 Onda {ss.wave} completa! +{bonus}g de bônus")
        if ss.wave >= ss.max_waves:
            ss.screen = "victory"
        else:
            avail = [u for u in ROGUELIKE_UPGRADES if u["id"] not in ss.upgrades]
            ss.pending_upgrades = random.sample(avail, min(3, len(avail)))
            if ss.pending_upgrades:
                ss.screen = "upgrade"

    if ss.lives <= 0:
        ss.screen = "gameover"

    ss.anim_events = events


def start_wave():
    ss = st.session_state
    ss.wave += 1
    queue = get_wave_enemies(ss.wave)
    ss._spawn_queue     = queue
    ss.enemies_to_spawn = len(queue)
    ss.enemies_spawned  = 0
    ss.enemies          = []
    ss.wave_active      = True
    ss.tick_counter     = 0
    ss.combat_log.append(f"⚔️ Onda {ss.wave} iniciada! {len(queue)} inimigos se aproximam...")


def reset_game():
    keys = ["wave","gold","lives","score","towers","enemies","selected_tower",
            "upgrades","combat_log","wave_active","enemies_spawned","enemies_to_spawn",
            "pending_upgrades","kills","anim_events","tick_counter",
            "pending_place","_spawn_queue"]
    for k in keys:
        st.session_state.pop(k, None)
    st.session_state.map_seed = random.randint(1, 99999)
    init_state()
    st.session_state.screen = "game"

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
def inject_global_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700;900&family=Cinzel:wght@400;600;700&display=swap');
    :root{--bg-deep:#0A0A0F;--bg-panel:#12121A;--bg-card:#1A1A2E;
          --gold:#D4AF37;--gold-light:#FFD700;--border:#2A2A3E;--text:#E8DCC8;--text-dim:#7A7A8A;}
    html,body,[data-testid="stAppViewContainer"]{background:var(--bg-deep)!important;color:var(--text)!important;font-family:'Cinzel',serif!important;}
    [data-testid="stHeader"],[data-testid="stToolbar"],footer,[data-testid="stSidebar"]{display:none!important;}
    .block-container{padding:.5rem 1rem!important;max-width:100%!important;}
    .stButton>button{background:linear-gradient(135deg,#1A1A2E,#2A1A0E)!important;color:var(--gold)!important;
        border:1px solid var(--gold)!important;border-radius:4px!important;font-family:'Cinzel',serif!important;
        font-weight:700!important;font-size:.75rem!important;padding:.3rem .6rem!important;
        transition:all .2s!important;text-transform:uppercase!important;letter-spacing:.05em!important;}
    .stButton>button:hover{background:linear-gradient(135deg,#2A2A4E,#3A2A1E)!important;
        border-color:var(--gold-light)!important;box-shadow:0 0 12px rgba(212,175,55,.4)!important;}
    [data-testid="column"]{padding:0 4px!important;}
    hr{border-color:var(--border)!important;}
    .game-title{font-family:'Cinzel Decorative',cursive;font-size:3.2rem;font-weight:900;color:var(--gold);
        text-shadow:0 0 30px rgba(212,175,55,.6),0 2px 4px rgba(0,0,0,.8);text-align:center;margin:0;line-height:1.1;}
    .hud-stat{display:flex;align-items:center;gap:6px;font-family:'Cinzel',serif;font-size:.85rem;font-weight:700;}
    .hud-stat .val{color:var(--gold-light);font-size:1rem;}
    .hud-stat.lives .val{color:#E74C3C;}
    .hud-stat.score .val{color:#00E5FF;}
    .panel-title{font-family:'Cinzel Decorative',cursive;font-size:.7rem;color:var(--gold);
        letter-spacing:.15em;text-transform:uppercase;margin-bottom:8px;border-bottom:1px solid var(--border);padding-bottom:4px;}
    .tower-card{background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:6px 8px;margin-bottom:4px;}
    .tower-card .tc-name{font-size:.75rem;font-weight:700;color:var(--text);}
    .tower-card .tc-cost{font-size:.7rem;color:var(--gold);}
    .tower-card .tc-desc{font-size:.62rem;color:var(--text-dim);margin-top:2px;}
    .log-box{background:#0A0A12;border:1px solid var(--border);border-radius:4px;padding:6px 8px;
        height:140px;overflow-y:auto;font-size:.62rem;font-family:'Cinzel',serif;color:var(--text-dim);}
    .log-entry{margin-bottom:3px;}
    .log-entry.kill{color:#E74C3C;}
    .log-entry.gold{color:var(--gold);}
    .upg-card{background:var(--bg-card);border:2px solid var(--border);border-radius:8px;padding:20px;text-align:center;}
    .upg-icon{font-size:2.5rem;display:block;margin-bottom:8px;}
    .upg-name{font-family:'Cinzel Decorative',cursive;font-size:.9rem;color:var(--gold);}
    .upg-desc{font-size:.75rem;color:var(--text-dim);margin-top:6px;}
    .end-screen{text-align:center;padding:60px 20px;}
    .end-title{font-family:'Cinzel Decorative',cursive;font-size:4rem;font-weight:900;margin-bottom:16px;}
    .end-sub{font-family:'Cinzel',serif;font-size:1.1rem;color:var(--text-dim);margin-bottom:32px;}
    </style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ARENA HTML  (Canvas 2D, rulers, hover, click bridge)
# ══════════════════════════════════════════════════════════════════════════════
def build_arena_html(path):
    ss   = st.session_state
    C, R = CELL, RULER
    COLS, ROWS = GRID_W, GRID_H
    CW   = R + COLS * C
    CH   = R + ROWS * C
    OX, OY = R, R

    towers_js = json.dumps({k: {"type": v["type"]} for k, v in ss.towers.items()})

    enemies_list = []
    for e in ss.enemies:
        pi     = min(e["path_idx"], len(path)-2)
        t      = max(0.0, min(1.0, e["progress"]))
        c1, r1 = path[pi]
        c2, r2 = path[min(pi+1, len(path)-1)]
        enemies_list.append({
            "id": e["id"], "x": c1+(c2-c1)*t, "y": r1+(r2-r1)*t,
            "hp_pct": max(0, e["hp"]/e["hp_max"]),
            "color": e["color"], "size": e["size"],
        })

    enemies_js  = json.dumps(enemies_list)
    path_js     = json.dumps(path)
    events_js   = json.dumps(ss.anim_events)
    selected    = ss.selected_tower or ""
    tcolors_js  = json.dumps({
        "archer":"#5D8A23","mage":"#6A0080","ballista":"#B36000",
        "frost":"#007A8C","cannon":"#4E342E",
    })

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#0A0A0F;width:{CW}px;height:{CH}px;overflow:hidden;font-family:monospace;user-select:none;}}
#w{{position:relative;width:{CW}px;height:{CH}px;}}
canvas{{display:block;position:absolute;top:0;left:0;image-rendering:pixelated;}}
#ov{{position:absolute;pointer-events:none;top:{OY}px;left:{OX}px;width:{COLS*C}px;height:{ROWS*C}px;}}
.ah{{position:absolute;border-radius:50%;pointer-events:none;animation:ha .4s ease-out forwards;}}
@keyframes ha{{0%{{transform:scale(.2);opacity:1;}}100%{{transform:scale(1.8);opacity:0;}}}}
.ak{{position:absolute;pointer-events:none;font-size:16px;animation:ka .8s ease-out forwards;}}
@keyframes ka{{0%{{transform:translateY(0);opacity:1;}}100%{{transform:translateY(-40px);opacity:0;}}}}
.dn{{position:absolute;color:#FF4444;font-size:13px;font-weight:bold;pointer-events:none;
     text-shadow:0 0 4px #000;animation:da .6s ease-out forwards;}}
@keyframes da{{0%{{transform:translateY(0) scale(1);opacity:1;}}100%{{transform:translateY(-30px) scale(.8);opacity:0;}}}}
#tip{{position:absolute;background:rgba(10,10,20,.94);border:1px solid #D4AF37;border-radius:4px;
      padding:5px 9px;font-size:11px;color:#E8DCC8;pointer-events:none;display:none;z-index:200;white-space:nowrap;}}
</style></head><body>
<div id="w">
  <canvas id="c" width="{CW}" height="{CH}"></canvas>
  <div id="ov"></div>
  <div id="tip"></div>
</div>
<script>
const COLS={COLS},ROWS={ROWS},C={C},R={R},CW={CW},CH={CH},OX={OX},OY={OY};
const cv=document.getElementById('c'),ctx=cv.getContext('2d');
const PATH={path_js};
const PS=new Set(PATH.map(p=>p[0]+','+p[1]));
const TW={towers_js};
const TC={tcolors_js};
const EN={enemies_js};
const EV={events_js};
const SEL="{selected}";

function lt(h,a){{const n=parseInt(h.slice(1),16),r=Math.min(255,((n>>16)&255)+a),g=Math.min(255,((n>>8)&255)+a),b=Math.min(255,(n&255)+a);return'#'+((r<<16)|(g<<8)|b).toString(16).padStart(6,'0');}}
function rn(a,b){{return Math.floor(Math.random()*(b-a))+a;}}

function drawRulers(){{
    ctx.fillStyle='#12121A';ctx.fillRect(0,0,CW,R);ctx.fillRect(0,0,R,CH);
    ctx.fillStyle='#1A1A2E';ctx.fillRect(0,0,R,R);
    ctx.fillStyle='#D4AF37';ctx.font='bold 9px monospace';ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText('C\\\\R',R/2,R/2);
    for(let c=0;c<COLS;c++){{
        ctx.fillStyle=c%2?'#141420':'#1A1A2E';ctx.fillRect(OX+c*C,0,C,R);
        ctx.fillStyle='#D4AF37';ctx.font='bold 11px monospace';
        ctx.textAlign='center';ctx.textBaseline='middle';
        ctx.fillText(c,OX+c*C+C/2,R/2);
    }}
    for(let r=0;r<ROWS;r++){{
        ctx.fillStyle=r%2?'#141420':'#1A1A2E';ctx.fillRect(0,OY+r*C,R,C);
        ctx.fillStyle='#D4AF37';ctx.font='bold 11px monospace';
        ctx.textAlign='center';ctx.textBaseline='middle';
        ctx.fillText(r,R/2,OY+r*C+C/2);
    }}
    ctx.strokeStyle='#2A2A4A';ctx.lineWidth=1;
    ctx.strokeRect(.5,.5,CW-1,CH-1);
    ctx.beginPath();ctx.moveTo(R,0);ctx.lineTo(R,CH);ctx.moveTo(0,R);ctx.lineTo(CW,R);ctx.stroke();
}}

function drawTerrain(){{
    for(let r=0;r<ROWS;r++)for(let c=0;c<COLS;c++){{
        const k=c+','+r,ip=PS.has(k),x=OX+c*C,y=OY+r*C;
        if(ip){{
            ctx.fillStyle='#C8A96E';ctx.fillRect(x,y,C,C);
            ctx.fillStyle='rgba(100,70,30,.3)';
            for(let px=2;px<C;px+=8)for(let py=2;py<C;py+=8)ctx.fillRect(x+px,y+py,2,2);
            ctx.strokeStyle='rgba(160,120,50,.4)';ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,C-1,C-1);
        }}else{{
            const dk=(c+r)%2;
            ctx.fillStyle=dk?'#2D5016':'#345C1A';ctx.fillRect(x,y,C,C);
            ctx.fillStyle=dk?'#3A6820':'#416824';
            ctx.fillRect(x+2,y+4,3,2);ctx.fillRect(x+C-8,y+C-7,3,2);ctx.fillRect(x+C/2-2,y+C/2,3,2);
            ctx.strokeStyle='rgba(0,0,0,.15)';ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,C-1,C-1);
        }}
    }}
    ctx.fillStyle='rgba(100,70,20,.45)';
    for(let i=1;i<PATH.length;i++){{
        const[c1,r1]=PATH[i-1],[c2,r2]=PATH[i];
        const cx=OX+(c1+c2)/2*C+C/2,cy=OY+(r1+r2)/2*C+C/2,ag=Math.atan2(r2-r1,c2-c1);
        ctx.save();ctx.translate(cx,cy);ctx.rotate(ag);
        ctx.beginPath();ctx.moveTo(7,0);ctx.lineTo(-5,-5);ctx.lineTo(-5,5);ctx.closePath();ctx.fill();ctx.restore();
    }}
    const[sc,sr]=PATH[0];
    ctx.fillStyle='rgba(0,200,0,.35)';ctx.fillRect(OX+sc*C,OY+sr*C,C,C);
    ctx.fillStyle='#00FF88';ctx.font='bold 10px monospace';ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText('▶ START',OX+sc*C+C/2,OY+sr*C+C/2);
    const[ec,er]=PATH[PATH.length-1];
    ctx.fillStyle='rgba(200,0,0,.35)';ctx.fillRect(OX+ec*C,OY+er*C,C,C);
    ctx.fillStyle='#FF4444';ctx.fillText('END ✖',OX+ec*C+C/2,OY+er*C+C/2);
}}

let hC=-1,hR=-1;
function drawHover(){{
    if(!SEL||hC<0)return;
    const k=hC+','+hR,v=!PS.has(k)&&!TW[k];
    ctx.fillStyle=v?'rgba(212,175,55,.28)':'rgba(200,50,50,.28)';
    ctx.fillRect(OX+hC*C,OY+hR*C,C,C);
    ctx.strokeStyle=v?'#D4AF37':'#E74C3C';ctx.lineWidth=2;
    ctx.strokeRect(OX+hC*C+1,OY+hR*C+1,C-2,C-2);
    ctx.fillStyle=v?'#D4AF37':'#FF6666';
    ctx.font='bold 10px monospace';ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillText('('+hC+','+hR+')',OX+hC*C+C/2,OY+hR*C+C/2);
}}

function drawTower(cx,cy,tp){{
    const col=TC[tp]||'#888';
    ctx.fillStyle='#5A4A3A';ctx.fillRect(cx-10,cy+4,20,8);
    ctx.fillStyle='#6B5B4B';ctx.fillRect(cx-7,cy-12,14,16);
    ctx.fillStyle='#7A6A5A';
    for(let i=0;i<3;i++)ctx.fillRect(cx-8+i*6,cy-17,4,5);
    ctx.fillStyle=col;ctx.fillRect(cx-4,cy-8,8,10);
    ctx.fillStyle='#0A0A1A';ctx.fillRect(cx-2,cy-6,4,5);
    const ic={{archer:'🏹',mage:'🔮',ballista:'⚡',frost:'❄️',cannon:'💣'}};
    ctx.font='14px serif';ctx.textAlign='center';ctx.textBaseline='alphabetic';
    ctx.fillText(ic[tp]||'🗼',cx,cy-20);
}}

function drawEnemy(e){{
    const px=OX+e.x*C+C/2,py=OY+e.y*C+C/2;
    const sz=e.size==='boss'?22:e.size==='large'?18:e.size==='medium'?14:11;
    ctx.save();
    ctx.fillStyle='rgba(0,0,0,.4)';ctx.beginPath();ctx.ellipse(px,py+sz-2,sz*.7,4,0,0,Math.PI*2);ctx.fill();
    ctx.fillStyle=e.color;ctx.fillRect(px-sz/2,py-sz,sz,sz*1.2);
    ctx.fillStyle=lt(e.color,20);ctx.fillRect(px-sz*.4,py-sz*1.6,sz*.8,sz*.7);
    ctx.fillStyle='#000';ctx.fillRect(px-sz*.25,py-sz*1.4,3,3);ctx.fillRect(px+sz*.1,py-sz*1.4,3,3);
    ctx.fillStyle='#200000';ctx.fillRect(px-sz*.8,py-sz*1.9,sz*1.6,5);
    ctx.fillStyle=e.hp_pct>.5?'#27AE60':e.hp_pct>.25?'#F39C12':'#E74C3C';
    ctx.fillRect(px-sz*.8,py-sz*1.9,sz*1.6*e.hp_pct,5);
    ctx.restore();
}}

function render(){{
    ctx.clearRect(0,0,CW,CH);
    drawTerrain();
    for(const[k,t]of Object.entries(TW)){{const[c,r]=k.split(',').map(Number);drawTower(OX+c*C+C/2,OY+r*C+C/2,t.type);}}
    EN.forEach(drawEnemy);
    drawHover();
    drawRulers();
}}

// FX
const ov=document.getElementById('ov');
function hitFx(ex,ey,tp){{
    const px=ex*C+C/2,py=ey*C+C/2,el=document.createElement('div');el.className='ah';
    const cl={{archer:'#8BC34A',mage:'#9C27B0',ballista:'#FF9800',frost:'#00BCD4',cannon:'#795548'}};
    el.style.cssText=`width:20px;height:20px;background:${{cl[tp]||'#FFF'}};left:${{px-10}}px;top:${{py-10}}px;opacity:.8;`;
    ov.appendChild(el);setTimeout(()=>el.remove(),400);
}}
function killFx(ex,ey){{
    const px=ex*C+C/2,py=ey*C+C/2,el=document.createElement('div');el.className='ak';
    el.textContent='💀';el.style.cssText=`left:${{px-10}}px;top:${{py-20}}px;`;
    ov.appendChild(el);setTimeout(()=>el.remove(),800);
}}
function dmgNum(ex,ey,d){{
    const px=ex*C+C/2+rn(-10,10),py=ey*C+C/2,el=document.createElement('div');el.className='dn';
    el.textContent='-'+d;el.style.cssText=`left:${{px}}px;top:${{py}}px;`;
    ov.appendChild(el);setTimeout(()=>el.remove(),600);
}}
EV.forEach(ev=>{{
    if(ev.type==='hit'){{hitFx(ev.ex,ev.ey,ev.tower_type);dmgNum(ev.ex,ev.ey,ev.dmg);}}
    else if(ev.type==='kill'){{killFx(ev.x,ev.y);}}
    else if(ev.type==='wave_clear'){{
        const fl=document.createElement('div');
        fl.style.cssText='position:absolute;inset:0;background:rgba(212,175,55,.15);animation:ha .5s ease-out forwards;pointer-events:none;';
        ov.appendChild(fl);setTimeout(()=>fl.remove(),500);
    }}
}});

// Tooltip + hover
const tip=document.getElementById('tip');
cv.addEventListener('mousemove',ev=>{{
    const rc=cv.getBoundingClientRect();
    const mx=(ev.clientX-rc.left)*(CW/rc.width),my=(ev.clientY-rc.top)*(CH/rc.height);
    const c=Math.floor((mx-OX)/C),r=Math.floor((my-OY)/C);
    if(c>=0&&c<COLS&&r>=0&&r<ROWS){{
        hC=c;hR=r;
        const k=c+','+r;
        let tx='Col '+c+' · Linha '+r;
        if(TW[k])tx+=' — Torre: '+TW[k].type;
        else if(PS.has(k))tx+=' — Caminho (bloqueado)';
        else if(SEL)tx+=' — Clique para construir';
        tip.textContent=tx;tip.style.display='block';
        tip.style.left=(ev.clientX-rc.left+12)+'px';
        tip.style.top=(ev.clientY-rc.top+12)+'px';
    }}else{{hC=-1;hR=-1;tip.style.display='none';}}
    render();
}});
cv.addEventListener('mouseleave',()=>{{hC=-1;hR=-1;tip.style.display='none';render();}});

// ── CLICK → update URL ?_pc=C&_pr=R  (same-origin, reliable) ─────────────────
cv.addEventListener('click',ev=>{{
    if(!SEL)return;
    const rc=cv.getBoundingClientRect();
    const mx=(ev.clientX-rc.left)*(CW/rc.width),my=(ev.clientY-rc.top)*(CH/rc.height);
    const c=Math.floor((mx-OX)/C),r=Math.floor((my-OY)/C);
    if(c<0||c>=COLS||r<0||r>=ROWS)return;
    const k=c+','+r;
    if(PS.has(k)||TW[k])return;
    // Navigate parent to ?_pc=C&_pr=R — Streamlit picks this up as query_params
    const url=new URL(window.parent.location.href);
    url.searchParams.set('_pc',c);
    url.searchParams.set('_pr',r);
    window.parent.location.href=url.toString();
}});

cv.style.cursor=SEL?'crosshair':'default';
render();
</script></body></html>"""

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
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("⚔️  INICIAR CAMPANHA", use_container_width=True):
            reset_game(); st.rerun()
    st.markdown("<div style='display:flex;justify-content:center;gap:40px;margin-top:40px;flex-wrap:wrap;'>", unsafe_allow_html=True)
    for ttype, td in TOWER_TYPES.items():
        st.markdown(f"""
        <div style='background:#12121A;border:1px solid #2A2A3E;border-radius:8px;padding:16px;
                    min-width:140px;text-align:center;font-family:Cinzel,serif;'>
            <div style='font-size:2rem;'>{td['emoji']}</div>
            <div style='color:#D4AF37;font-size:.8rem;font-weight:700;margin:4px 0;'>{td['name']}</div>
            <div style='color:#7A7A8A;font-size:.65rem;'>{td['desc']}</div>
            <div style='color:#D4AF37;font-size:.7rem;margin-top:4px;'>💰 {td['cost']}g</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def screen_game():
    inject_global_css()
    ss   = st.session_state
    path = current_path()

    # ── Handle click-to-place from URL params ─────────────────────────────────
    # The canvas click sets ?_pc=C&_pr=R on the parent URL; Streamlit picks it up.
    pc_param = st.query_params.get("_pc", "")
    pr_param = st.query_params.get("_pr", "")
    if pc_param and pr_param and ss.selected_tower:
        try:
            pc, pr   = int(pc_param), int(pr_param)
            key      = f"{pc},{pr}"
            path_set = set(map(tuple, path))
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
        except Exception:
            pass
        # Always clear params after processing
        st.query_params.pop("_pc", None)
        st.query_params.pop("_pr", None)
        st.rerun()

    # ── Tick ──────────────────────────────────────────────────────────────────
    if ss.wave_active:
        for _ in range(6):
            tick_game()
            if not ss.wave_active:
                break

    # ── HUD ───────────────────────────────────────────────────────────────────
    h1,h2,h3,h4,h5,h6 = st.columns(6)
    with h1: st.markdown(f"<div class='hud-stat'>⚔️ Onda <span class='val'>{ss.wave}/{ss.max_waves}</span></div>", unsafe_allow_html=True)
    with h2: st.markdown(f"<div class='hud-stat lives'>❤️ Vidas <span class='val'>{ss.lives}</span></div>", unsafe_allow_html=True)
    with h3: st.markdown(f"<div class='hud-stat'>💰 Ouro <span class='val'>{ss.gold}g</span></div>", unsafe_allow_html=True)
    with h4: st.markdown(f"<div class='hud-stat score'>🏆 Score <span class='val'>{ss.score:,}</span></div>", unsafe_allow_html=True)
    with h5: st.markdown(f"<div class='hud-stat'>💀 Kills <span class='val'>{ss.kills}</span></div>", unsafe_allow_html=True)
    with h6:
        rem = (ss.enemies_to_spawn - ss.enemies_spawned + len(ss.enemies)) if ss.wave_active else 0
        st.markdown(f"<div class='hud-stat'>👾 Restam <span class='val'>{rem}</span></div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

    arena_col, side_col = st.columns([4, 1])

    with arena_col:
        from streamlit.components.v1 import html as st_html
        ARENA_H = RULER + GRID_H * CELL + 4
        st_html(build_arena_html(path), height=ARENA_H, scrolling=False)

    with side_col:
        st.markdown(f"<div style='font-size:.6rem;color:#5A5A6A;font-family:Cinzel,serif;margin-bottom:4px;'>🗺️ Mapa #{ss.map_seed}</div>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🏰 Torres</div>", unsafe_allow_html=True)

        for ttype, td in TOWER_TYPES.items():
            cost      = get_tower_cost(ttype)
            can_afford = ss.gold >= cost
            is_sel    = ss.selected_tower == ttype
            sel_s     = "border-color:#D4AF37;background:#1A1A2E;" if is_sel else ""
            aff_s     = "" if can_afford else "opacity:.4;"
            st.markdown(f"""
            <div class='tower-card' style='{sel_s}{aff_s}'>
                <div class='tc-name'>{td['emoji']} {td['name']}</div>
                <div class='tc-cost'>💰 {cost}g</div>
                <div class='tc-desc'>{td['desc']}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("✓ Selecionado" if is_sel else "Selecionar", key=f"sel_{ttype}",
                         disabled=not can_afford, use_container_width=True):
                ss.selected_tower = None if is_sel else ttype
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        if ss.selected_tower:
            td = TOWER_TYPES[ss.selected_tower]
            st.markdown(f"""
            <div style='background:#1A1A2E;border:1px solid #D4AF37;border-radius:6px;
                        padding:8px;margin-bottom:6px;text-align:center;'>
                <div style='font-size:.7rem;color:#D4AF37;font-family:Cinzel,serif;font-weight:700;margin-bottom:4px;'>
                    {td['emoji']} {td['name']} selecionado
                </div>
                <div style='font-size:.58rem;color:#7A7A8A;font-family:Cinzel,serif;'>
                    Clique em célula de grama no mapa<br>ou use o formulário abaixo.
                </div>
            </div>""", unsafe_allow_html=True)

            st.markdown("<div class='panel-title'>📍 Construir em</div>", unsafe_allow_html=True)
            ci1, ci2 = st.columns(2)
            with ci1:
                col_in = st.number_input("Col", 0, GRID_W-1, 3, key="pc", help="Coluna 0–13")
            with ci2:
                row_in = st.number_input("Lin", 0, GRID_H-1, 2, key="pr", help="Linha 0–9")

            kp          = f"{col_in},{row_in}"
            path_set_p  = set(map(tuple, path))
            is_path_c   = (col_in, row_in) in path_set_p
            is_occ      = kp in ss.towers
            cell_ok     = not is_path_c and not is_occ

            if is_path_c:
                st.markdown("<div style='font-size:.62rem;color:#E74C3C;font-family:Cinzel,serif;'>⛔ Célula no caminho!</div>", unsafe_allow_html=True)
            elif is_occ:
                st.markdown("<div style='font-size:.62rem;color:#E74C3C;font-family:Cinzel,serif;'>⛔ Já há uma torre!</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='font-size:.62rem;color:#27AE60;font-family:Cinzel,serif;'>✅ Posição livre ({col_in},{row_in})</div>", unsafe_allow_html=True)

            cost_now = get_tower_cost(ss.selected_tower)
            if st.button(f"🔨 Construir — {cost_now}g", use_container_width=True,
                         disabled=not cell_ok or ss.gold < cost_now):
                ss.towers[kp] = {
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

        if not ss.wave_active:
            if ss.wave < ss.max_waves:
                if st.button(f"⚔️ Onda {ss.wave+1}", use_container_width=True):
                    start_wave(); st.rerun()
            else:
                st.success("Vitória!")
        else:
            st.markdown(f"<div style='text-align:center;color:#E74C3C;font-family:Cinzel,serif;font-size:.75rem;'>⚔️ Onda {ss.wave} ativa!</div>", unsafe_allow_html=True)
            if st.button("🔄 Atualizar", use_container_width=True):
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        if ss.upgrades:
            st.markdown("<div class='panel-title'>✨ Melhorias</div>", unsafe_allow_html=True)
            for uid in ss.upgrades:
                u = next((x for x in ROGUELIKE_UPGRADES if x["id"]==uid), None)
                if u:
                    st.markdown(f"<div style='font-size:.62rem;color:#D4AF37;font-family:Cinzel,serif;margin-bottom:2px;'>{u['icon']} {u['name']}</div>", unsafe_allow_html=True)

        st.markdown("<div class='panel-title' style='margin-top:8px;'>📜 Log</div>", unsafe_allow_html=True)
        log_html = "".join(
            f"<div class='log-entry {'kill' if '💀' in e else 'gold' if '💰' in e else 'wave'}'>{e}</div>"
            for e in reversed(ss.combat_log[-20:])
        )
        st.markdown(f"<div class='log-box'>{log_html}</div>", unsafe_allow_html=True)

    if ss.wave_active and ss.screen == "game":
        time.sleep(0.15)
        st.rerun()

    if ss.screen != "game":
        st.rerun()


def screen_upgrade():
    inject_global_css()
    ss = st.session_state
    st.markdown(f"""
    <div style='text-align:center;padding:30px 0 20px;'>
        <div style='font-family:"Cinzel Decorative",cursive;font-size:2rem;color:#D4AF37;text-shadow:0 0 20px rgba(212,175,55,.5);'>✨ Escolha sua Melhoria ✨</div>
        <div style='font-family:Cinzel,serif;font-size:.85rem;color:#7A7A8A;margin-top:8px;'>
            Onda {ss.wave} superada! Ouro: {ss.gold}g · Score: {ss.score:,}
        </div>
    </div>""", unsafe_allow_html=True)
    cols = st.columns(len(ss.pending_upgrades))
    for i, (col, upg) in enumerate(zip(cols, ss.pending_upgrades)):
        with col:
            st.markdown(f"""
            <div class='upg-card'>
                <span class='upg-icon'>{upg['icon']}</span>
                <div class='upg-name'>{upg['name']}</div>
                <div class='upg-desc'>{upg['desc']}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("🗡️ Escolher", key=f"upg_{i}", use_container_width=True):
                ss.upgrades.append(upg["id"])
                ss.combat_log.append(f"✨ Melhoria: {upg['name']} ({upg['desc']})")
                ss.pending_upgrades = []
                ss.screen = "game"
                st.rerun()
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
        <div class='end-title' style='color:#C0392B;text-shadow:0 0 40px rgba(192,57,43,.7);'>💀 DERROTADO 💀</div>
        <div class='end-sub'>O castelo caiu. As trevas avançaram.</div>
        <div style='font-family:Cinzel,serif;font-size:1rem;color:#D4AF37;margin-bottom:8px;'>
            Onda alcançada: {ss.wave}/{ss.max_waves} · Mapa #{ss.map_seed}
        </div>
        <div style='font-family:Cinzel,serif;font-size:.9rem;color:#7A7A8A;'>
            Score: {ss.score:,} · Kills: {ss.kills} · Torres: {len(ss.towers)}
        </div>
    </div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("🔄 Tentar Novamente", use_container_width=True):
            reset_game(); st.rerun()
        if st.button("🏠 Menu Principal", use_container_width=True):
            reset_game(); st.session_state.screen = "menu"; st.rerun()


def screen_victory():
    inject_global_css()
    ss = st.session_state
    st.markdown(f"""
    <div class='end-screen'>
        <div class='end-title' style='color:#D4AF37;text-shadow:0 0 40px rgba(212,175,55,.8);'>🏆 VITÓRIA! 🏆</div>
        <div class='end-sub'>O castelo foi defendido. As trevas foram derrotadas!</div>
        <div style='font-family:Cinzel,serif;font-size:1.1rem;color:#D4AF37;margin-bottom:8px;'>
            Todas as {ss.max_waves} ondas superadas! · Mapa #{ss.map_seed}
        </div>
        <div style='font-family:Cinzel,serif;font-size:.9rem;color:#7A7A8A;'>
            Score: {ss.score:,} · Kills: {ss.kills} · Melhorias: {len(ss.upgrades)}/{len(ROGUELIKE_UPGRADES)}
        </div>
    </div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("🔄 Jogar Novamente", use_container_width=True):
            reset_game(); st.rerun()
        if st.button("🏠 Menu Principal", use_container_width=True):
            reset_game(); st.session_state.screen = "menu"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
{
    "menu":     screen_menu,
    "game":     screen_game,
    "upgrade":  screen_upgrade,
    "gameover": screen_gameover,
    "victory":  screen_victory,
}.get(st.session_state.screen, screen_menu)()
