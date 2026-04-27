# WYD Bot - Legends of Midgard

Bot inteligente para **WYD (With Your Destiny)** no servidor **[Legends of Midgard](https://legendsofmidgard.com.br)** usando visão computacional e automação, com base preparada para Reinforcement Learning.

## Funcionalidades

- **Captura de tela em tempo real** — usa `mss` para captura rápida e eficiente
- **Visão computacional** — detecta HP/MP, monstros, itens no chão usando OpenCV
- **Automação humanizada** — controle de teclado/mouse com variações aleatórias
- **Anti-detecção** — delays aleatórios, offsets no mouse, padrões variados de movimento
- **Sistema de decisão inteligente** — engine de regras com 7 estratégias por prioridade:
  - **Resurrect** (prioridade 300) — ressurreição automática após morte
  - **Flee** (prioridade 200) — fuga quando HP crítico
  - **Heal** (prioridade 100) — uso automático de poções de HP/MP com cooldown
  - **ReturnToTown** (prioridade 90) — volta para cidade quando sem poções
  - **AutoBuff** (prioridade 80) — usa buffs automaticamente em intervalo configurável
  - **Loot** (prioridade 75) — coleta de itens com detecção de drops raros
  - **Farm** (prioridade 50) — ataque a monstros e patrulha com múltiplos padrões
- **Estatísticas em tempo real** — kills/hora, loot/hora, poções usadas
- **Overlay de debug** — visualização detalhada do que o bot está fazendo
- **Screenshot de drops raros** — captura automática quando item raro é detectado
- **Configuração flexível** — tudo configurável via YAML
- **Hotkeys** — F9 para pausar/continuar, F10 para parar
- **Base para RL** — ambiente Gymnasium pronto para treinar com stable-baselines3

## Requisitos

- Python 3.10+
- Windows (para rodar o WYD) — o bot funciona em Windows e Linux
- WYD instalado e configurado no servidor Legends of Midgard

## Instalação

### Windows (PowerShell)

```powershell
# Clonar o repositório
git clone https://github.com/Dev-Aprendiz0/wyd-bot.git
cd wyd-bot

# Criar ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# Se der erro de permissão, rode antes:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Instalar dependências básicas
pip install -e .

# (Opcional) Instalar dependências de RL/ML
pip install -e ".[ml]"

# (Opcional) Instalar dependências de desenvolvimento
pip install -e ".[dev]"
```

### Linux / Mac

```bash
git clone https://github.com/Dev-Aprendiz0/wyd-bot.git
cd wyd-bot
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Uso Rápido

### 1. Calibração (primeira vez)

Abra o WYD e execute o modo de calibração para capturar uma screenshot:

```bash
# Opção 1: Com o venv ativado
wyd-bot --calibrate

# Opção 2: Sem ativar o venv (funciona sempre)
python -m wyd_bot --calibrate
```

Use a screenshot gerada em `screenshots/` para identificar as coordenadas das barras de HP/MP e ajuste no arquivo `config/default.yaml`.

### 2. Executar o bot

```bash
# Com configuração padrão
python -m wyd_bot

# Com configuração customizada
python -m wyd_bot -c config/minha_config.yaml

# Com logging detalhado
python -m wyd_bot -v
```

> **Nota Windows:** Se `wyd-bot` não funcionar como comando, use `python -m wyd_bot` que funciona sempre.

### 3. Controles

| Tecla | Ação |
|-------|------|
| F9    | Pausar / Continuar |
| F10   | Parar o bot |

## Configuração

Edite `config/default.yaml` para ajustar o comportamento do bot:

```yaml
# Barras de HP/MP (ajuste para sua resolução)
hp_mp:
  hp_region:
    x: 90
    y: 8
    width: 150
    height: 12

# Combate
combat:
  attack_key: "space"
  skill_keys: ["1", "2", "3", "4"]
  hp_heal_threshold: 0.5   # Usar poção quando HP < 50%
  hp_potion_key: "f1"
  potion_cooldown: 2.0     # Segundos entre poções

# Farm
farm:
  loot_enabled: true
  walk_pattern: "mixed"    # circular, square, random, mixed

# Auto-buff
buff:
  enabled: true
  buff_keys: ["5", "6"]    # Teclas dos seus buffs
  buff_interval: 300.0     # 5 minutos

# Ressurreição automática
resurrect:
  enabled: true
  resurrect_key: "enter"

# Anti-detecção
anti_detection:
  enabled: true
```

## Arquitetura

```
wyd_bot/
├── vision/              # Visão computacional
│   ├── screen_capture.py  # Captura de tela (mss)
│   ├── detector.py        # Detecção de HP/MP, monstros, itens
│   └── ocr.py             # Leitura de texto (base)
├── automation/          # Automação de inputs
│   ├── keyboard.py        # Controle de teclado
│   ├── mouse.py           # Controle de mouse (humanizado)
│   └── actions.py         # Ações de alto nível (atacar, curar, etc.)
├── decision/            # Sistema de decisão
│   ├── state.py           # Estado do jogo + SessionStats
│   ├── strategy.py        # 7 estratégias (Resurrect, Flee, Heal, etc.)
│   └── rule_engine.py     # Motor de regras por prioridade
├── rl/                  # Reinforcement Learning
│   ├── environment.py     # Ambiente Gymnasium
│   └── agent.py           # Agente RL (PPO)
├── utils/               # Utilitários
│   ├── config.py          # Sistema de configuração
│   └── logger.py          # Logging
├── overlay.py           # Overlay visual de debug
├── main.py              # Bot principal
└── __main__.py          # Suporte a python -m wyd_bot
```

## Templates de Monstros/Itens

Para melhorar a detecção, adicione screenshots de monstros e itens:

```
templates/
├── monsters/
│   ├── goblin.png
│   ├── skeleton.png
│   └── ...
└── items/
    ├── potion.png
    ├── gold.png
    └── ...
```

Capture screenshots dos monstros/itens no jogo e salve como PNG. O bot usa template matching para encontrá-los na tela.

## Reinforcement Learning (Avançado)

O bot inclui uma base para treinar com RL:

```python
from wyd_bot.rl.environment import create_wyd_environment
from wyd_bot.rl.agent import RLAgent

# Criar ambiente
env = create_wyd_environment()

# Treinar agente
agent = RLAgent()
agent.train(env, total_timesteps=100000, save_path="models/wyd_ppo")

# Usar agente treinado
agent = RLAgent(model_path="models/wyd_ppo")
action = agent.predict(game_state)
```

## Testes

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Aviso Legal

Este projeto é apenas para fins educacionais e de estudo. O uso de bots pode violar os termos de serviço do jogo. Use por sua conta e risco.

## Licença

MIT
