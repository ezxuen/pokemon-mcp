import aiohttp  
import aiosqlite
import csv
import logging
import zipfile
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime


logger = logging.getLogger(__name__)

# Builds Pokemon SQLite database from PokeAPI CSV data
class PokemonCSVDatabaseBuilder:    
    def __init__(
        self,
        db_path: str = "data/pokemon.db",
        csv_url: str = "https://github.com/PokeAPI/pokeapi/archive/refs/heads/master.zip",
        cache_dir: str = "data/csv_cache"
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_url = csv_url
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Updated CSV files mapping based on PokeAPI structure
        self.required_csvs = {
            "pokemon": "pokemon.csv",
            "pokemon_stats": "pokemon_stats.csv", 
            "pokemon_types": "pokemon_types.csv",
            "pokemon_abilities": "pokemon_abilities.csv",
            "pokemon_moves": "pokemon_moves.csv",
            "stats": "stats.csv",
            "types": "types.csv",
            "abilities": "abilities.csv",
            "ability_prose": "ability_prose.csv",
            "moves": "moves.csv",
            "move_effect_prose": "move_effect_prose.csv",  
            "move_damage_classes": "move_damage_classes.csv",
            "move_effects": "move_effects.csv",
            "type_efficacy": "type_efficacy.csv",
            "pokemon_species": "pokemon_species.csv",
            "evolution_chains": "evolution_chains.csv",
            "version_groups": "version_groups.csv",
            "pokemon_move_methods": "pokemon_move_methods.csv"
        }

    async def build_database(self, force_rebuild: bool = False) -> None:    
        if self.db_path.exists() and not force_rebuild:
            logger.info(f"Database already exists at {self.db_path}")
            return
        
        logger.info("Building Pokemon database from CSV data...")
        
        # Download and extract CSV files
        csv_files = await self._download_and_extract_csvs()
        
        # Create database schema
        await self._create_schema()
        
        # Populate all tables
        await self._populate_all_tables(csv_files)
        
        # Create indexes for performance
        await self._create_indexes()
        
        logger.info(f"Database built successfully at {self.db_path}")

    # Download and extract required CSV files
    async def _download_and_extract_csvs(self) -> Dict[str, Path]:  
        zip_path = self.cache_dir / "pokeapi-master.zip"
        
        # Download if not cached
        if not zip_path.exists():
            logger.info("Downloading PokeAPI CSV data...")
            async with aiohttp.ClientSession() as session:
                async with session.get(self.csv_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download CSV data: {response.status}")
                    
                    with open(zip_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
        
        # Extract CSV files
        csv_files = {}
        logger.info("Extracting CSV files...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for key, filename in self.required_csvs.items():    
                zip_path_in_archive = f"pokeapi-master/data/v2/csv/{filename}"
                
                try:
                    # Extract to cache directory
                    extracted_path = self.cache_dir / filename
                    
                    with zip_ref.open(zip_path_in_archive) as source:
                        with open(extracted_path, 'wb') as target:
                            target.write(source.read())
                    
                    csv_files[key] = extracted_path
                    logger.debug(f"Extracted {filename}")
                    
                except KeyError:
                    logger.warning(f"CSV file not found in archive: {filename}")
        
        logger.info(f"Extracted {len(csv_files)} CSV files")
        return csv_files
    
    # Create database tables
    async def _create_schema(self) -> None: 
        schema = """
        -- Core Pokemon table
        CREATE TABLE pokemon (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            species_id INTEGER,
            height INTEGER,
            weight INTEGER,
            base_experience INTEGER,
            pokemon_order INTEGER,
            is_default BOOLEAN
        );
        
        -- Stats reference table
        CREATE TABLE stats (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            name TEXT
        );
        
        -- Pokemon stats
        CREATE TABLE pokemon_stats (
            pokemon_id INTEGER,
            stat_id INTEGER,
            base_stat INTEGER,
            effort INTEGER,
            PRIMARY KEY (pokemon_id, stat_id),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (stat_id) REFERENCES stats(id)
        );
        
        -- Types reference table  
        CREATE TABLE types (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            name TEXT
        );
        
        -- Pokemon types
        CREATE TABLE pokemon_types (
            pokemon_id INTEGER,
            type_id INTEGER,
            slot INTEGER,
            PRIMARY KEY (pokemon_id, type_id),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (type_id) REFERENCES types(id)
        );
        
        -- Abilities reference table
        CREATE TABLE abilities (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            name TEXT
        );
        
        -- Ability descriptions (English only)
        CREATE TABLE ability_descriptions (
            ability_id INTEGER PRIMARY KEY,
            short_effect TEXT,
            effect TEXT,
            FOREIGN KEY (ability_id) REFERENCES abilities(id)
        );
        
        -- Pokemon abilities
        CREATE TABLE pokemon_abilities (
            pokemon_id INTEGER,
            ability_id INTEGER,
            is_hidden BOOLEAN,
            slot INTEGER,
            PRIMARY KEY (pokemon_id, ability_id, slot),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (ability_id) REFERENCES abilities(id)
        );
        
        -- Move damage classes
        CREATE TABLE move_damage_classes (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            name TEXT
        );
        
        -- Move effects
        CREATE TABLE move_effects (
            id INTEGER PRIMARY KEY
        );
        
        -- Move effect descriptions
        CREATE TABLE move_effect_descriptions (
            move_effect_id INTEGER,
            local_language_id INTEGER,
            short_effect TEXT,
            effect TEXT,
            PRIMARY KEY (move_effect_id, local_language_id),
            FOREIGN KEY (move_effect_id) REFERENCES move_effects(id)
        );
        
        -- Moves reference table (UPDATED to match target structure)
        CREATE TABLE moves (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            name TEXT,
            type_id INTEGER,
            power INTEGER,
            pp INTEGER,
            accuracy INTEGER,
            priority INTEGER,
            damage_class_id INTEGER,
            effect_id INTEGER,
            effect_chance INTEGER,
            FOREIGN KEY (type_id) REFERENCES types(id),
            FOREIGN KEY (damage_class_id) REFERENCES move_damage_classes(id),
            FOREIGN KEY (effect_id) REFERENCES move_effects(id)
        );
        
        -- Version groups for move learning context
        CREATE TABLE version_groups (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            name TEXT
        );
        
        -- Pokemon move methods (how moves are learned)
        CREATE TABLE pokemon_move_methods (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            name TEXT
        );
        
        -- Pokemon moves (UPDATED to match PokeAPI CSV structure)
        CREATE TABLE pokemon_moves (
            pokemon_id INTEGER,
            version_group_id INTEGER,
            move_id INTEGER,
            pokemon_move_method_id INTEGER,
            level INTEGER,
            move_order INTEGER,
            PRIMARY KEY (pokemon_id, move_id, pokemon_move_method_id, version_group_id),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
            FOREIGN KEY (move_id) REFERENCES moves(id),
            FOREIGN KEY (version_group_id) REFERENCES version_groups(id),
            FOREIGN KEY (pokemon_move_method_id) REFERENCES pokemon_move_methods(id)
        );
        
        -- Type effectiveness
        CREATE TABLE type_efficacy (
            damage_type_id INTEGER,
            target_type_id INTEGER,
            damage_factor INTEGER,
            PRIMARY KEY (damage_type_id, target_type_id),
            FOREIGN KEY (damage_type_id) REFERENCES types(id),
            FOREIGN KEY (target_type_id) REFERENCES types(id)
        );
        
        -- Pokemon species
        CREATE TABLE pokemon_species (
            id INTEGER PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            generation_id INTEGER,
            evolves_from_species_id INTEGER,
            evolution_chain_id INTEGER,
            color_id INTEGER,
            shape_id INTEGER,
            habitat_id INTEGER,
            gender_rate INTEGER,
            capture_rate INTEGER,
            base_happiness INTEGER,
            is_baby BOOLEAN,
            hatch_counter INTEGER,
            has_gender_differences BOOLEAN,
            growth_rate_id INTEGER,
            forms_switchable BOOLEAN,
            is_legendary BOOLEAN,
            is_mythical BOOLEAN,
            species_order INTEGER,
            conquest_order INTEGER,
            FOREIGN KEY (evolves_from_species_id) REFERENCES pokemon_species(id)
        );
        
        -- Evolution chains
        CREATE TABLE evolution_chains (
            id INTEGER PRIMARY KEY,
            baby_trigger_item_id INTEGER
        );
        
        -- UPDATED VIEW: Pokemon complete with move data matching target JSON structure
        CREATE VIEW pokemon_complete_with_moves AS
        SELECT 
            p.id,
            p.identifier as name,
            p.height,
            p.weight,
            p.base_experience,
            ps.is_legendary,
            ps.is_mythical,
            ps.generation_id,
            ps.evolution_chain_id,
            ps.evolves_from_species_id,
            json_group_array(
                json_object(
                    'move', json_object(
                        'id', m.id,
                        'name', m.identifier,
                        'power', m.power,
                        'accuracy', m.accuracy,
                        'move_effect_chance', m.effect_chance,
                        'movedamageclass', json_object('name', mdc.identifier),
                        'type', json_object('name', t.identifier),
                        'moveeffect', json_object(
                            'moveeffecteffecttexts', json_array(
                                json_object('short_effect', COALESCE(med.short_effect, ''))
                            )
                        )
                    )
                )
            ) as pokemonmoves
        FROM pokemon p
        JOIN pokemon_species ps ON p.species_id = ps.id
        LEFT JOIN pokemon_moves pm ON p.id = pm.pokemon_id
        LEFT JOIN moves m ON pm.move_id = m.id
        LEFT JOIN move_damage_classes mdc ON m.damage_class_id = mdc.id
        LEFT JOIN types t ON m.type_id = t.id
        LEFT JOIN move_effect_descriptions med ON m.effect_id = med.move_effect_id AND med.local_language_id = 9
        GROUP BY p.id;
        
        -- Other views remain the same
        CREATE VIEW pokemon_stats_view AS
        SELECT 
            ps.pokemon_id,
            s.identifier as stat_name,
            s.name as stat_display_name,
            ps.base_stat,
            ps.effort
        FROM pokemon_stats ps
        JOIN stats s ON ps.stat_id = s.id;
        
        CREATE VIEW pokemon_types_view AS
        SELECT 
            pt.pokemon_id,
            t.identifier as type_name,
            t.name as type_display_name,
            pt.slot
        FROM pokemon_types pt
        JOIN types t ON pt.type_id = t.id;
        
        CREATE VIEW pokemon_abilities_view AS
        SELECT 
            pa.pokemon_id,
            a.identifier as ability_name,
            a.name as ability_display_name,
            ad.short_effect,
            ad.effect,
            pa.is_hidden,
            pa.slot
        FROM pokemon_abilities pa
        JOIN abilities a ON pa.ability_id = a.id
        LEFT JOIN ability_descriptions ad ON a.id = ad.ability_id;
        
        CREATE VIEW type_effectiveness_view AS
        SELECT 
            dt.identifier as damage_type,
            tt.identifier as target_type,
            te.damage_factor,
            CAST(te.damage_factor AS REAL) / 100.0 as effectiveness
        FROM type_efficacy te
        JOIN types dt ON te.damage_type_id = dt.id
        JOIN types tt ON te.target_type_id = tt.id;
        
        -- Metadata table
        CREATE TABLE database_info (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(schema)
            await db.commit()

    # Populate all tables with CSV data
    async def _populate_all_tables(self, csv_files: Dict[str, Path]) -> None:   
        async with aiosqlite.connect(self.db_path) as db:   
            await self._populate_stats(db, csv_files.get("stats"))
            await self._populate_types(db, csv_files.get("types"))
            await self._populate_abilities(db, csv_files.get("abilities"))
            await self._populate_ability_descriptions(db, csv_files.get("ability_prose"))
            await self._populate_move_damage_classes(db, csv_files.get("move_damage_classes"))
            await self._populate_move_effects(db, csv_files.get("move_effects"))
            await self._populate_move_effect_descriptions(db, csv_files.get("move_effect_prose"))
            await self._populate_version_groups(db, csv_files.get("version_groups"))
            await self._populate_pokemon_move_methods(db, csv_files.get("pokemon_move_methods"))
            await self._populate_moves(db, csv_files.get("moves"))

            await self._populate_pokemon_species(db, csv_files.get("pokemon_species"))
            await self._populate_pokemon(db, csv_files.get("pokemon"))
            
            # Relationship tables
            await self._populate_pokemon_stats(db, csv_files.get("pokemon_stats"))
            await self._populate_pokemon_types(db, csv_files.get("pokemon_types"))
            await self._populate_pokemon_abilities(db, csv_files.get("pokemon_abilities"))
            await self._populate_pokemon_moves(db, csv_files.get("pokemon_moves"))
            await self._populate_type_efficacy(db, csv_files.get("type_efficacy"))
            
            # Evolution table
            await self._populate_evolution_chains(db, csv_files.get("evolution_chains"))
            
            # Metadata
            await db.execute(
                "INSERT OR REPLACE INTO database_info (key, value) VALUES (?, ?)",
                ("last_updated", datetime.now().isoformat())
            )
            await db.execute(
                "INSERT OR REPLACE INTO database_info (key, value) VALUES (?, ?)",
                ("version", "2.0")
            )
            await db.execute(
                "INSERT OR REPLACE INTO database_info (key, value) VALUES (?, ?)",
                ("source", "PokeAPI CSV - Fixed Move Structure")
            )
            
            await db.commit()

    # CSV population methods
    async def _populate_csv_table(self, db: aiosqlite.Connection, csv_path: Optional[Path], 
                                 table_name: str, columns: List[str], 
                                 transform_func=None) -> None:  
        if not csv_path or not csv_path.exists():
            logger.warning(f"CSV file not found: {csv_path}")
            return
        
        records = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:  
                if transform_func:
                    row = transform_func(row)

                record = tuple(row.get(col, None) for col in columns)
                records.append(record)
        
        if records:
            placeholders = ','.join(['?' for _ in columns])
            query = f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
            await db.executemany(query, records)
            logger.info(f"Inserted {len(records)} records into {table_name}")

    # Individual table population methods 
    async def _populate_stats(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "stats", ["id", "identifier", "name"])

    async def _populate_types(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "types", ["id", "identifier", "name"])

    async def _populate_abilities(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "abilities", ["id", "identifier", "name"])

    # Populate ability descriptions (English only)
    async def _populate_ability_descriptions(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        """Populate ability descriptions (English only)"""
        if not csv_path or not csv_path.exists():
            return
        
        records = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:  
                if row.get('local_language_id') == '9':
                    records.append((
                        row.get('ability_id'),
                        row.get('short_effect', ''),
                        row.get('effect', '')
                    ))
        
        if records:
            await db.executemany(
                "INSERT OR REPLACE INTO ability_descriptions (ability_id, short_effect, effect) VALUES (?, ?, ?)",
                records
            )
            logger.info(f"Inserted {len(records)} ability descriptions")

    async def _populate_move_damage_classes(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "move_damage_classes", ["id", "identifier", "name"])

    async def _populate_move_effects(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "move_effects", ["id"])

    # Populate move effect descriptions (English only)
    async def _populate_move_effect_descriptions(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        if not csv_path or not csv_path.exists():   
            return
        
        records = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:  
                if row.get('local_language_id') == '9':
                    records.append((
                        row.get('move_effect_id'),
                        9,
                        row.get('short_effect', ''),
                        row.get('effect', '')
                    ))
        
        if records:
            await db.executemany(
                "INSERT OR REPLACE INTO move_effect_descriptions (move_effect_id, local_language_id, short_effect, effect) VALUES (?, ?, ?, ?)",
                records
            )
            logger.info(f"Inserted {len(records)} move effect descriptions")

    async def _populate_version_groups(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "version_groups", ["id", "identifier", "name"])

    async def _populate_pokemon_move_methods(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "pokemon_move_methods", ["id", "identifier", "name"])

    async def _populate_moves(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(
            db, csv_path, "moves",
            ["id", "identifier", "name", "type_id", "power", "pp", "accuracy", "priority", "damage_class_id", "effect_id", "effect_chance"]
        )

    async def _populate_pokemon_species(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        def transform_bool(row):    
            bool_fields = ['is_baby', 'has_gender_differences', 'forms_switchable', 'is_legendary', 'is_mythical']
            for field in bool_fields:
                if field in row and row[field] in ('1', 'true', 'True'):
                    row[field] = True
                elif field in row:
                    row[field] = False
            return row
        
        await self._populate_csv_table(
            db, csv_path, "pokemon_species",
            ["id", "identifier", "generation_id", "evolves_from_species_id", "evolution_chain_id",
             "color_id", "shape_id", "habitat_id", "gender_rate", "capture_rate", "base_happiness",
             "is_baby", "hatch_counter", "has_gender_differences", "growth_rate_id", "forms_switchable",
             "is_legendary", "is_mythical", "species_order", "conquest_order"],
            transform_func=transform_bool
        )

    async def _populate_pokemon(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        def transform_bool(row):
            if 'is_default' in row and row['is_default'] in ('1', 'true', 'True'):
                row['is_default'] = True
            elif 'is_default' in row:
                row['is_default'] = False
            return row
        
        await self._populate_csv_table(
            db, csv_path, "pokemon",
            ["id", "identifier", "species_id", "height", "weight", "base_experience", "pokemon_order", "is_default"],
            transform_func=transform_bool
        )

    async def _populate_pokemon_stats(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "pokemon_stats", ["pokemon_id", "stat_id", "base_stat", "effort"])

    async def _populate_pokemon_types(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "pokemon_types", ["pokemon_id", "type_id", "slot"])

    async def _populate_pokemon_abilities(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        def transform_bool(row):
            if 'is_hidden' in row and row['is_hidden'] in ('1', 'true', 'True'):
                row['is_hidden'] = True
            elif 'is_hidden' in row:
                row['is_hidden'] = False
            return row
        
        await self._populate_csv_table(
            db, csv_path, "pokemon_abilities", 
            ["pokemon_id", "ability_id", "is_hidden", "slot"],
            transform_func=transform_bool
        )

    async def _populate_pokemon_moves(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        """Populate pokemon moves table from CSV"""
        await self._populate_csv_table(
            db, csv_path, "pokemon_moves",
            ["pokemon_id", "version_group_id", "move_id", "pokemon_move_method_id", "level", "move_order"]
        )

    async def _populate_type_efficacy(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "type_efficacy", ["damage_type_id", "target_type_id", "damage_factor"])

    async def _populate_evolution_chains(self, db: aiosqlite.Connection, csv_path: Optional[Path]) -> None:
        await self._populate_csv_table(db, csv_path, "evolution_chains", ["id", "baby_trigger_item_id"])

    # Create indexes for better query performance
    async def _create_indexes(self) -> None:    
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_pokemon_identifier ON pokemon(identifier)",
            "CREATE INDEX IF NOT EXISTS idx_pokemon_species_id ON pokemon(species_id)",
            "CREATE INDEX IF NOT EXISTS idx_pokemon_stats_pokemon_id ON pokemon_stats(pokemon_id)",
            "CREATE INDEX IF NOT EXISTS idx_pokemon_types_pokemon_id ON pokemon_types(pokemon_id)",  
            "CREATE INDEX IF NOT EXISTS idx_pokemon_abilities_pokemon_id ON pokemon_abilities(pokemon_id)",
            "CREATE INDEX IF NOT EXISTS idx_pokemon_moves_pokemon_id ON pokemon_moves(pokemon_id)",
            "CREATE INDEX IF NOT EXISTS idx_pokemon_moves_move_id ON pokemon_moves(move_id)",
            "CREATE INDEX IF NOT EXISTS idx_type_efficacy ON type_efficacy(damage_type_id, target_type_id)",
            "CREATE INDEX IF NOT EXISTS idx_pokemon_species_evolution ON pokemon_species(evolution_chain_id)",
            "CREATE INDEX IF NOT EXISTS idx_moves_type ON moves(type_id)",
            "CREATE INDEX IF NOT EXISTS idx_moves_effect ON moves(effect_id)",
            "CREATE INDEX IF NOT EXISTS idx_move_effects ON move_effect_descriptions(move_effect_id)",
        ]
        
        async with aiosqlite.connect(self.db_path) as db:
            for index_sql in indexes:
                await db.execute(index_sql)
            await db.commit()

class PokemonDatabase:  
    def __init__(self, db_path: str = "data/pokemon.db"):
        self.db_path = db_path
    async def get_move_details(self, move_name: str) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Comprehensive move details query
            cursor = await db.execute("""
                SELECT 
                    m.id, 
                    m.identifier as name, 
                    t.identifier as type_name,
                    m.power,
                    m.accuracy,
                    m.pp,
                    mdc.identifier as damage_class,
                    m.effect_chance,
                    med.short_effect
                FROM moves m
                JOIN types t ON m.type_id = t.id
                JOIN move_damage_classes mdc ON m.damage_class_id = mdc.id
                LEFT JOIN move_effect_descriptions med ON m.effect_id = med.move_effect_id
                WHERE LOWER(m.identifier) = LOWER(?)
            """, (move_name,))
            
            move_row = await cursor.fetchone()
            
            if not move_row:
                return None

            return {
                'move': {
                    'name': move_row['name'],
                    'type': {'name': move_row['type_name']},
                    'power': move_row['power'],
                    'accuracy': move_row['accuracy'],
                    'pp': move_row['pp'],
                    'movedamageclass': {'name': move_row['damage_class']},
                    'move_effect_chance': move_row['effect_chance'],
                    'moveeffect': {
                        'moveeffecteffecttexts': [
                            {'short_effect': move_row['short_effect']}
                        ] if move_row['short_effect'] else []
                    }
                }
            }
    async def get_pokemon_by_name(self, name: str) -> Optional[Dict[str, Any]]: 
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get basic Pokemon info
            cursor = await db.execute(
                """SELECT pc.*, t1.type_name as primary_type, t2.type_name as secondary_type
                   FROM (
                       SELECT p.*, ps.is_legendary, ps.is_mythical, ps.generation_id, ps.evolution_chain_id, ps.evolves_from_species_id
                       FROM pokemon p
                       JOIN pokemon_species ps ON p.species_id = ps.id
                   ) pc
                   LEFT JOIN pokemon_types_view t1 ON pc.id = t1.pokemon_id AND t1.slot = 1
                   LEFT JOIN pokemon_types_view t2 ON pc.id = t2.pokemon_id AND t2.slot = 2
                   WHERE LOWER(pc.identifier) = LOWER(?)""",
                (name,)
            )
            pokemon = await cursor.fetchone()
            if not pokemon:
                return None
            
            pokemon_id = pokemon["id"]
            result = dict(pokemon)  
            result["species_id"] = pokemon["species_id"]
            cursor = await db.execute(  
                """
                SELECT id, identifier, evolves_from_species_id
                FROM pokemon_species
                WHERE evolution_chain_id = ?
                ORDER BY id ASC
                """,
                (result.get("evolution_chain_id"),)
            )
            result["evolution_chain_species"] = [dict(row) for row in await cursor.fetchall()]

            # Get stats
            cursor = await db.execute(
                "SELECT stat_name, base_stat FROM pokemon_stats_view WHERE pokemon_id = ?",
                (pokemon_id,)
            )
            result["stats"] = {row["stat_name"]: row["base_stat"] for row in await cursor.fetchall()}
            
            # Get types
            types = [result["primary_type"]] if result["primary_type"] else []
            if result["secondary_type"]:
                types.append(result["secondary_type"])
            result["types"] = types
            
            # Get abilities  
            cursor = await db.execute(
                "SELECT * FROM pokemon_abilities_view WHERE pokemon_id = ? ORDER BY slot",
                (pokemon_id,)
            )
            result["abilities"] = [dict(row) for row in await cursor.fetchall()]
            
            # Get moves
            cursor = await db.execute(
                """SELECT DISTINCT 
                          m.id as move_id,
                          m.identifier as move_name, 
                          m.power, 
                          m.accuracy, 
                          m.effect_chance,
                          t.identifier as type_name, 
                          mdc.identifier as damage_class,
                          COALESCE(med.short_effect, '') as short_effect,
                          pm.level
                   FROM pokemon_moves pm
                   JOIN moves m ON pm.move_id = m.id
                   JOIN types t ON m.type_id = t.id  
                   JOIN move_damage_classes mdc ON m.damage_class_id = mdc.id
                   LEFT JOIN move_effect_descriptions med ON m.effect_id = med.move_effect_id AND med.local_language_id = 9
                   WHERE pm.pokemon_id = ? AND pm.pokemon_move_method_id = 1
                   ORDER BY pm.level, m.identifier
                   LIMIT 20""",
                (pokemon_id,)
            )
            moves_data = await cursor.fetchall()

            result["moves"] = []
            for move in moves_data:
                move_dict = {
                    "move": {
                        "id": move["move_id"],
                        "name": move["move_name"],
                        "power": move["power"],
                        "accuracy": move["accuracy"],
                        "move_effect_chance": move["effect_chance"],
                        "movedamageclass": {
                            "name": move["damage_class"]
                        },
                        "type": {
                            "name": move["type_name"]
                        },
                        "moveeffect": {
                            "moveeffecteffecttexts": [
                                {
                                    "short_effect": move["short_effect"]
                                }
                            ] if move["short_effect"] else []
                        }
                    }
                }
                result["moves"].append(move_dict)
            
            return result
    
    # Calculate type effectiveness multiplier
    async def get_type_effectiveness(self, attacking_type: str, defending_types: List[str]) -> float:   
        total_effectiveness = 1.0
        
        async with aiosqlite.connect(self.db_path) as db:
            for defending_type in defending_types:
                cursor = await db.execute(
                    "SELECT effectiveness FROM type_effectiveness_view WHERE damage_type = ? AND target_type = ?",
                    (attacking_type, defending_type)
                )
                row = await cursor.fetchone()
                if row:
                    total_effectiveness *= row[0]
        
        return total_effectiveness
    
    # Get Pokemon's best moves for battle (highest power, diverse types)
    async def get_pokemon_moves_for_battle(self, pokemon_name: str, limit: int = 4) -> List[Dict]:  
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get pokemon_id
            cursor = await db.execute(
                "SELECT id FROM pokemon WHERE LOWER(identifier) = LOWER(?)",
                (pokemon_name,)
            )
            pokemon_row = await cursor.fetchone()
            if not pokemon_row:
                return []
            
            # Get diverse, powerful moves
            cursor = await db.execute(
                """SELECT DISTINCT 
                          m.id as move_id,
                          m.identifier as move_name, 
                          m.power, 
                          m.accuracy, 
                          m.pp,
                          t.identifier as type_name, 
                          mdc.identifier as damage_class,
                          COALESCE(med.short_effect, '') as short_effect, 
                          m.priority
                   FROM pokemon_moves pm
                   JOIN moves m ON pm.move_id = m.id
                   JOIN types t ON m.type_id = t.id
                   JOIN move_damage_classes mdc ON m.damage_class_id = mdc.id
                   LEFT JOIN move_effect_descriptions med ON m.effect_id = med.move_effect_id AND med.local_language_id = 9
                   WHERE pm.pokemon_id = ? AND m.power IS NOT NULL AND m.power > 0
                   ORDER BY m.power DESC, m.accuracy DESC
                   LIMIT ?""",
                (pokemon_row["id"], limit * 2) 
            )
            all_moves = [dict(row) for row in await cursor.fetchall()]
            
            # Select diverse moves (different types/damage classes)
            selected_moves = []
            seen_types = set()
            seen_classes = set()
            
            for move in all_moves:
                move_type = move["type_name"]
                damage_class = move["damage_class"]

                is_new_type = move_type not in seen_types
                is_new_class = damage_class not in seen_classes
                
                if (is_new_type or is_new_class) or len(selected_moves) < limit:
                    selected_moves.append(move)
                    seen_types.add(move_type)
                    seen_classes.add(damage_class)
                    
                    if len(selected_moves) >= limit:
                        break
            
            return selected_moves
    
    async def get_all_pokemon_names(self) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:   
            cursor = await db.execute("SELECT identifier FROM pokemon ORDER BY id")
            return [row[0] for row in await cursor.fetchall()]
