from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import random
import logging
    
from ..adapters.pokeapi_client import PokemonDatabase
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Status Effects Enum
class StatusEffect:
    BURN = "burn"
    POISON = "poison" 
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    CONFUSION = "confusion"

@dataclass
class Pokemon:
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int
    types: List[str]
    moves: List[Dict]
    status_effects: List[str] = field(default_factory=list)
    status_turns: Dict[str, int] = field(default_factory=dict)

@dataclass
class BattleResult:
    winner: Optional[str]
    turns: List[Dict]
    battle_summary: str

class StatusEffectManager:
    """Manages status effects and their impacts"""
    
    @staticmethod
    def apply_status_effect(pokemon: Pokemon, status: str) -> str:
        """Apply a status effect to a Pokemon"""
        if status in pokemon.status_effects:
            return f"{pokemon.name} is already {status}!"
        
        # Some status effects are mutually exclusive with major conditions
        if status in [StatusEffect.BURN, StatusEffect.POISON, StatusEffect.PARALYSIS, 
                     StatusEffect.SLEEP, StatusEffect.FREEZE]:
            # Remove other major status effects
            major_statuses = [StatusEffect.BURN, StatusEffect.POISON, StatusEffect.PARALYSIS,
                            StatusEffect.SLEEP, StatusEffect.FREEZE]
            for existing_status in major_statuses:
                if existing_status in pokemon.status_effects:
                    pokemon.status_effects.remove(existing_status)
                    pokemon.status_turns.pop(existing_status, None)
        
        pokemon.status_effects.append(status)
        
        # Set duration for temporary effects
        if status == StatusEffect.SLEEP:
            pokemon.status_turns[status] = random.randint(1, 3)  # 1-3 turns
        elif status == StatusEffect.CONFUSION:
            pokemon.status_turns[status] = random.randint(2, 5)  # 2-5 turns
        
        return f"{pokemon.name} is now {status}!"
    
    @staticmethod
    def process_status_damage(pokemon: Pokemon) -> Tuple[int, str]:
        """Process end-of-turn status damage"""
        damage = 0
        messages = []
        
        for status in pokemon.status_effects.copy(): 
            if status == StatusEffect.BURN:
                burn_damage = max(1, pokemon.max_hp // 16) 
                damage += burn_damage
                messages.append(f"{pokemon.name} is hurt by its burn! (-{burn_damage} HP)")
            
            elif status == StatusEffect.POISON:
                poison_damage = max(1, pokemon.max_hp // 8) 
                damage += poison_damage
                messages.append(f"{pokemon.name} is hurt by poison! (-{poison_damage} HP)")
        
        return damage, "; ".join(messages)
    
    @staticmethod
    def can_move(pokemon: Pokemon) -> Tuple[bool, str]:
        """Check if Pokemon can move this turn"""
        messages = []
        
        # Process temporary status effects
        for status in pokemon.status_effects.copy():
            if status == StatusEffect.PARALYSIS:
                if random.random() < 0.25: 
                    return False, f"{pokemon.name} is paralyzed and can't move!"
            
            elif status == StatusEffect.SLEEP:
                turns_left = pokemon.status_turns.get(status, 0)
                if turns_left > 0:
                    pokemon.status_turns[status] = turns_left - 1
                    if pokemon.status_turns[status] <= 0:
                        pokemon.status_effects.remove(StatusEffect.SLEEP)
                        pokemon.status_turns.pop(StatusEffect.SLEEP, None)
                        return True, f"{pokemon.name} woke up!"
                    else:
                        return False, f"{pokemon.name} is fast asleep!"
            
            elif status == StatusEffect.FREEZE: 
                if random.random() < 0.2:
                    pokemon.status_effects.remove(StatusEffect.FREEZE)
                    return True, f"{pokemon.name} thawed out!"
                else:
                    return False, f"{pokemon.name} is frozen solid!"
            
            elif status == StatusEffect.CONFUSION:
                turns_left = pokemon.status_turns.get(status, 0)
                if turns_left > 0:
                    pokemon.status_turns[status] = turns_left - 1
                    if pokemon.status_turns[status] <= 0:
                        pokemon.status_effects.remove(StatusEffect.CONFUSION)
                        pokemon.status_turns.pop(StatusEffect.CONFUSION, None)
                        messages.append(f"{pokemon.name} snapped out of confusion!")
                    else:   
                        if random.random() < 0.5:
                            return False, f"{pokemon.name} is confused and hurt itself!"
        
        return True, "; ".join(messages) if messages else ""
    
    @staticmethod
    def modify_damage(pokemon: Pokemon, damage: int, is_physical: bool) -> int:
        """Modify damage based on status effects"""
        if StatusEffect.BURN in pokemon.status_effects and is_physical:
            damage = damage // 2 
        
        return damage

class BattleSimulator:
    def __init__(self, db: PokemonDatabase):
        self.db = db
        self.status_manager = StatusEffectManager()

    async def _get_type_effectiveness(self, attacking_type: str, defending_types: List[str]) -> float:
        """Use database method for type effectiveness"""
        return await self.db.get_type_effectiveness(attacking_type, defending_types)

    def _get_move_status_chance(self, move_name: str) -> Tuple[Optional[str], float]:
        """Get status effect and chance for specific moves"""
        move_status_map = {
            # Fire moves
            'flamethrower': (StatusEffect.BURN, 0.1),
            'fire-blast': (StatusEffect.BURN, 0.1),
            'ember': (StatusEffect.BURN, 0.1),
            'fire-punch': (StatusEffect.BURN, 0.1),
            
            # Electric moves  
            'thunderbolt': (StatusEffect.PARALYSIS, 0.1),
            'thunder-shock': (StatusEffect.PARALYSIS, 0.1),
            'thunder': (StatusEffect.PARALYSIS, 0.3),
            'nuzzle': (StatusEffect.PARALYSIS, 1.0), 
            
            # Poison moves
            'poison-sting': (StatusEffect.POISON, 0.3),
            'toxic': (StatusEffect.POISON, 0.9),
            'poison-jab': (StatusEffect.POISON, 0.3),
            'sludge-bomb': (StatusEffect.POISON, 0.3),
            
            # Sleep moves
            'sleep-powder': (StatusEffect.SLEEP, 0.75),
            'spore': (StatusEffect.SLEEP, 1.0),
            'hypnosis': (StatusEffect.SLEEP, 0.6),
            
            # Ice moves
            'ice-beam': (StatusEffect.FREEZE, 0.1),
            'blizzard': (StatusEffect.FREEZE, 0.1),
            
            # Confusion moves
            'confusion': (StatusEffect.CONFUSION, 0.1),
            'psybeam': (StatusEffect.CONFUSION, 0.1),
        }
        
        return move_status_map.get(move_name.lower(), (None, 0.0))

    # Calculate damage with comprehensive mechanics returns (damage, is_critical, status_inflicted)
    async def _calculate_damage(self, attacker: Pokemon, defender: Pokemon, move: Dict) -> Tuple[int, bool, Optional[str]]: 
        power = move.get('power', 0)
        if not power or int(power) <= 0:
            return 0, False, None
        
        power = int(power)
        
        # Get type effectiveness
        effectiveness = await self._get_type_effectiveness(move['type'], defender.types)
        
        # Determine attack and defense stats based on move type
        is_physical = move['damage_class'] == 'physical'
        if is_physical:
            attack_stat = int(attacker.attack)
            defense_stat = int(defender.defense)
        else: 
            attack_stat = int(attacker.special_attack)
            defense_stat = int(defender.special_defense)

        # Fixed level
        level = 50

        # Base damage formula
        base_damage = ((2 * level / 5 + 2) * power * attack_stat / defense_stat) / 50 + 2

        # Apply type effectiveness
        base_damage *= effectiveness

        # Critical hit calculation (1/16 chance)
        is_critical = random.random() < (1/16)
        if is_critical:
            base_damage *= 1.5

        # Random factor (0.85 to 1.0)
        damage = base_damage * random.uniform(0.85, 1.0)

        # STAB (Same Type Attack Bonus)
        if move['type'] in attacker.types:
            damage *= 1.5

        # Apply status effect modifications
        damage = self.status_manager.modify_damage(attacker, int(damage), is_physical)

        # Check for status effect infliction
        status_effect, status_chance = self._get_move_status_chance(move['name'])
        status_inflicted = None
        
        if status_effect and random.random() < status_chance:
            status_message = self.status_manager.apply_status_effect(defender, status_effect)
            status_inflicted = status_effect

        return max(1, int(damage)), is_critical, status_inflicted

    async def simulate_battle(self, pokemon1: Pokemon, pokemon2: Pokemon) -> BattleResult:
        """Simulate a comprehensive Pokemon battle with status effects"""
        current_hp1 = pokemon1.hp
        current_hp2 = pokemon2.hp
        turns = []  
        turn_count = 0
        max_turns = 100

        while current_hp1 > 0 and current_hp2 > 0 and turn_count < max_turns:
            turn_count += 1
            turn_details = {'turn': turn_count, 'actions': []}

            # Determine turn order based on speed (with paralysis check)
            speed1 = pokemon1.speed
            speed2 = pokemon2.speed
            
            if StatusEffect.PARALYSIS in pokemon1.status_effects:
                speed1 //= 2
            if StatusEffect.PARALYSIS in pokemon2.status_effects:
                speed2 //= 2
            
            first_pokemon = pokemon1 if speed1 >= speed2 else pokemon2
            second_pokemon = pokemon2 if first_pokemon == pokemon1 else pokemon1

            # First Pokemon's turn
            can_move, status_msg = self.status_manager.can_move(first_pokemon)
            if status_msg:
                turn_details['actions'].append(status_msg)
            
            if can_move:
                if not first_pokemon.moves:
                    turn_details['actions'].append(f"{first_pokemon.name} has no moves and cannot attack!")
                else:
                    attacking_moves = [m for m in first_pokemon.moves if int(m.get('power', 0)) > 0]
                    if not attacking_moves:
                        turn_details['actions'].append(f"{first_pokemon.name} has no attacking moves and struggles helplessly!")
                    else:
                        move = random.choice(attacking_moves)
                        move = random.choice(attacking_moves)
                        
                        damage, is_critical, status_inflicted = await self._calculate_damage(
                            first_pokemon, 
                            second_pokemon if first_pokemon == pokemon1 else pokemon1, 
                            move
                        )
                        
                        # Apply damage
                        if first_pokemon == pokemon1:
                            current_hp2 = max(0, current_hp2 - damage)
                            target_name = second_pokemon.name
                        else:
                            current_hp1 = max(0, current_hp1 - damage)
                            target_name = pokemon1.name
                        
                        action = f"{first_pokemon.name} used {move['name']} and dealt {damage} damage to {target_name}"
                        if is_critical:
                            action += " (Critical hit!)"
                        if status_inflicted:
                            action += f" {target_name} is now {status_inflicted}!"
                        
                        turn_details['actions'].append(action)

            # Check if battle is over
            if current_hp1 <= 0 or current_hp2 <= 0:
                turns.append(turn_details)
                break

            # Second Pokemon's turn
            can_move, status_msg = self.status_manager.can_move(second_pokemon)
            if status_msg:
                turn_details['actions'].append(status_msg)
            
            if can_move and current_hp1 > 0 and current_hp2 > 0:
                if not second_pokemon.moves:
                    turn_details['actions'].append(f"{second_pokemon.name} has no moves and cannot attack!")
                else:
                    attacking_moves = [m for m in second_pokemon.moves if int(m.get('power', 0)) > 0]
                    if not attacking_moves:
                        turn_details['actions'].append(f"{second_pokemon.name} has no attacking moves and struggles helplessly!")
                    else:
                        move = random.choice(attacking_moves)
                        
                        damage, is_critical, status_inflicted = await self._calculate_damage(
                            second_pokemon, 
                            first_pokemon, 
                            move
                        )
                        
                        # Apply damage
                        if second_pokemon == pokemon1:
                            current_hp2 = max(0, current_hp2 - damage)
                            target_name = first_pokemon.name
                        else:
                            current_hp1 = max(0, current_hp1 - damage)
                            target_name = pokemon2.name if second_pokemon == pokemon1 else pokemon1.name
                        
                        action = f"{second_pokemon.name} used {move['name']} and dealt {damage} damage to {target_name}"
                        if is_critical:
                            action += " (Critical hit!)"
                        if status_inflicted:
                            action += f" {target_name} is now {status_inflicted}!"
                        
                        turn_details['actions'].append(action)

            # Process end-of-turn status effects
            for pkmn, name in [(pokemon1, "pokemon1"), (pokemon2, "pokemon2")]:
                if (pkmn == pokemon1 and current_hp1 > 0) or (pkmn == pokemon2 and current_hp2 > 0):
                    status_damage, status_msg = self.status_manager.process_status_damage(pkmn)
                    if status_damage > 0:
                        if pkmn == pokemon1:
                            current_hp1 = max(0, current_hp1 - status_damage)
                        else:
                            current_hp2 = max(0, current_hp2 - status_damage)
                        turn_details['actions'].append(status_msg)

            turns.append(turn_details)

            # Final HP check
            if current_hp1 <= 0 or current_hp2 <= 0:
                break

        # Determine winner
        winner = (pokemon1.name if current_hp1 > 0 else 
                  pokemon2.name if current_hp2 > 0 else 
                  None)

        battle_summary = f"{winner} won in {len(turns)} turns" if winner else "Battle ended in a draw"

        return BattleResult(
            winner=winner,
            turns=turns,
            battle_summary=battle_summary
        )

def prepare_pokemon_for_battle(data: Dict[str, Any]) -> Pokemon:
    # Prepare a Pokemon for battle with proper level 50 stat scaling
    logger.info(f"Preparing Pokemon: {data.get('identifier', 'unknown')}")
    stats = data.get('stats', {})
    
    # Calculate level 50 stats using Pokemon formula
    def calculate_hp(base_hp: int, level: int = 50) -> int:
        return int(((base_hp * 2) * level / 100) + level + 10)
    
    def calculate_stat(base_stat: int, level: int = 50) -> int:
        return int(((base_stat * 2) * level / 100) + 5)
    
    # Get base stats and convert to integers
    base_hp = int(stats.get('hp', 35))
    base_attack = int(stats.get('attack', 50))
    base_defense = int(stats.get('defense', 50))
    base_sp_attack = int(stats.get('special-attack', 50))
    base_sp_defense = int(stats.get('special-defense', 50))
    base_speed = int(stats.get('speed', 50))
    
    # Scale to level 50
    scaled_hp = calculate_hp(base_hp)
    scaled_attack = calculate_stat(base_attack)
    scaled_defense = calculate_stat(base_defense)
    scaled_sp_attack = calculate_stat(base_sp_attack)
    scaled_sp_defense = calculate_stat(base_sp_defense)
    scaled_speed = calculate_stat(base_speed)
    
    logger.info(f"Scaled stats - HP: {base_hp}->{scaled_hp}, Attack: {base_attack}->{scaled_attack}")
    
    return Pokemon(
        name=data['identifier'],
        hp=scaled_hp,
        max_hp=scaled_hp,
        attack=scaled_attack,
        defense=scaled_defense,
        special_attack=scaled_sp_attack,
        special_defense=scaled_sp_defense,
        speed=scaled_speed,
        types=data.get('types', []),
        moves=[
            {
                'name': move['move']['name'],
                'type': move['move']['type']['name'],
                'power': int(move['move'].get('power') or 0),
                'accuracy': int(move['move'].get('accuracy') or 100),
                'damage_class': move['move']['movedamageclass']['name']
            } for move in data.get('moves', [])[:4]
            if move['move'].get('power')
        ],
        status_effects=[],
        status_turns={} 
    )

class BattleSimulationTool: 
    def __init__(self, db: PokemonDatabase):
        self.db = db
        self.battle_simulator = BattleSimulator(db)

    def setup_tools(self, mcp: FastMCP):
        @mcp.tool()
        async def simulate_pokemon_battle(
            pokemon1_name: str,
            pokemon2_name: str,
            detailed: bool = True
        ) -> Dict[str, Any]:    
            try:
                logger.info(f"Starting battle simulation: {pokemon1_name} vs {pokemon2_name}")
                
                # Fetch Pokemon data
                pokemon1_data = await self.db.get_pokemon_by_name(pokemon1_name.lower())
                pokemon2_data = await self.db.get_pokemon_by_name(pokemon2_name.lower())

                if not pokemon1_data:
                    return {"error": f"Pokemon not found: {pokemon1_name}"}
                if not pokemon2_data:
                    return {"error": f"Pokemon not found: {pokemon2_name}"}

                # Prepare Pokemon with level scaling
                pokemon1 = prepare_pokemon_for_battle(pokemon1_data)
                pokemon2 = prepare_pokemon_for_battle(pokemon2_data)

                logger.info(f"Battle ready: {pokemon1.name} (HP: {pokemon1.hp}) vs {pokemon2.name} (HP: {pokemon2.hp})")

                # Simulate battle
                battle_result = await self.battle_simulator.simulate_battle(pokemon1, pokemon2)

                # Format
                result = {
                    'pokemon1': pokemon1.name,
                    'pokemon2': pokemon2.name,
                    'winner': battle_result.winner,
                    'total_turns': len(battle_result.turns),
                    'battle_summary': battle_result.battle_summary,
                    'status_effects_used': True,
                    'battle_mechanics': [
                        "Type effectiveness calculations",
                        "Damage formulas based on stats and move power", 
                        "Speed-based turn order",
                        "Status effects: Burn, Poison, Paralysis, Sleep, Freeze, Confusion",
                        "Critical hits and STAB bonuses",
                        "Level 50 stat scaling"
                    ]
                }
                
                if detailed:
                    result['detailed_turns'] = battle_result.turns
                
                return result

            except Exception as e:
                logger.error(f"Error in battle simulation: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return {"error": f"Battle simulation failed: {str(e)}"}
        