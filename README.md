# WYD Bot - Legends of Midgard

Bot inteligente para **WYD (With Your Destiny)** no servidor **[Legends of Midgard](https://legendsofmidgard.com.br)** usando visão computacional e automação, com base preparada para Reinforcement Learning.

## Funcionalidades

- **Captura de tela em tempo real** — usa `mss` para captura rápida e eficiente
- **Visão computacional** — detecta HP/MP, monstros, itens no chão usando OpenCV
- **Automação humanizada** — controle de teclado/mouse com variações aleatórias
- **Sistema de decisão inteligente** — engine de regras com estratégias por prioridade:
  - **Flee** (prioridade máxima) — fuga quando HP crítico
  - **Heal** — uso automático de poções de HP/MP
  - **Loot** — coleta de itens do chão
  - **Farm** — ataque a monstros e patrulha
- **Overlay de debug** — visualização em tempo real do que o bot está fazendo
- **Configuração flexível** — tudo configurável via YAML
- **Hotkeys** — F9 para pausar/continuar, F10 para parar
- **Base para RL** — ambiente Gymnasium pronto para treinar com stable-baselines3

## Requisitos

- Python 3.10+
- Windows (para rodar o WYD) — o bot funciona em Windows e Linux
- WYD instalado e configurado no servidor Legends of Midgard

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/Dev-Aprendiz0/wyd-bot.git
cd wyd-bot

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependências básicas
pip install -e .

# (Opcional) Instalar dependências de RL/ML
pip install -e ".[ml]"

# (Opcional) Instalar dependências de desenvolvimento
pip install -e ".[dev]"
```

## Uso Rápido

### 1. Calibração (primeira vez)

Abra o WYD e execute o modo de calibração para capturar uma screenshot:

```bash
wyd-bot --calibrate
```

Use a screenshot gerada em `screenshots/` para identificar as coordenadas das barras de HP/MP e ajuste no arquivo `config/default.yaml`.

### 2. Executar o bot

```bash
# Com configuração padrão
wyd-bot

# Com configuração customizada
wyd-bot -c config/minha_config.yaml

# Com logging detalhado
wyd-bot -v
```

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

# Farm
farm:
  loot_enabled: true
  walk_pattern: "circular"
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
│   ├── state.py           # Estado do jogo
│   ├── strategy.py        # Estratégias (Farm, Heal, Loot, Flee)
│   └── rule_engine.py     # Motor de regras por prioridade
├── rl/                  # Reinforcement Learning
│   ├── environment.py     # Ambiente Gymnasium
│   └── agent.py           # Agente RL (PPO)
├── utils/               # Utilitários
│   ├── config.py          # Sistema de configuração
│   └── logger.py          # Logging
├── overlay.py           # Overlay visual de debug
└── main.py              # Bot principal
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
