"""
Tower Siege: Ruínas Eternas
100% self-contained — works on Streamlit Cloud with NO external files.
The arena component HTML is embedded as a Python string and rendered via
st.components.v1.html(), with game state injected as inline JSON.
Click-to-place uses the URL query-param bridge (same-origin navigation).
"""
import streamlit as st
import streamlit.components.v1 as st_components
import random, math, json, time

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
    "archer":   {"name":"Arqueiro","emoji":"🏹","cost":80,  "damage":45, "range":3.5,"fire_rate":6.0,"color":"#8BC34A","desc":"Ataque rápido, alcance médio","pixel_color":"#5D8A23","proj_speed":12,"proj_color":"#C8E6A0","proj_size":3},
    "mage":     {"name":"Mago",    "emoji":"🔮","cost":130, "damage":95, "range":2.5,"fire_rate":2.0,"color":"#9C27B0","desc":"Dano em área, lento",          "pixel_color":"#6A0080","proj_speed":8, "proj_color":"#CE93D8","proj_size":6},
    "ballista": {"name":"Balista", "emoji":"⚡","cost":200, "damage":190,"range":5.0,"fire_rate":1.0,"color":"#FF9800","desc":"Dano perfurante brutal",        "pixel_color":"#B36000","proj_speed":16,"proj_color":"#FFE0B2","proj_size":4},
    "frost":    {"name":"Gelo",    "emoji":"❄️","cost":110, "damage":20, "range":2.5,"fire_rate":4.0,"color":"#00BCD4","desc":"Lentifica inimigos -40%",       "pixel_color":"#007A8C","proj_speed":10,"proj_color":"#80DEEA","proj_size":5},
    "cannon":   {"name":"Canhão",  "emoji":"💣","cost":160, "damage":130,"range":2.5,"fire_rate":1.5,"color":"#795548","desc":"Explosão 3x3, lento",           "pixel_color":"#4E342E","proj_speed":7, "proj_color":"#A1887F","proj_size":7},
}

ENEMY_TYPES = {
    "goblin":   {"name":"Goblin",   "hp_base":140,  "speed":1.4,"reward":12, "color":"#4CAF50","size":"small"},
    "orc":      {"name":"Orc",      "hp_base":480,  "speed":0.8,"reward":25, "color":"#8D6E63","size":"medium"},
    "skeleton": {"name":"Esqueleto","hp_base":220,  "speed":1.2,"reward":18, "color":"#ECEFF1","size":"medium"},
    "troll":    {"name":"Troll",    "hp_base":1100, "speed":0.5,"reward":55, "color":"#33691E","size":"large"},
    "wraith":   {"name":"Espectro", "hp_base":320,  "speed":1.5,"reward":35, "color":"#7E57C2","size":"small"},
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

CELL_EMPTY = 0
CELL_PATH  = 1

# ══════════════════════════════════════════════════════════════════════════════
# MAP GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
def generate_grid(seed):
    rng = random.Random(seed)
    grid = [[CELL_EMPTY]*GRID_W for _ in range(GRID_H)]
    entry_row = rng.randint(2, GRID_H-3)
    exit_row  = rng.randint(2, GRID_H-3)
    path = []
    col, row = 0, entry_row
    grid[row][col] = CELL_PATH; path.append((col, row))
    while col < GRID_W - 1:
        if rng.random() < 0.45 and col < GRID_W - 2:
            d = rng.choice([-1, 1])
            for _ in range(rng.randint(1, 2)):
                nr = row + d
                if 1 <= nr <= GRID_H-2 and grid[nr][col] == CELL_EMPTY:
                    row = nr; grid[row][col] = CELL_PATH; path.append((col, row))
                else: break
        col += 1
        if grid[row][col] == CELL_EMPTY:
            grid[row][col] = CELL_PATH; path.append((col, row))
    while row != exit_row:
        d = 1 if exit_row > row else -1
        nr = row + d
        if 1 <= nr <= GRID_H-2 and grid[nr][col] == CELL_EMPTY:
            row = nr; grid[row][col] = CELL_PATH; path.append((col, row))
        else: break
    return grid, path

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "screen":"menu","wave":0,"gold":200,"lives":20,"score":0,
        "grid":None,"path":None,"enemies":[],"selected_tower":None,
        "upgrades":[],"combat_log":[],"wave_active":False,
        "enemies_spawned":0,"enemies_to_spawn":0,"pending_upgrades":[],
        "kills":0,"max_waves":15,"anim_events":[],"tick_counter":0,
        "map_seed":42,"click_col":-1,"click_row":-1,
        "projectiles":[],"tower_cooldowns":{},"tower_targets":{},"game_tick":0,
    }
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
    if st.session_state.grid is None:
        g, p = generate_grid(st.session_state.map_seed)
        st.session_state.grid = g; st.session_state.path = p

init_state()

def current_path(): return st.session_state.path
def current_grid(): return st.session_state.grid
def tower_count():
    g=current_grid()
    return sum(1 for r in range(GRID_H) for c in range(GRID_W) if isinstance(g[r][c],str))

# ══════════════════════════════════════════════════════════════════════════════
# GAME LOGIC
# ══════════════════════════════════════════════════════════════════════════════
def get_wave_enemies(wave):
    if wave<=3:   pool=["goblin"]*6+["skeleton"]*2
    elif wave<=6: pool=["goblin"]*5+["skeleton"]*4+["orc"]*2
    elif wave<=9: pool=["goblin"]*3+["skeleton"]*4+["orc"]*4+["wraith"]*2
    elif wave<=12:pool=["skeleton"]*3+["orc"]*5+["wraith"]*3+["troll"]*1
    else:         pool=["orc"]*5+["wraith"]*4+["troll"]*2+["dragon"]*1
    base_count = 8 + wave*2
    count = min(base_count, 30) if wave >= 13 else base_count
    return [random.choice(pool) for _ in range(count)]

def spawn_enemy(etype, wave):
    scale = 1 + (wave-1)*0.12
    base = ENEMY_TYPES[etype]; hp = int(base["hp_base"]*scale)
    gold_mult = 1.5 if "gold_rush" in st.session_state.upgrades else 1.0
    return {"id":random.randint(10000,99999),"type":etype,"name":base["name"],
            "hp":hp,"hp_max":hp,"speed":base["speed"],"slow":1.0,
            "reward":int(base["reward"]*gold_mult),"path_idx":0,"progress":0.0,
            "color":base["color"],"size":base["size"],"alive":True,"reached_end":False}

def dist(ax,ay,bx,by): return math.sqrt((ax-bx)**2+(ay-by)**2)

def apply_upgrades_to_tower(tower):
    t=tower.copy(); upg=st.session_state.upgrades
    if t["type"]=="archer":
        if "iron_arrows" in upg: t["damage"]=int(t["damage"]*1.25)
        if "double_shot" in upg: t["fire_rate"]*=2
    if t["type"]=="mage":
        if "mana_surge"      in upg: t["damage"]=int(t["damage"]*1.40)
        if "chain_lightning" in upg: t["extra_targets"]=3
    if t["type"]=="frost":  t["slow_amount"]=0.60 if "permafrost" in upg else 0.40
    if t["type"]=="ballista":
        if "explosive_tip" in upg: t["splash"]=True
    if t["type"]=="cannon":
        if "titan_barrel" in upg: t["damage"]=int(t["damage"]*1.80)
    return t

def get_tower_cost(ttype):
    base=TOWER_TYPES[ttype]["cost"]
    return int(base*0.80) if "arcane_nexus" in st.session_state.upgrades else base

def place_tower(col, row):
    ss = st.session_state
    if not ss.selected_tower: return False
    if col < 0 or col >= GRID_W or row < 0 or row >= GRID_H: return False
    grid = current_grid()
    if grid[row][col] != CELL_EMPTY: return False
    cost = get_tower_cost(ss.selected_tower)
    if ss.gold < cost: return False
    grid[row][col] = ss.selected_tower
    ss.gold -= cost
    ss.combat_log.append(f"🏰 {TOWER_TYPES[ss.selected_tower]['name']} erguida em ({col},{row})")
    ss.selected_tower = None
    ss.click_col = -1; ss.click_row = -1
    return True

def tick_game():
    ss=st.session_state
    if not ss.wave_active: return
    ss.game_tick+=1
    path=current_path(); path_len=len(path)-1; events=[]

    # Spawn
    if ss.enemies_spawned<ss.enemies_to_spawn:
        ss.tick_counter+=1
        if ss.tick_counter%4==0:
            ss.enemies.append(spawn_enemy(ss._spawn_queue[ss.enemies_spawned],ss.wave))
            ss.enemies_spawned+=1

    # Move enemies
    alive=[]
    for e in ss.enemies:
        if not e["alive"]: continue
        if e["reached_end"]: ss.lives=max(0,ss.lives-1); continue
        e["progress"]+=e["speed"]*e["slow"]*0.09
        while e["progress"]>=1.0 and e["path_idx"]<path_len-1:
            e["progress"]-=1.0; e["path_idx"]+=1
        if e["path_idx"]>=path_len-1 and e["progress"]>=1.0:
            e["reached_end"]=True; continue
        e["slow"]=1.0; alive.append(e)
    ss.enemies=alive

    # Towers fire projectiles
    grid=current_grid()
    _tw=[(tc,tr,{**TOWER_TYPES[grid[tr][tc]],"type":grid[tr][tc]})
         for tr in range(GRID_H) for tc in range(GRID_W) if isinstance(grid[tr][tc],str)]
    for tc,tr,_td in _tw:
        t=apply_upgrades_to_tower(_td)
        tkey=f"{tc},{tr}"
        cd_ticks=(1.0/t["fire_rate"])*24
        if (ss.game_tick-ss.tower_cooldowns.get(tkey,-9999))<cd_ticks: continue
        # Target locking
        locked_id=ss.tower_targets.get(tkey)
        target=None
        if locked_id is not None:
            tgt=next((e for e in ss.enemies if e["id"]==locked_id and e["alive"]),None)
            if tgt and dist(tc,tr,*path[tgt["path_idx"]])<=t["range"]: target=tgt
            else: ss.tower_targets.pop(tkey,None)
        if target is None:
            candidates=[e for e in ss.enemies if e["alive"] and dist(tc,tr,*path[e["path_idx"]])<=t["range"]]
            if not candidates: continue
            candidates.sort(key=lambda e:e["path_idx"]+e["progress"],reverse=True)
            target=candidates[0]; ss.tower_targets[tkey]=target["id"]
        pi=min(target["path_idx"],len(path)-2)
        prog=max(0.0,min(1.0,target["progress"]))
        c1,r1=path[pi]; c2,r2=path[min(pi+1,len(path)-1)]
        ex=c1+(c2-c1)*prog; ey=r1+(r2-r1)*prog
        proj={"id":random.randint(10000,99999),"tower_type":t["type"],
              "x":float(tc),"y":float(tr),"tx":ex,"ty":ey,
              "target_id":target["id"],"speed":t.get("proj_speed",6),
              "damage":t["damage"],"color":t.get("proj_color","#FFF"),
              "size":t.get("proj_size",4),"effects":[],"alive":True}
        if t["type"]=="frost": proj["effects"].append({"type":"slow","amount":t.get("slow_amount",0.40)})
        if t["type"] in ("cannon","mage"): proj["effects"].append({"type":"splash","radius":1.5,"ratio":0.6})
        ss.projectiles.append(proj)
        ss.tower_cooldowns[tkey]=ss.game_tick

    # Move projectiles + hit
    alive_proj=[]
    for p in ss.projectiles:
        if not p["alive"]: continue
        tgt=next((e for e in ss.enemies if e["id"]==p["target_id"] and e["alive"]),None)
        if tgt:
            pi=min(tgt["path_idx"],len(path)-2); prog=max(0.0,min(1.0,tgt["progress"]))
            c1,r1=path[pi]; c2,r2=path[min(pi+1,len(path)-1)]
            p["tx"]=c1+(c2-c1)*prog; p["ty"]=r1+(r2-r1)*prog
        dx=p["tx"]-p["x"]; dy=p["ty"]-p["y"]
        d=math.sqrt(dx*dx+dy*dy); step=p["speed"]*0.10
        if d<=step or d<0.3:
            if tgt and tgt["alive"]:
                dmg=p["damage"]
                for eff in p["effects"]:
                    if eff["type"]=="slow": tgt["slow"]=1.0-eff["amount"]
                    if eff["type"]=="splash":
                        for nb in ss.enemies:
                            if nb["id"]!=tgt["id"] and nb["alive"]:
                                nc,nr=path[nb["path_idx"]]
                                if dist(p["tx"],p["ty"],nc,nr)<=eff["radius"]:
                                    nb["hp"]-=int(dmg*eff["ratio"])
                                    if nb["hp"]<=0:
                                        nb["alive"]=False; ss.gold+=nb["reward"]; ss.score+=nb["reward"]*10; ss.kills+=1
                tgt["hp"]-=dmg
                events.append({"type":"hit","tower_type":p["tower_type"],"ex":p["tx"],"ey":p["ty"],"dmg":dmg})
                if tgt["hp"]<=0:
                    tgt["alive"]=False; ss.gold+=tgt["reward"]; ss.score+=tgt["reward"]*10; ss.kills+=1
                    events.append({"type":"kill","x":p["tx"],"y":p["ty"]})
            p["alive"]=False
        else:
            p["x"]+=dx/d*step; p["y"]+=dy/d*step; alive_proj.append(p)
    ss.projectiles=alive_proj
    ss.enemies=[e for e in ss.enemies if e["alive"]]

    # Wave end
    if ss.enemies_spawned>=ss.enemies_to_spawn and len(ss.enemies)==0 and len(ss.projectiles)==0:
        ss.wave_active=False; bonus=40+ss.wave*15; ss.gold+=bonus; ss.score+=bonus*5
        events.append({"type":"wave_clear"})
        ss.combat_log.append(f"🏆 Onda {ss.wave} completa! +{bonus}g de bônus")
        if ss.wave>=ss.max_waves: ss.screen="victory"
        else:
            avail=[u for u in ROGUELIKE_UPGRADES if u["id"] not in ss.upgrades]
            ss.pending_upgrades=random.sample(avail,min(3,len(avail)))
            if ss.pending_upgrades: ss.screen="upgrade"
    if ss.lives<=0: ss.screen="gameover"
    ss.anim_events=events

def start_wave():
    ss=st.session_state; ss.wave+=1
    queue=get_wave_enemies(ss.wave)
    ss._spawn_queue=queue; ss.enemies_to_spawn=len(queue)
    ss.enemies_spawned=0; ss.enemies=[]; ss.wave_active=True; ss.tick_counter=0
    ss.combat_log.append(f"⚔️ Onda {ss.wave} iniciada! {len(queue)} inimigos se aproximam...")

def reset_game():
    keys=["wave","gold","lives","score","grid","path","enemies","selected_tower",
          "upgrades","combat_log","wave_active","enemies_spawned","enemies_to_spawn",
          "pending_upgrades","kills","anim_events","tick_counter",
          "click_col","click_row","_spawn_queue",
          "projectiles","tower_cooldowns","tower_targets","game_tick","_last_click_ts"]
    for k in keys: st.session_state.pop(k,None)
    st.session_state.map_seed=random.randint(1,99999)
    init_state(); st.session_state.screen="game"

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
    .block-container{padding:.4rem .6rem!important;max-width:100%!important;}
    .stButton>button{background:linear-gradient(135deg,#1A1A2E,#2A1A0E)!important;color:var(--gold)!important;
        border:1px solid var(--gold)!important;border-radius:4px!important;font-family:'Cinzel',serif!important;
        font-weight:700!important;font-size:.72rem!important;padding:.28rem .5rem!important;
        transition:all .2s!important;text-transform:uppercase!important;letter-spacing:.04em!important;}
    .stButton>button:hover{background:linear-gradient(135deg,#2A2A4E,#3A2A1E)!important;
        border-color:var(--gold-light)!important;box-shadow:0 0 12px rgba(212,175,55,.4)!important;}
    .stButton>button:disabled{opacity:.35!important;cursor:not-allowed!important;}
    [data-testid="column"]{padding:0 3px!important;}
    hr{border-color:var(--border)!important;margin:.3rem 0!important;}
    [data-testid="stNumberInput"] input{background:#0A0A1A!important;color:var(--gold-light)!important;
        border:1px solid var(--border)!important;font-family:'Cinzel',serif!important;font-size:.75rem!important;}
    .hud-stat{display:flex;align-items:center;gap:5px;font-family:'Cinzel',serif;font-size:.78rem;font-weight:700;white-space:nowrap;}
    .hud-stat .val{color:var(--gold-light);font-size:.9rem;}
    .hud-stat.lives .val{color:#E74C3C;}
    .hud-stat.score .val{color:#00E5FF;}
    .panel-title{font-family:'Cinzel Decorative',cursive;font-size:.65rem;color:var(--gold);
        letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;
        border-bottom:1px solid var(--border);padding-bottom:3px;}
    .tower-card{background:var(--bg-card);border:1px solid var(--border);border-radius:4px;padding:5px 7px;margin-bottom:3px;}
    .tower-card.sel{border-color:var(--gold);background:#16162A;}
    .tower-card .tc-name{font-size:.72rem;font-weight:700;color:var(--text);}
    .tower-card .tc-cost{font-size:.66rem;color:var(--gold);}
    .tower-card .tc-desc{font-size:.58rem;color:var(--text-dim);margin-top:1px;}
    .build-panel{background:#12121A;border:1px solid var(--gold);border-radius:6px;padding:8px;margin-bottom:6px;}
    .build-panel .bp-title{font-family:'Cinzel',serif;font-size:.68rem;font-weight:700;color:var(--gold);text-align:center;margin-bottom:4px;}
    .build-panel .bp-hint{font-size:.56rem;color:var(--text-dim);text-align:center;font-family:'Cinzel',serif;}
    .ok-cell{font-size:.6rem;color:#27AE60;font-family:'Cinzel',serif;}
    .bad-cell{font-size:.6rem;color:#E74C3C;font-family:'Cinzel',serif;}
    .log-box{background:#050508;border:1px solid var(--border);border-radius:4px;padding:5px 7px;
        height:120px;overflow-y:auto;font-size:.58rem;font-family:'Cinzel',serif;color:var(--text-dim);}
    .log-entry{margin-bottom:2px;line-height:1.3;}
    .log-entry.kill{color:#E74C3C;}
    .log-entry.gold{color:var(--gold);}
    .upg-card{background:var(--bg-card);border:2px solid var(--border);border-radius:8px;padding:18px;text-align:center;}
    .upg-icon{font-size:2.2rem;display:block;margin-bottom:6px;}
    .upg-name{font-family:'Cinzel Decorative',cursive;font-size:.85rem;color:var(--gold);}
    .upg-desc{font-size:.7rem;color:var(--text-dim);margin-top:5px;}
    .end-screen{text-align:center;padding:50px 20px;}
    .end-title{font-family:'Cinzel Decorative',cursive;font-size:3.5rem;font-weight:900;margin-bottom:14px;}
    .end-sub{font-family:'Cinzel',serif;font-size:1rem;color:var(--text-dim);margin-bottom:28px;}
    .arena-scroll{width:100%;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;}
    @media(max-width:600px){.hud-stat{font-size:.65rem;}.hud-stat .val{font-size:.75rem;}}
    </style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ARENA — self-contained HTML injected with game state as inline JSON
# No external files. Click → URL ?_pc=C&_pr=R → Streamlit query_params.
# Lerped 60fps animation loop for enemies and projectiles.
# ══════════════════════════════════════════════════════════════════════════════
def build_arena_html(path):
    ss  = st.session_state
    C, R = CELL, RULER
    COLS, ROWS = GRID_W, GRID_H
    CW = R + COLS*C; CH = R + ROWS*C; OX = R; OY = R

    grid = current_grid()
    towers_js = json.dumps({
        f"{c},{r}": {"type": grid[r][c]}
        for r in range(GRID_H) for c in range(GRID_W) if isinstance(grid[r][c], str)
    })
    elist = []
    for e in ss.enemies:
        pi = min(e["path_idx"], len(path)-2)
        t  = max(0.0, min(1.0, e["progress"]))
        c1,r1 = path[pi]; c2,r2 = path[min(pi+1, len(path)-1)]
        elist.append({"id":e["id"], "x":c1+(c2-c1)*t, "y":r1+(r2-r1)*t,
                      "hp_pct":max(0, e["hp"]/e["hp_max"]),
                      "color":e["color"], "size":e["size"]})
    plist = [{"id":p["id"],"x":p["x"],"y":p["y"],
              "color":p["color"],"size":p["size"]}
             for p in ss.projectiles if p["alive"]]

    enemies_js  = json.dumps(elist)
    proj_js     = json.dumps(plist)
    path_js     = json.dumps(path)
    events_js   = json.dumps(ss.anim_events)
    selected    = ss.selected_tower or ""
    tcolors_js  = json.dumps({"archer":"#5D8A23","mage":"#6A0080",
                               "ballista":"#B36000","frost":"#007A8C","cannon":"#4E342E"})

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#0A0A0F;overflow:hidden;font-family:monospace;
          user-select:none;touch-action:none;width:{CW}px;height:{CH}px;}}
#w{{position:relative;width:{CW}px;height:{CH}px;}}
canvas{{display:block;position:absolute;top:0;left:0;image-rendering:pixelated;}}
#ov{{position:absolute;pointer-events:none;top:{OY}px;left:{OX}px;
    width:{COLS*C}px;height:{ROWS*C}px;}}
.ah{{position:absolute;border-radius:50%;pointer-events:none;animation:ha .4s ease-out forwards;}}
@keyframes ha{{0%{{transform:scale(.2);opacity:1;}}100%{{transform:scale(1.8);opacity:0;}}}}
.ak{{position:absolute;pointer-events:none;font-size:16px;animation:ka .8s ease-out forwards;}}
@keyframes ka{{0%{{transform:translateY(0);opacity:1;}}100%{{transform:translateY(-40px);opacity:0;}}}}
.dn{{position:absolute;color:#FF4444;font-size:13px;font-weight:bold;pointer-events:none;
    text-shadow:0 0 4px #000;animation:da .6s ease-out forwards;}}
@keyframes da{{0%{{transform:translateY(0) scale(1);opacity:1;}}100%{{transform:translateY(-30px) scale(.8);opacity:0;}}}}
#tip{{position:absolute;background:rgba(10,10,20,.94);border:1px solid #D4AF37;border-radius:4px;
    padding:4px 8px;font-size:11px;color:#E8DCC8;pointer-events:none;display:none;z-index:200;white-space:nowrap;}}
</style></head><body>
<div id="w">
  <canvas id="c" width="{CW}" height="{CH}"></canvas>
  <div id="ov"></div>
  <div id="tip"></div>
</div>
<script>
// ── Static state (injected from Python) ──────────────────────────────────
var COLS={COLS},ROWS={ROWS},C={C},R={R},CW={CW},CH={CH},OX={OX},OY={OY};
var PATH={path_js};
var PS=new Set(PATH.map(function(p){{return p[0]+','+p[1];}}));
var TW={towers_js};
var TC={tcolors_js};
var SEL="{selected}";

// ── Lerped display state ──────────────────────────────────────────────────
var newEnemies={enemies_js};
var newProj={proj_js};
var EV={events_js};

var dispEnemies=[];
var dispProj=[];
var LERP=0.18;

// Initialise / merge enemies
(function(){{
  var newEN=newEnemies;
  newEN.forEach(function(ne){{
    dispEnemies.push({{id:ne.id,x:ne.x,y:ne.y,tx:ne.x,ty:ne.y,
                       hp_pct:ne.hp_pct,color:ne.color,size:ne.size}});
  }});
  var newPR=newProj;
  newPR.forEach(function(np){{
    dispProj.push({{id:np.id,x:np.x,y:np.y,tx:np.x,ty:np.y,
                    color:np.color,size:np.size}});
  }});
}})();

function lerpTo(c,t,f){{return c+(t-c)*f;}}

// ── Canvas ────────────────────────────────────────────────────────────────
var cv=document.getElementById('c'),ctx=cv.getContext('2d');
var ov=document.getElementById('ov'),tip=document.getElementById('tip');
var hC=-1,hR=-1;

function lt(h,a){{
  var n=parseInt(h.slice(1),16);
  return'#'+[((n>>16)&255)+a,((n>>8)&255)+a,(n&255)+a]
    .map(function(v){{return Math.min(255,Math.max(0,v)).toString(16).padStart(2,'0');}}).join('');
}}
function rn(a,b){{return Math.floor(Math.random()*(b-a))+a;}}

function drawRulers(){{
  ctx.fillStyle='#12121A';ctx.fillRect(0,0,CW,R);ctx.fillRect(0,0,R,CH);
  ctx.fillStyle='#1A1A2E';ctx.fillRect(0,0,R,R);
  ctx.fillStyle='#D4AF37';ctx.font='bold 8px monospace';
  ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('C\\\\R',R/2,R/2);
  for(var c=0;c<COLS;c++){{
    ctx.fillStyle=c%2?'#141420':'#1A1A2E';ctx.fillRect(OX+c*C,0,C,R);
    ctx.fillStyle='#D4AF37';ctx.font='bold 10px monospace';
    ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(c,OX+c*C+C/2,R/2);
  }}
  for(var r=0;r<ROWS;r++){{
    ctx.fillStyle=r%2?'#141420':'#1A1A2E';ctx.fillRect(0,OY+r*C,R,C);
    ctx.fillStyle='#D4AF37';ctx.font='bold 10px monospace';
    ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(r,R/2,OY+r*C+C/2);
  }}
  ctx.strokeStyle='#2A2A4A';ctx.lineWidth=1;ctx.strokeRect(.5,.5,CW-1,CH-1);
  ctx.beginPath();ctx.moveTo(R,0);ctx.lineTo(R,CH);ctx.moveTo(0,R);ctx.lineTo(CW,R);ctx.stroke();
}}

function drawTerrain(){{
  for(var r=0;r<ROWS;r++)for(var c=0;c<COLS;c++){{
    var k=c+','+r,ip=PS.has(k),x=OX+c*C,y=OY+r*C;
    if(ip){{
      ctx.fillStyle='#C8A96E';ctx.fillRect(x,y,C,C);
      ctx.fillStyle='rgba(100,70,30,.3)';
      for(var px=2;px<C;px+=8)for(var py=2;py<C;py+=8)ctx.fillRect(x+px,y+py,2,2);
      ctx.strokeStyle='rgba(160,120,50,.4)';ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,C-1,C-1);
    }}else{{
      var dk=(c+r)%2;ctx.fillStyle=dk?'#2D5016':'#345C1A';ctx.fillRect(x,y,C,C);
      ctx.fillStyle=dk?'#3A6820':'#416824';
      ctx.fillRect(x+2,y+4,3,2);ctx.fillRect(x+C-8,y+C-7,3,2);ctx.fillRect(x+C/2-2,y+C/2,3,2);
      ctx.strokeStyle='rgba(0,0,0,.15)';ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,C-1,C-1);
    }}
  }}
  ctx.fillStyle='rgba(100,70,20,.45)';
  for(var i=1;i<PATH.length;i++){{
    var c1=PATH[i-1][0],r1=PATH[i-1][1],c2=PATH[i][0],r2=PATH[i][1];
    var cx=OX+(c1+c2)/2*C+C/2,cy=OY+(r1+r2)/2*C+C/2,ag=Math.atan2(r2-r1,c2-c1);
    ctx.save();ctx.translate(cx,cy);ctx.rotate(ag);
    ctx.beginPath();ctx.moveTo(7,0);ctx.lineTo(-5,-5);ctx.lineTo(-5,5);ctx.closePath();ctx.fill();ctx.restore();
  }}
  var sc=PATH[0][0],sr=PATH[0][1];
  ctx.fillStyle='rgba(0,200,0,.35)';ctx.fillRect(OX+sc*C,OY+sr*C,C,C);
  ctx.fillStyle='#00FF88';ctx.font='bold 10px monospace';
  ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('▶START',OX+sc*C+C/2,OY+sr*C+C/2);
  var ec=PATH[PATH.length-1][0],er=PATH[PATH.length-1][1];
  ctx.fillStyle='rgba(200,0,0,.35)';ctx.fillRect(OX+ec*C,OY+er*C,C,C);
  ctx.fillStyle='#FF4444';ctx.fillText('END✖',OX+ec*C+C/2,OY+er*C+C/2);
}}

function drawHover(){{
  if(!SEL||hC<0)return;
  var k=hC+','+hR,v=!PS.has(k)&&!TW[k];
  ctx.fillStyle=v?'rgba(212,175,55,.3)':'rgba(200,50,50,.3)';ctx.fillRect(OX+hC*C,OY+hR*C,C,C);
  ctx.strokeStyle=v?'#D4AF37':'#E74C3C';ctx.lineWidth=2;ctx.strokeRect(OX+hC*C+1,OY+hR*C+1,C-2,C-2);
  ctx.fillStyle=v?'#FFD700':'#FF8888';ctx.font='bold 9px monospace';
  ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('('+hC+','+hR+')',OX+hC*C+C/2,OY+hR*C+C/2);
}}

function drawTower(cx,cy,tp){{
  var col=TC[tp]||'#888';
  ctx.fillStyle='#5A4A3A';ctx.fillRect(cx-10,cy+4,20,8);
  ctx.fillStyle='#6B5B4B';ctx.fillRect(cx-7,cy-12,14,16);
  ctx.fillStyle='#7A6A5A';for(var i=0;i<3;i++)ctx.fillRect(cx-8+i*6,cy-17,4,5);
  ctx.fillStyle=col;ctx.fillRect(cx-4,cy-8,8,10);
  ctx.fillStyle='#0A0A1A';ctx.fillRect(cx-2,cy-6,4,5);
  var ic={archer:'🏹',mage:'🔮',ballista:'⚡',frost:'❄',cannon:'💣'};
  ctx.font='13px serif';ctx.textAlign='center';ctx.textBaseline='alphabetic';ctx.fillText(ic[tp]||'🗼',cx,cy-20);
}}

function drawEnemy(e){{
  var px=OX+e.x*C+C/2,py=OY+e.y*C+C/2;
  var sz=e.size==='boss'?22:e.size==='large'?18:e.size==='medium'?14:11;
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

function drawProjectile(p){{
  var px=OX+p.x*C+C/2,py=OY+p.y*C+C/2,sz=p.size||4;
  ctx.save();
  ctx.globalAlpha=0.4;ctx.fillStyle=p.color;ctx.beginPath();ctx.arc(px,py,sz+3,0,Math.PI*2);ctx.fill();
  ctx.globalAlpha=1;ctx.fillStyle='#FFF';ctx.beginPath();ctx.arc(px,py,sz*.6,0,Math.PI*2);ctx.fill();
  ctx.fillStyle=p.color;ctx.beginPath();ctx.arc(px,py,sz,0,Math.PI*2);ctx.fill();
  ctx.restore();
}}

function render(){{
  ctx.clearRect(0,0,CW,CH);
  drawTerrain();
  for(var k in TW){{var p=k.split(',').map(Number);drawTower(OX+p[0]*C+C/2,OY+p[1]*C+C/2,TW[k].type);}}
  dispEnemies.forEach(function(e){{e.x=lerpTo(e.x,e.tx,LERP);e.y=lerpTo(e.y,e.ty,LERP);drawEnemy(e);}});
  dispProj.forEach(function(p){{p.x=lerpTo(p.x,p.tx,LERP);p.y=lerpTo(p.y,p.ty,LERP);drawProjectile(p);}});
  drawHover();
  drawRulers();
}}

// ── 60fps loop ────────────────────────────────────────────────────────────
function animLoop(){{render();requestAnimationFrame(animLoop);}}
requestAnimationFrame(animLoop);

// ── FX ────────────────────────────────────────────────────────────────────
EV.forEach(function(ev){{
  if(ev.type==='hit'){{
    var px=ev.ex*C+C/2,py=ev.ey*C+C/2,el=document.createElement('div');el.className='ah';
    var cl={{archer:'#8BC34A',mage:'#9C27B0',ballista:'#FF9800',frost:'#00BCD4',cannon:'#795548'}};
    el.style.cssText='width:18px;height:18px;background:'+(cl[ev.tower_type]||'#FFF')+
      ';left:'+(px-9)+'px;top:'+(py-9)+'px;opacity:.8;';
    ov.appendChild(el);setTimeout(function(){{el.remove();}},400);
    var dn=document.createElement('div');dn.className='dn';
    dn.textContent='-'+ev.dmg;
    dn.style.cssText='left:'+(px+rn(-10,10))+'px;top:'+py+'px;';
    ov.appendChild(dn);setTimeout(function(){{dn.remove();}},600);
  }} else if(ev.type==='kill'){{
    var px2=ev.x*C+C/2,py2=ev.y*C+C/2,el2=document.createElement('div');el2.className='ak';
    el2.textContent='💀';el2.style.cssText='left:'+(px2-10)+'px;top:'+(py2-20)+'px;';
    ov.appendChild(el2);setTimeout(function(){{el2.remove();}},800);
  }} else if(ev.type==='wave_clear'){{
    cv.style.transition='opacity .15s';cv.style.opacity='.6';
    setTimeout(function(){{cv.style.opacity='1';}},300);
  }}
}});

// ── Tooltip + hover ───────────────────────────────────────────────────────
function getCell(ev){{
  var rc=cv.getBoundingClientRect();
  var mx=(ev.clientX-rc.left)*(CW/rc.width),my=(ev.clientY-rc.top)*(CH/rc.height);
  return[Math.floor((mx-OX)/C),Math.floor((my-OY)/C)];
}}
cv.addEventListener('mousemove',function(ev){{
  var cr=getCell(ev),c=cr[0],r=cr[1];
  if(c>=0&&c<COLS&&r>=0&&r<ROWS){{
    hC=c;hR=r;var k=c+','+r,tx='Col '+c+' · Linha '+r;
    if(TW[k])tx+=' — '+TW[k].type;
    else if(PS.has(k))tx+=' — Caminho';
    else if(SEL)tx+=' — Clique para construir';
    tip.textContent=tx;tip.style.display='block';
    var rc2=cv.getBoundingClientRect();
    tip.style.left=(ev.clientX-rc2.left+12)+'px';tip.style.top=(ev.clientY-rc2.top+12)+'px';
  }}else{{hC=-1;hR=-1;tip.style.display='none';}}
}});
cv.addEventListener('mouseleave',function(){{hC=-1;hR=-1;tip.style.display='none';}});

// ── Click → ?_pc=C&_pr=R (same-origin, picked up by Streamlit) ───────────
function sendPlace(c,r){{
  var url=new URL(window.parent.location.href);
  url.searchParams.set('_pc',c);url.searchParams.set('_pr',r);
  window.parent.location.href=url.toString();
}}
cv.addEventListener('click',function(ev){{
  if(!SEL)return;
  var cr=getCell(ev),c=cr[0],r=cr[1];
  if(c<0||c>=COLS||r<0||r>=ROWS)return;
  var k=c+','+r;if(PS.has(k)||TW[k])return;
  sendPlace(c,r);
}});
cv.addEventListener('touchstart',function(ev){{
  ev.preventDefault();var cr=getCell(ev.touches[0]),c=cr[0],r=cr[1];
  if(c>=0&&c<COLS&&r>=0&&r<ROWS){{hC=c;hR=r;}}
}},{{passive:false}});
cv.addEventListener('touchend',function(ev){{
  ev.preventDefault();
  if(hC>=0&&SEL){{var k=hC+','+hR;if(!PS.has(k)&&!TW[k])sendPlace(hC,hR);}}
}},{{passive:false}});

cv.style.cursor=SEL?'crosshair':'default';
</script></body></html>"""

# ══════════════════════════════════════════════════════════════════════════════
# SCREENS
# ══════════════════════════════════════════════════════════════════════════════
def screen_menu():
    inject_global_css()
    st.markdown("""
    <div style='text-align:center;padding:50px 20px 24px;'>
        <div style='font-family:"Cinzel Decorative",cursive;font-size:2.8rem;font-weight:900;color:#D4AF37;
                    text-shadow:0 0 28px rgba(212,175,55,.6);'>⚔️ Tower Siege ⚔️</div>
        <div style='font-family:"Cinzel Decorative",cursive;font-size:.9rem;color:#8B6914;letter-spacing:.4em;margin-top:4px;'>RUÍNAS ETERNAS</div>
        <div style='margin:20px auto;max-width:460px;font-size:.82rem;color:#7A7A8A;font-family:Cinzel,serif;line-height:1.8;'>
            Erga suas torres nas ruínas de um castelo maldito.<br>
            Defenda o portão sagrado contra hordas de criaturas das trevas.<br>
            <em style='color:#D4AF37'>Permadeath. Sem segunda chance. Só a estratégia salva.</em>
        </div>
    </div>""", unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,1])
    with c2:
        if st.button("⚔️  INICIAR CAMPANHA",use_container_width=True):
            reset_game();st.rerun()
    st.markdown("<div style='display:flex;justify-content:center;gap:32px;margin-top:36px;flex-wrap:wrap;'>",unsafe_allow_html=True)
    for ttype,td in TOWER_TYPES.items():
        st.markdown(f"""
        <div style='background:#12121A;border:1px solid #2A2A3E;border-radius:8px;padding:14px;
                    min-width:130px;text-align:center;font-family:Cinzel,serif;'>
            <div style='font-size:1.8rem;'>{td['emoji']}</div>
            <div style='color:#D4AF37;font-size:.75rem;font-weight:700;margin:3px 0;'>{td['name']}</div>
            <div style='color:#7A7A8A;font-size:.6rem;'>{td['desc']}</div>
            <div style='color:#D4AF37;font-size:.65rem;margin-top:3px;'>💰 {td['cost']}g</div>
        </div>""",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)


def screen_game():
    inject_global_css()
    ss   = st.session_state
    path = current_path()

    # ── Click-to-place via URL params ─────────────────────────────────────────
    pc_param = st.query_params.get("_pc","")
    pr_param = st.query_params.get("_pr","")
    if pc_param and pr_param and ss.selected_tower:
        try:
            pc,pr = int(pc_param),int(pr_param)
            if place_tower(pc,pr):
                st.query_params.pop("_pc",None); st.query_params.pop("_pr",None)
                st.rerun()
        except Exception:
            pass
        st.query_params.pop("_pc",None); st.query_params.pop("_pr",None)

    # ── Tick ──────────────────────────────────────────────────────────────────
    if ss.wave_active:
        for _ in range(6):
            tick_game()
            if not ss.wave_active: break

    # ── HUD ───────────────────────────────────────────────────────────────────
    h1,h2,h3,h4,h5,h6=st.columns(6)
    with h1: st.markdown(f"<div class='hud-stat'>⚔️ Onda <span class='val'>{ss.wave}/{ss.max_waves}</span></div>",unsafe_allow_html=True)
    with h2: st.markdown(f"<div class='hud-stat lives'>❤️ Vidas <span class='val'>{ss.lives}</span></div>",unsafe_allow_html=True)
    with h3: st.markdown(f"<div class='hud-stat'>💰 <span class='val'>{ss.gold}g</span></div>",unsafe_allow_html=True)
    with h4: st.markdown(f"<div class='hud-stat score'>🏆 <span class='val'>{ss.score:,}</span></div>",unsafe_allow_html=True)
    with h5: st.markdown(f"<div class='hud-stat'>💀 <span class='val'>{ss.kills}</span></div>",unsafe_allow_html=True)
    with h6:
        rem=(ss.enemies_to_spawn-ss.enemies_spawned+len(ss.enemies)) if ss.wave_active else 0
        st.markdown(f"<div class='hud-stat'>👾 <span class='val'>{rem}</span></div>",unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)

    arena_col, towers_col, ctrl_col = st.columns([5, 2, 2])

    # ── ARENA ─────────────────────────────────────────────────────────────────
    with arena_col:
        ARENA_H = RULER + GRID_H*CELL + 4
        st.markdown("<div class='arena-scroll'>",unsafe_allow_html=True)
        st_components.html(build_arena_html(path), height=ARENA_H, scrolling=False)
        st.markdown("</div>",unsafe_allow_html=True)

    # ── TOWERS COLUMN ─────────────────────────────────────────────────────────
    with towers_col:
        st.markdown(f"<div style='font-size:.55rem;color:#4A4A5A;font-family:Cinzel,serif;margin-bottom:3px;'>🗺️ #{ss.map_seed}</div>",unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🏰 Torres</div>",unsafe_allow_html=True)
        for ttype,td in TOWER_TYPES.items():
            cost=get_tower_cost(ttype)
            can_afford=ss.gold>=cost
            is_sel=ss.selected_tower==ttype
            sel_cls="sel" if is_sel else ""
            dim="opacity:.35;" if not can_afford else ""
            st.markdown(f"""
            <div class='tower-card {sel_cls}' style='{dim}'>
                <div class='tc-name'>{td['emoji']} {td['name']}</div>
                <div class='tc-cost'>💰 {cost}g</div>
                <div class='tc-desc'>{td['desc']}</div>
            </div>""",unsafe_allow_html=True)
            lbl="✓ Ativo" if is_sel else "Selecionar"
            if st.button(lbl, key=f"sel_{ttype}", disabled=not can_afford, use_container_width=True):
                ss.selected_tower=None if is_sel else ttype
                ss.click_col=-1; ss.click_row=-1
                st.rerun()
        if ss.upgrades:
            st.markdown("<hr>",unsafe_allow_html=True)
            st.markdown("<div class='panel-title'>✨ Melhorias</div>",unsafe_allow_html=True)
            for uid in ss.upgrades:
                u=next((x for x in ROGUELIKE_UPGRADES if x["id"]==uid),None)
                if u:
                    st.markdown(f"<div style='font-size:.58rem;color:#D4AF37;font-family:Cinzel,serif;margin-bottom:1px;'>{u['icon']} {u['name']}</div>",unsafe_allow_html=True)

    # ── CONTROLS COLUMN ───────────────────────────────────────────────────────
    with ctrl_col:
        if ss.selected_tower:
            td=TOWER_TYPES[ss.selected_tower]
            default_c=ss.click_col if ss.click_col>=0 else 0
            default_r=ss.click_row if ss.click_row>=0 else 0
            st.markdown(f"""
            <div class='build-panel'>
                <div class='bp-title'>{td['emoji']} {td['name']}</div>
                <div class='bp-hint'>Clique no mapa ou informe abaixo</div>
            </div>""",unsafe_allow_html=True)
            st.markdown("<div class='panel-title'>📍 Posição</div>",unsafe_allow_html=True)
            ci1,ci2=st.columns(2)
            with ci1:
                col_in=st.number_input("Col",0,GRID_W-1,default_c,key="pc",help="Coluna 0–13")
            with ci2:
                row_in=st.number_input("Lin",0,GRID_H-1,default_r,key="pr",help="Linha 0–9")
            g_cell=current_grid()[row_in][col_in]
            is_path_c=g_cell==CELL_PATH
            is_occ=isinstance(g_cell,str)
            cell_ok=g_cell==CELL_EMPTY
            cost_now=get_tower_cost(ss.selected_tower)
            if is_path_c:
                st.markdown("<div class='bad-cell'>⛔ Célula no caminho!</div>",unsafe_allow_html=True)
            elif is_occ:
                st.markdown("<div class='bad-cell'>⛔ Posição ocupada!</div>",unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='ok-cell'>✅ Livre ({col_in},{row_in})</div>",unsafe_allow_html=True)
            if st.button(f"🔨 Construir — {cost_now}g", use_container_width=True,
                         disabled=not cell_ok or ss.gold < cost_now):
                if place_tower(col_in, row_in): st.rerun()
            if st.button("❌ Cancelar",use_container_width=True):
                ss.selected_tower=None; ss.click_col=-1; ss.click_row=-1; st.rerun()

        st.markdown("<hr>",unsafe_allow_html=True)
        if not ss.wave_active:
            if ss.wave<ss.max_waves:
                if st.button(f"⚔️ Onda {ss.wave+1}",use_container_width=True):
                    start_wave();st.rerun()
            else:
                st.success("Vitória! 🏆")
        else:
            st.markdown(f"<div style='text-align:center;color:#E74C3C;font-family:Cinzel,serif;font-size:.7rem;'>⚔️ Onda {ss.wave} ativa!</div>",unsafe_allow_html=True)
            if st.button("🔄 Atualizar",use_container_width=True): st.rerun()

        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📜 Log</div>",unsafe_allow_html=True)
        log_html="".join(
            f"<div class='log-entry {'kill' if '💀' in e else 'gold' if '💰' in e else 'wave'}'>{e}</div>"
            for e in reversed(ss.combat_log[-25:])
        )
        st.markdown(f"<div class='log-box'>{log_html}</div>",unsafe_allow_html=True)

    if ss.wave_active and ss.screen=="game":
        time.sleep(0.15); st.rerun()
    if ss.screen!="game": st.rerun()


def screen_upgrade():
    inject_global_css()
    ss=st.session_state
    st.markdown(f"""
    <div style='text-align:center;padding:28px 0 18px;'>
        <div style='font-family:"Cinzel Decorative",cursive;font-size:1.9rem;color:#D4AF37;
                    text-shadow:0 0 20px rgba(212,175,55,.5);'>✨ Escolha sua Melhoria ✨</div>
        <div style='font-family:Cinzel,serif;font-size:.82rem;color:#7A7A8A;margin-top:7px;'>
            Onda {ss.wave} superada! Ouro: {ss.gold}g · Score: {ss.score:,}
        </div>
    </div>""",unsafe_allow_html=True)
    cols=st.columns(len(ss.pending_upgrades))
    for i,(col,upg) in enumerate(zip(cols,ss.pending_upgrades)):
        with col:
            st.markdown(f"""
            <div class='upg-card'>
                <span class='upg-icon'>{upg['icon']}</span>
                <div class='upg-name'>{upg['name']}</div>
                <div class='upg-desc'>{upg['desc']}</div>
            </div>""",unsafe_allow_html=True)
            if st.button("🗡️ Escolher",key=f"upg_{i}",use_container_width=True):
                ss.upgrades.append(upg["id"])
                ss.combat_log.append(f"✨ {upg['name']} ({upg['desc']})")
                ss.pending_upgrades=[];ss.screen="game";st.rerun()
    c1,c2,c3=st.columns([1,2,1])
    with c2:
        if st.button("⏭️ Pular",use_container_width=True):
            ss.pending_upgrades=[];ss.screen="game";st.rerun()


def screen_gameover():
    inject_global_css()
    ss=st.session_state
    st.markdown(f"""
    <div class='end-screen'>
        <div class='end-title' style='color:#C0392B;text-shadow:0 0 40px rgba(192,57,43,.7);'>💀 DERROTADO 💀</div>
        <div class='end-sub'>O castelo caiu. As trevas avançaram.</div>
        <div style='font-family:Cinzel,serif;font-size:.95rem;color:#D4AF37;margin-bottom:8px;'>
            Onda {ss.wave}/{ss.max_waves} · Mapa #{ss.map_seed}
        </div>
        <div style='font-family:Cinzel,serif;font-size:.85rem;color:#7A7A8A;'>
            Score: {ss.score:,} · Kills: {ss.kills} · Torres: {tower_count()}
        </div>
    </div>""",unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,1])
    with c2:
        if st.button("🔄 Tentar Novamente",use_container_width=True):
            reset_game();st.rerun()
        if st.button("🏠 Menu",use_container_width=True):
            reset_game();st.session_state.screen="menu";st.rerun()


def screen_victory():
    inject_global_css()
    ss=st.session_state
    st.markdown(f"""
    <div class='end-screen'>
        <div class='end-title' style='color:#D4AF37;text-shadow:0 0 40px rgba(212,175,55,.8);'>🏆 VITÓRIA! 🏆</div>
        <div class='end-sub'>O castelo foi defendido. As trevas foram derrotadas!</div>
        <div style='font-family:Cinzel,serif;font-size:1rem;color:#D4AF37;margin-bottom:8px;'>
            {ss.max_waves} ondas superadas · Mapa #{ss.map_seed}
        </div>
        <div style='font-family:Cinzel,serif;font-size:.85rem;color:#7A7A8A;'>
            Score: {ss.score:,} · Kills: {ss.kills} · Melhorias: {len(ss.upgrades)}/{len(ROGUELIKE_UPGRADES)}
        </div>
    </div>""",unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,1])
    with c2:
        if st.button("🔄 Jogar Novamente",use_container_width=True):
            reset_game();st.rerun()
        if st.button("🏠 Menu",use_container_width=True):
            reset_game();st.session_state.screen="menu";st.rerun()

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
