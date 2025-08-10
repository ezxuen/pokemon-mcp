import logging
import asyncio
import logging  
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.adapters.pokeapi_client import PokemonCSVDatabaseBuilder

async def main():   
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    builder = PokemonCSVDatabaseBuilder()
    
    logging.info("Building Pokemon database from PokeAPI...")
    logging.info("This will take a few minutes but only needs to be done once!")
    
    try:
        await builder.build_database(force_rebuild=False)
        logging.info("Database built successfully!")
        logging.info(f"Database location: {builder.db_path.absolute()}")
      
    except Exception as e:
        logging.error(f" Failed to build database: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)