import logging
import asyncio
import os
import sys
import signal
from pathlib import Path
from typing import Optional

# Setup paths and directories FIRST
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
CSV_CACHE_DIR = DATA_DIR / "csv_cache"
DB_PATH = DATA_DIR / "pokemon.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CSV_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Environment setup
os.chdir(PROJECT_ROOT)
os.environ.setdefault("DATABASE_PATH", str(DB_PATH))
os.environ.setdefault("CSV_CACHE_DIR", str(CSV_CACHE_DIR))

# Python path setup for imports
src_path = PROJECT_ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pokemon-server")

# Startup info
logger.info(f"PROJECT_ROOT={PROJECT_ROOT}")
logger.info(f"DATABASE_PATH={DB_PATH}")
logger.info(f"CSV_CACHE_DIR={CSV_CACHE_DIR}")
logger.info(f"CWD={Path.cwd()}")

# Now import MCP after path setup
from mcp.server.fastmcp import FastMCP

# MCP server
mcp = FastMCP("Pokemon Battle Simulation MCP Server")

# Global DB ref for cleanup
_db_ref: Optional[object] = None  

# Clean up resources on shutdown
def _cleanup():     
    global _db_ref
    try:
        if _db_ref is not None: 
            logger.info("Cleaning up database connection...")
    finally:
        _db_ref = None
        logger.info("Cleanup complete.")

def _handle_signal(sig, frame):     
    logger.info(f"Signal {sig} received. Stopping server...")
    _cleanup()
    sys.exit(0)

def register_signal_handlers():     
    try:
        signal.signal(signal.SIGINT, _handle_signal)  
        signal.signal(signal.SIGTERM, _handle_signal)   
    except Exception as e:
        logger.debug(f"Signal handler setup error: {e}")

async def setup_server():   
    global _db_ref
    
    logger.info("Starting Pokemon MCP Server...")

    try:
        # Import modules
        from src.adapters.pokeapi_client import PokemonDatabase, PokemonCSVDatabaseBuilder
        from src.resources.pokemon_resource import PokemonResource
        from src.tools.battle_simulation import BattleSimulationTool

        logger.info("Imports successful")

        # Initialize database if needed
        if not DB_PATH.exists():
            logger.info("Database not found. Building from scratch...")
            builder = PokemonCSVDatabaseBuilder(db_path=str(DB_PATH))
            await builder.build_database(force_rebuild=False)
            logger.info("Database built successfully!")

        # Create database connection
        db = PokemonDatabase(str(DB_PATH))
        _db_ref = db
        logger.info("Database connected")

        # Setup Pokemon resource
        pokemon_resource = PokemonResource(db)
        pokemon_resource.setup_resources(mcp)
        logger.info("Pokemon resource registered")

        # Setup battle simulation tools
        battle_tool = BattleSimulationTool(db)
        battle_tool.setup_tools(mcp)
        logger.info("Battle simulation tools registered")

        logger.info("All tools registered successfully!")
        logger.info("Pokemon Battle Simulation Server ready!")
        return True

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main(): 
    """Main entry point"""
    try:
        logger.info("=== Pokemon Battle Simulation - MCP Server ===")
        
        # Setup server
        success = asyncio.run(setup_server())
        if not success:
            logger.error("Failed to initialize server")
            return 1

        logger.info("Starting MCP server...")
        register_signal_handlers()

        # Start the MCP server
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Stopping server...")
        return 0
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:    
        _cleanup()
        logger.info("Server shut down.")
        return 0

if __name__ == "__main__":  
    try:
        exit_code = main()
        sys.exit(exit_code if isinstance(exit_code, int) else 0)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Error starting server: %s", e)
        sys.exit(1)