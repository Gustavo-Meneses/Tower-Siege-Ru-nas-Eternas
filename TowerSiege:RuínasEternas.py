import streamlit as st
import json
import streamlit.components.v1 as components

# =========================
# CONFIG
# =========================
GRID_W = 12
GRID_H = 7
CELL = 60

def init_game_state():
    return {
        "gold": 150,
        "lives": 10,
        "wave": 1,
        "score": 0
    }

def build_game_html(state):

    state_json = json.dumps(state)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    margin:0;
    background:#020617;
    color:white;
    font-family:Arial;
}}

#hud {{
    display:flex;
    gap:20px;
    padding:10px;
    background:#0f172a;
}}

canvas {{
    display:block;
    margin:auto;
}}
</style>
</head>

<body>

<div id="hud">
💰 <span id="gold"></span>
❤️ <span id="lives"></span>
🏆 <span id="score"></span>
</div>

<canvas id="game"></canvas>

<script>

// =========================
// STATE
// =========================
let state = {state_json};

const CELL = {CELL};
const GRID_W = {GRID_W};
const GRID_H = {GRID_H};

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

canvas.width = GRID_W * CELL;
canvas.height = GRID_H * CELL;

// caminho fixo
const path = [];
for (let i=0;i<GRID_W;i++) {{
    path.push({{x:i, y:Math.floor(GRID_H/2)}});
}}

// =========================
// ENTIDADES
// =========================
let enemies = [];
let towers = [];

function spawnEnemy() {{
    enemies.push({{
        pathIndex:0,
        progress:0,
        speed:0.02,
        hp:100,
        maxHp:100
    }});
}}

// =========================
// UPDATE
// =========================
let tick = 0;

function update() {{

    tick++;

    if (tick % 120 === 0) spawnEnemy();

    for (let e of enemies) {{

        e.progress += e.speed;

        if (e.progress >= 1) {{
            e.progress = 0;
            e.pathIndex++;
        }}

        if (e.pathIndex >= path.length-1) {{
            state.lives--;
            e.hp = 0;
        }}
    }}

    // torres
    for (let t of towers) {{

        if (!t.cooldown) t.cooldown = 0;

        if (t.cooldown > 0) {{
            t.cooldown--;
            continue;
        }}

        for (let e of enemies) {{

            let p = path[e.pathIndex];
            let dx = t.x - p.x;
            let dy = t.y - p.y;
            let dist = Math.sqrt(dx*dx + dy*dy);

            if (dist < t.range) {{
                e.hp -= t.damage;
                t.cooldown = 30;
                break;
            }}
        }}
    }}

    enemies = enemies.filter(e => e.hp > 0);
}}

// =========================
// DRAW
// =========================
function drawGrid() {{
    ctx.strokeStyle="#1e293b";
    for (let x=0;x<canvas.width;x+=CELL) {{
        for (let y=0;y<canvas.height;y+=CELL) {{
            ctx.strokeRect(x,y,CELL,CELL);
        }}
    }}
}}

function drawPath() {{
    ctx.fillStyle="#334155";
    for (let p of path) {{
        ctx.fillRect(p.x*CELL,p.y*CELL,CELL,CELL);
    }}
}}

function drawEnemies() {{
    for (let e of enemies) {{

        let p = path[e.pathIndex];

        let x = p.x*CELL;
        let y = p.y*CELL;

        ctx.fillStyle="red";
        ctx.beginPath();
        ctx.arc(x+CELL/2,y+CELL/2,10,0,Math.PI*2);
        ctx.fill();

        // HP bar
        ctx.fillStyle="green";
        ctx.fillRect(x+10,y+5,(e.hp/e.maxHp)*40,5);
    }}
}}

function drawTowers() {{
    for (let t of towers) {{

        ctx.fillStyle="cyan";
        ctx.fillRect(t.x*CELL+10,t.y*CELL+10,40,40);

        // range
        ctx.strokeStyle="rgba(0,255,255,0.2)";
        ctx.beginPath();
        ctx.arc(
            t.x*CELL+CELL/2,
            t.y*CELL+CELL/2,
            t.range*CELL,
            0,
            Math.PI*2
        );
        ctx.stroke();
    }}
}}

function draw() {{
    ctx.clearRect(0,0,canvas.width,canvas.height);

    drawGrid();
    drawPath();
    drawEnemies();
    drawTowers();

    document.getElementById("gold").innerText = state.gold;
    document.getElementById("lives").innerText = state.lives;
    document.getElementById("score").innerText = state.score;
}}

// =========================
// LOOP
// =========================
function loop() {{
    update();
    draw();
    requestAnimationFrame(loop);
}}

loop();

// =========================
// INPUT
// =========================
canvas.addEventListener("click", (e)=>{{

    const rect = canvas.getBoundingClientRect();

    const x = Math.floor((e.clientX-rect.left)/CELL);
    const y = Math.floor((e.clientY-rect.top)/CELL);

    // não pode no caminho
    for (let p of path) {{
        if (p.x===x && p.y===y) return;
    }}

    if (state.gold >= 50) {{
        state.gold -= 50;

        towers.push({{
            x:x,
            y:y,
            range:2,
            damage:10,
            cooldown:0
        }});
    }}
}});

</script>

</body>
</html>
"""
    return html

def main():
    st.set_page_config(layout="wide")

    if "game_state" not in st.session_state:
        st.session_state.game_state = init_game_state()

    html = build_game_html(st.session_state.game_state)

    html_safe = html.encode("ascii", "xmlcharrefreplace").decode()

    components.html(html_safe, height=550, scrolling=False)

if __name__ == "__main__":
    main()
