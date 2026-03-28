# 🏰 Tower Siege: Ruínas Eternas

**Tower Siege: Ruínas Eternas** é um jogo Tower Defense Roguelike de fantasia sombria desenvolvido em Python. O projeto utiliza o **Streamlit** como motor de interface, elevando os limites da biblioteca ao integrar renderização de sprites em tempo real, sistema de animações de combate via iframes sandboxed e pixel art puro em CSS/Canvas.

---

## 🎨 Diferenciais Técnicos (Engine)

Seguindo a filosofia do Dark Castle, o **Tower Siege** utiliza soluções de engenharia criativas para superar as limitações do Streamlit:

* **Renderização via Iframes (Sandboxing)**: A arena de combate é renderizada dentro de um `st.components.v1.html`, funcionando como um ambiente isolado. Isso evita o *sanitizing* de HTML do Streamlit e permite o controle total do canvas, eventos de mouse e animações complexas sem conflito com o ciclo de renderização do framework.

* **Sprites em Pixel Art (Canvas 2D)**: Todos os personagens, torres e terrenos são desenhados via `canvas.getContext('2d')` usando primitivas geométricas (fillRect, arc, beginPath). Nenhum arquivo de imagem externo é utilizado — os sprites existem puramente em código, garantindo carregamento instantâneo e uma estética *pixel art* autêntica com detalhes como sombras, olhos e texturas de grama.

* **Sistema de Animação de Combate**: Três camadas de animação simultâneas:
  - **Hit Flash**: Círculo colorido que expande e desaparece ao acertar um inimigo (`@keyframes hit-anim`)
  - **Kill FX**: Emoji 💀 que flutua para cima ao eliminar uma criatura (`@keyframes kill-anim`)
  - **Damage Numbers**: Números de dano em vermelho que sobem do ponto de impacto (`@keyframes dmg-anim`)
  - **Wave Clear Flash**: Flash dourado na tela inteira ao completar uma onda

* **Sistema de Tick Independente**: O jogo processa múltiplos ticks por render do Streamlit (6 ticks/frame por padrão) e usa `time.sleep + st.rerun()` para criar um loop de jogo responsivo sem bloquear a interface.

---

## 🎮 Funcionalidades do Jogo

### 🏹 Sistema de Torres (5 tipos únicos)

| Torre | Custo | Dano | Alcance | Especial |
|-------|-------|------|---------|---------|
| **Arqueiro** 🏹 | 80g | 18 | 3 | Ataque rápido, versátil |
| **Mago** 🔮 | 130g | 35 | 2.5 | Dano em área + chain lightning |
| **Balista** ⚡ | 200g | 65 | 4 | Dano perfurante brutal, longa distância |
| **Gelo** ❄️ | 110g | 12 | 2 | Lentifica inimigos em -40% (até -60%) |
| **Canhão** 💣 | 160g | 50 | 2.5 | Explosão em área 3x3 |

### 👾 Bestiário (6 tipos de inimigos)

* **Goblin**: Rápido e fraco, aparece em massa nas primeiras ondas
* **Esqueleto**: Balanceado, moderado em velocidade e HP
* **Orc**: Tanque lento, muito HP, recompensa média
* **Wraith (Espectro)**: O mais rápido de todos, esquiva facilmente das torres lentas
* **Troll**: Boss de meia-campanha, HP colossal, recompensa alta
* **Dragão** 🐉: Boss final, 900+ HP escalados, recompensa massiva

### ✨ Sistema Roguelike (10 Melhorias Únicas)

Ao completar cada onda, escolha **1 de 3** melhorias aleatórias:

| Melhoria | Efeito |
|----------|--------|
| 🔩 Flechas de Ferro | +25% dano Arqueiros |
| ⚗️ Surto de Mana | +40% dano Magos |
| 🌨️ Permafrost | Gelo lentifica -60% |
| 🏹 Tiro Duplo | Arqueiros disparam 2x |
| 💥 Ponta Explosiva | Balista causa splash |
| 💰 Corrida do Ouro | +50% ouro de inimigos |
| 🛡️ Fortalecer | +2 vidas extras |
| 🔮 Nexo Arcano | Torres custam -20% |
| ⚡ Relâmpago em Cadeia | Mago atinge 3 alvos |
| 🪣 Barril Titã | +80% dano Canhão |

### 🗺️ Progressão e Economia

* **15 Ondas** com dificuldade crescente
* **Escalonamento 22% por onda**: HP e velocidade dos inimigos aumentam a cada wave
* **Bônus por onda**: `40 + (onda × 15)` ouro ao limpar a onda
* **Mercado dinâmico**: Torres com custo reduzido via Nexo Arcano
* **Permadeath**: Uma vida perdida para cada inimigo que alcança o fim do caminho

---

## 🗺️ Layout do Mapa

O mapa é uma grade de **14×10** células com um caminho fixo sinuoso de 29 waypoints. Torres podem ser construídas em qualquer célula de grama que não seja parte do caminho.

### Réguas de Coordenadas
O mapa exibe **réguas douradas** nas bordas superior e esquerda, permitindo que o jogador identifique visualmente a posição (coluna, linha) de cada célula antes de construir.

```
     Col → 0   1   2   3   4  ...  13
Linha ↓ ┌───┬───┬───┬───┬───┬    ┬───┐
  0     │   │   │▒▒▒│   │   │    │   │   ← ▒▒▒ = caminho
  1     │   │   │▒▒▒│   │   │    │   │
  2     │   │   │▒▒▒│▒▒▒│▒▒▒│... │   │
 ...    │   │   │   │   │   │    │   │
  9     │   │   │   │   │   │ ▒▒▒│▒▒▒│ → END
        └───┴───┴───┴───┴───┴    ┴───┘
START → (0,4)                    END → (13,7)
```

### Como posicionar torres
1. **Hover no mapa**: Passe o mouse sobre qualquer célula — a coordenada `(Col, Linha)` aparece em um tooltip e é destacada com borda dourada (válida) ou vermelha (bloqueada).
2. **Clique direto no mapa**: Com uma torre selecionada, clique sobre uma célula de grama para construí-la instantaneamente.
3. **Formulário numérico**: No painel lateral, insira a coluna e a linha manualmente e clique em "Construir". O sistema valida em tempo real se a posição é livre.

---

## 🛠️ Tecnologias Utilizadas

* **Python 3.x**: Lógica principal, sistema de ticks, IA dos inimigos e gerenciamento de estado via `session_state`
* **Streamlit**: Framework de interface web, roteamento de telas e componentes de input
* **HTML5 Canvas 2D**: Renderização de sprites, terreno e inimigos via primitivas geométricas
* **JavaScript (Vanilla)**: Loop de animação, sistema de efeitos visuais, detecção de clique na arena
* **CSS3 Keyframes**: Animações de hit, kill e damage numbers
* **Google Fonts**: Fontes *Cinzel Decorative* e *Cinzel* para a estética Dark Fantasy

---

## 🚀 Como Executar

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/SEU_USUARIO/tower-siege
   cd tower-siege
   ```

2. **Instale as dependências**:
   ```bash
   pip install streamlit
   ```

3. **Inicie o jogo**:
   ```bash
   streamlit run tower_siege.py
   ```

4. **Acesse no navegador**: `http://localhost:8501`

> 💡 **Dica**: Use `streamlit run tower_siege.py --server.runOnSave false` para evitar reloads acidentais durante o jogo.

---

## 📜 Regras de Combate

* **Targeting**: Cada torre ataca o inimigo mais avançado no caminho dentro de seu alcance
* **Dano**: Calculado pelo atributo `damage` da torre, modificado pelas melhorias roguelike
* **Lentidão (Frost)**: Reduz a velocidade de movimento do inimigo no tick atual; se múltiplas torres de gelo cobrem o mesmo inimigo, o efeito se acumula
* **Área (Mago/Canhão)**: Inimigos adjacentes ao alvo principal recebem 60% do dano
* **Permadeath**: Ao perder todas as 20 vidas, o progresso é perdido completamente

---

## 🔧 Arquitetura Técnica

```
tower_siege.py
├── CONSTANTS          — Definições de torres, inimigos e caminho
├── SESSION STATE      — Inicialização e persistência do estado
├── GAME LOGIC
│   ├── tick_game()    — Loop principal: spawn, movimento, combate
│   ├── start_wave()   — Inicia nova onda com fila de inimigos
│   └── apply_upgrades_to_tower() — Modificadores roguelike em runtime
├── IFRAME RENDERER
│   └── build_arena_html() — Canvas 2D + animações JS sandboxed
└── SCREENS
    ├── screen_menu()     — Tela inicial
    ├── screen_game()     — Gameplay principal
    ├── screen_upgrade()  — Seleção de melhoria roguelike
    ├── screen_gameover() — Derrota
    └── screen_victory()  — Vitória
```

---

## 🤝 Contribuições

Sugestões de novos tipos de torre, inimigos, melhorias roguelike ou otimizações no sistema de ticks são muito bem-vindas! Abra uma issue ou pull request.

---

## 📋 Changelog

### v1.2 — Mapa Aleatório + Balanceamento + Clique Funcional
- **HP dos inimigos aumentado ≈2.5×** — combates duram muito mais e exigem mais estratégia de posicionamento
- **Escala por onda reduzida de +22% → +15%** — ramp mais gradual
- **Mapa gerado aleatoriamente** a cada novo jogo via semente (`map_seed`), criando caminhos únicos com serpentinas e desvios verticais aleatórios
- **Clique no mapa funciona** — ao clicar numa célula de grama válida com torre selecionada, a URL do pai é atualizada com `?_pc=C&_pr=R`; o Streamlit detecta via `st.query_params` e constrói instantaneamente
- Número do mapa exibido no HUD (ex: `🗺️ Mapa #42837`)

### v1.1 — Réguas de Coordenadas + Hover
- Réguas douradas de col/linha nas bordas do mapa
- Highlight dourado/vermelho no hover com coordenada da célula
- Formulário com validação em tempo real

### v1.0 — Lançamento inicial
- Tower Defense + Roguelike em Streamlit
- 5 torres, 6 inimigos, 10 melhorias, 15 ondas

**Desenvolvido com ⚔️ e 🐍 — inspirado em Dark Castle: Ascensão por Gustavo Meneses.**
