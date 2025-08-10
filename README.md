# Pokémon Battle Simulation — MCP Server

A comprehensive Model Context Protocol (MCP) server that provides AI models with access to Pokémon data and battle simulation capabilities. This server acts as a bridge between AI and the Pokémon world, enabling sophisticated battles and data analysis.

MCP server exposing:

- Resource: `pokemon://info/{name}` — structured JSON (stats, types, abilities, moves, evolution)
- Tool: `simulate_pokemon_battle` — realistic battle simulation

The database is built automatically on first run.

## Assessment Implementation

This project fulfills all requirements for the Pokémon Battle Simulation MCP Server technical assessment:

### Part 1: Pokémon Data Resource

- **Comprehensive Pokémon Database**: Built from PokeAPI CSV data with 800+ Pokémon
- **Complete Stats**: Base stats (HP, Attack, Defense, Special Attack, Special Defense, Speed)
- **Type Information**: All 18 Pokémon types with effectiveness calculations
- **Abilities & Moves**: Detailed ability effects and move descriptions
- **Evolution Data**: Evolution chains and relationships
- **MCP Resource Interface**: Standardized access for LLMs via `pokemon://info/{name}`

### Part 2: Battle Simulation Tool

- **Realistic Battle Mechanics**:
  - Type effectiveness calculations (18 types, 324 interactions)
  - Damage formulas based on actual Pokémon mechanics
  - Speed-based turn order determination
  - Critical hit calculations and STAB bonuses
- **Status Effects**: Implementation of 6 status effects (Burn, Poison, Paralysis, Sleep, Freeze, Confusion)
- **Detailed Battle Logs**: Turn-by-turn action descriptions with damage calculations
- **MCP Tool Interface**: Accessible via `simulate_pokemon_battle` tool

## Quick Start

### 1) Clone & enter

```bash
git clone <your-repo-url> pokemon-mcp
cd pokemon-mcp
```

### 2) Virtual environment

**Windows (PowerShell):**

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.env\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Run the server manually (optional check)

```bash
# If server.py is at repo root:
python -m server
```

The server will start and display:

```
Pokemon Battle Simulation Server ready!
Starting MCP server...
```

## Claude Desktop Integration

Edit the config location:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Or via the app: Claude Desktop → Settings → Developer → Edit Config (create the file if missing).

### Windows config (uses bundled launcher)

```json
{
  "mcpServers": {
    "pokemon-mcp": {
      "command": "C:\\absolute\\path\\to\\pokemon-mcp\\run_server.cmd",
      "cwd": "C:\\absolute\\path\\to\\pokemon-mcp"
    }
  }
}
```

### macOS/Linux config (uses bundled launcher)

First, make the launcher executable:

```bash
chmod +x run_server.sh
```

Then set:

```json
{
  "mcpServers": {
    "pokemon-mcp": {
      "command": "/absolute/path/to/pokemon-mcp/run_server.sh",
      "cwd": "/absolute/path/to/pokemon-mcp"
    }
  }
}
```

After editing, fully restart Claude Desktop (it caches MCP capabilities).

## Using the MCP Interfaces

### Resource

- URI: `pokemon://info/{name}`
- In Claude: Add from server → select Pokémon Info → set `name` (e.g., `Pichu`).

### Tool

- Name: `simulate_pokemon_battle`
- Args: `pokemon1_name`, `pokemon2_name`, `detailed` (optional)

## Usage Examples

### MCP Resource Usage

#### Get Pokémon Information

```
Resource URI: pokemon://info/pikachu
Returns: Complete JSON with stats, types, abilities, moves, and evolution data
```

**Example Response Structure**:

```json
{
  "data": {
    "pokemon": [{
      "name": "pikachu",
      "pokemonstats": [
        {"base_stat": 35, "stat": {"name": "hp"}},
        {"base_stat": 55, "stat": {"name": "attack"}},
        {"base_stat": 40, "stat": {"name": "defense"}},
        {"base_stat": 50, "stat": {"name": "special-attack"}},
        {"base_stat": 50, "stat": {"name": "special-defense"}},
        {"base_stat": 90, "stat": {"name": "speed"}}
      ],
      "pokemontypes": [{"type": {"name": "electric"}}],
      "pokemonabilities": [...],
      "pokemonmoves": [...],
      "pokemonspecy": {
        "evolutionchain": {...}
      }
    }]
  }
}
```

### MCP Tool Usage

#### Simulate Pokémon Battle

```json
{
  "tool": "simulate_pokemon_battle",
  "arguments": {
    "pokemon1_name": "pikachu",
    "pokemon2_name": "charizard",
    "detailed": true
  }
}
```

**Example Battle Output**:

```json
{
  "pokemon1": "pikachu",
  "pokemon2": "charizard",
  "winner": "charizard",
  "total_turns": 6,
  "battle_summary": "charizard won in 6 turns",
  "detailed_turns": [
    {
      "turn": 1,
      "actions": [
        "pikachu used thunderbolt and dealt 78 damage to charizard (Critical hit!)",
        "charizard used flamethrower and dealt 45 damage to pikachu"
      ]
    }
  ],
  "battle_mechanics": [
    "Type effectiveness calculations",
    "Damage formulas based on stats and move power",
    "Speed-based turn order",
    "Status effects: Burn, Poison, Paralysis, Sleep, Freeze, Confusion",
    "Critical hits and STAB bonuses",
    "Level 50 stat scaling"
  ]
}
```

### Example LLM Queries

Once connected to an LLM with MCP support, you can ask:

- "Show me Pikachu's stats and abilities"
- "Simulate a battle between Charizard and Blastoise"
- "What are the type advantages of Electric moves?"
- "Compare the stats of all starter Pokémon"

## Battle Mechanics Implementation

### Core Battle Features

- **Damage Calculation**: Uses actual Pokémon damage formula with type effectiveness
- **Status Effects**: Full implementation of 6 major status conditions
- **Turn Order**: Speed-based with paralysis modifier
- **Critical Hits**: 1/16 chance with 1.5x damage multiplier
- **STAB**: Same Type Attack Bonus (1.5x damage)
- **Level Scaling**: All Pokémon scaled to level 50 for fair battles

### Status Effects Implemented

1. **Burn**: Halves physical attack, causes HP damage each turn
2. **Poison**: Causes HP damage each turn
3. **Paralysis**: 25% chance to skip turn, halves speed
4. **Sleep**: Cannot move until wake up
5. **Freeze**: Cannot move until thaw
6. **Confusion**: 50% chance to hurt self

## Database Structure

The server uses a comprehensive SQLite database with:

- **800+ Pokémon** with complete data
- **18 Types** with full effectiveness matrix (324 interactions)
- **Moves database** with power, accuracy, and effects
- **Abilities** with descriptions
- **Evolution chains** and species relationships

## Project Structure

```
src/
├── adapters/
│   └── pokeapi_client.py          # Database builder and data access
├── resources/
│   └── pokemon_resource.py        # MCP resource implementation
├── tools/
│   └── battle_simulation.py       # MCP battle simulation tool
├── init_database.py               # Database initialization
└── server.py                      # Main MCP server
```

## Technical Notes

### Performance Optimizations

- SQLite database with optimized indexes
- Efficient move selection for battles
- Cached type effectiveness calculations

### Data Source

- Built from official PokeAPI CSV data
- Comprehensive and accurate Pokémon information
- Regular structure following official game mechanics
