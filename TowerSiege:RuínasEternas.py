import streamlit as st
import json
import streamlit.components.v1 as components

# =========================
# ⚙️ CONFIG
# =========================
GRID_W = 12
GRID_H = 7
CELL = 60

# =========================
# 🧠 ESTADO INICIAL
# =========================
def init_game_state():
    return {
        "gold": 200,
        "lives": 10,
        "wave": 1,
        "score": 0,
        "towers": [],
        "enemies": [],
        "tick": 0
    }

# =========================
# 🎮 ENGINE HTML (CORE)
# =========================
def build_game_html(state):

    state_json = json.dumps(state)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<style>
body {{
    margin: 0;
    background: #020617;
    color: white;
    font-family: Arial;
}}

#hud {{
    display: flex;
    gap: 20px;
    padding: 10px;
    background: #0f172a;
    border-bottom: 2px solid #1e293b;
    font-size: 18px;
}}

canvas {{
    display: block;
    margin: auto;
    background: #020617;
}}
</style>

</head>

<body>

<div id="hud">
💰 <span id="gold"></span>
❤️ <span id="lives"></span>
🏆 <span id="score"></span>
⚔️ <span id="wave"></span>
</div>

<canvas id="game"></canvas>

<script>

let state = {state_json};

// =========================
// 🎯 CONFIG
// =========================
const CELL = {CELL};
const GRID_W = {GRID_W};
const GRID_H = {GRID_H};

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

canvas.width = GRID_W * CELL;
canvas.height = GRID_H * CELL;

// =========================
// 🧠 ENGINE
// =========================

function spawnEnemy() {{
    state.enemies.push({{
        x: 0,
        y: Math.floor(Math.random() * GRID_H),
        hp: 100,
        speed: 0.03
    }});
}}

function update() {{

    state.tick++;

    // spawn progressivo
    if (state.tick % 60 === 0) spawnEnemy();

    // movimentação
    for (let e of state.enemies) {{
        e.x += e.speed;

        if (e.x > GRID_W) {{
            state.lives -= 1;
            e.hp = 0;
        }}
    }}

    // combate
    for (let t of state.towers) {{
        for (let e of state.enemies) {{

            let dx = t.x - e.x;
            let dy = t.y - e.y;
            let dist = Math.sqrt(dx*dx + dy*dy);

            if (dist < 2) {{
                e.hp -= 0.6;

                if (e.hp <= 0) {{
                    state.gold += 10;
                    state.score += 5;
                }}
            }}
        }}
    }}

    // limpar mortos
    state.enemies = state.enemies.filter(e => e.hp > 0);
}}

function drawGrid() {{
    ctx.strokeStyle = "#1e293b";

    for (let x=0; x<canvas.width; x+=CELL) {{
        for (let y=0; y<canvas.height; y+=CELL) {{
            ctx.strokeRect(x, y, CELL, CELL);
        }}
    }}
}}

function draw() {{
    ctx.clearRect(0,0,canvas.width,canvas.height);

    drawGrid();

    // torres
    for (let t of state.towers) {{
        ctx.fillStyle = "#22d3ee";
        ctx.fillRect(t.x * CELL + 5, t.y * CELL + 5, CELL-10, CELL-10);
    }}

    // inimigos
    for (let e of state.enemies) {{
        ctx.fillStyle = "#ef4444";

        ctx.beginPath();
        ctx.arc(e.x * CELL, e.y * CELL + CELL/2, 10, 0, Math.PI*2);
        ctx.fill();
    }}

    // HUD
    document.getElementById("gold").innerText = state.gold;
    document.getElementById("lives").innerText = state.lives;
    document.getElementById("score").innerText = state.score;
    document.getElementById("wave").innerText = state.wave;
}}

// =========================
// 🔁 GAME LOOP
// =========================
function loop() {{
    update();
    draw();
    requestAnimationFrame(loop);
}}

loop();

// =========================
// 🖱️ INPUT
// =========================
canvas.addEventListener("click", (e) => {{

    const rect = canvas.getBoundingClientRect();

    const x = Math.floor((e.clientX - rect.left) / CELL);
    const y = Math.floor((e.clientY - rect.top) / CELL);

    // custo
    if (state.gold >= 50) {{
        state.gold -= 50;
        state.towers.push({{x, y}});
    }}
}});

</script>

</body>
</html>
"""
    return html

# =========================
# 🖥️ APP
# =========================
def main():

    st.set_page_config(layout="wide")
    st.title("🏰 Tower Defense PRO (Engine JS)")

    if "game_state" not in st.session_state:
        st.session_state.game_state = init_game_state()

    html = build_game_html(st.session_state.game_state)

    # 🔥 proteção unicode
    html_safe = html.encode("ascii", "xmlcharrefreplace").decode()

    components.html(html_safe, height=550, scrolling=False)


if __name__ == "__main__":
    main()
