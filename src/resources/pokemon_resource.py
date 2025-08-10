from mcp.server.fastmcp import FastMCP 
from mcp.types import TextResourceContents
from src.adapters.pokeapi_client import PokemonDatabase
import json

def _strip_ids(obj, keep=("evolves_from_species_id",)):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "id" and k not in keep:
                continue
            out[k] = _strip_ids(v, keep)
        return out
    if isinstance(obj, list):
        return [_strip_ids(x, keep) for x in obj]
    return obj

class PokemonResource:

    def __init__(self, db: PokemonDatabase):
        self.db = db

    async def build_response(self, name: str, include_ids: bool = False) -> dict:
        data = await self.db.get_pokemon_by_name(name.lower())
        if not data:
            return {"error": f"Pokemon not found: {name}"}

        payload = {
            "data": {
                "pokemon": [
                    {
                        "name": data["identifier"],
                        "pokemonstats": [
                            {"base_stat": data["stats"].get("hp", 0), "stat": {"name": "hp"}},
                            {"base_stat": data["stats"].get("attack", 0), "stat": {"name": "attack"}},
                            {"base_stat": data["stats"].get("defense", 0), "stat": {"name": "defense"}},
                            {"base_stat": data["stats"].get("special-attack", 0), "stat": {"name": "special-attack"}},
                            {"base_stat": data["stats"].get("special-defense", 0), "stat": {"name": "special-defense"}},
                            {"base_stat": data["stats"].get("speed", 0), "stat": {"name": "speed"}},
                        ],
                        "pokemontypes": [{"type": {"name": t}} for t in data.get("types", [])],
                        "pokemonabilities": [
                            {
                                "is_hidden": bool(a.get("is_hidden", False)),
                                "slot": a.get("slot", 1),
                                "ability": {
                                    "name": a.get("ability_name", ""),
                                    "abilityeffecttexts": (
                                        [{"short_effect": a.get("short_effect", "")}]
                                        if a.get("short_effect") else []
                                    ),
                                },
                            }
                            for a in data.get("abilities", [])
                        ],
                        "pokemonmoves": data.get("moves", []),

                        # Evolution/species section
                        "pokemonspecy": {
                            "id": data.get("species_id"), 
                            "name": data["identifier"],
                            "evolves_from_species_id": data.get("evolves_from_species_id"),
                            "evolutionchain": {
                                "id": data.get("evolution_chain_id"),
                                "pokemonspecies": [
                                    {
                                        "id": s["id"],  
                                        "name": s["identifier"],
                                        "evolves_from_species_id": s["evolves_from_species_id"],
                                    }
                                    for s in (data.get("evolution_chain_species") or [])
                                ],
                            },
                        },
                    }
                ]
            }
        }


        return payload if include_ids else _strip_ids(payload)

    def setup_resources(self, mcp: FastMCP):
        @mcp.resource(
            "pokemon://info/{name}",
            title="Pokemon Info",
            description="Returns structured JSON for a single Pokemon: stats, types, abilities, moves, and evolution."
        )
        async def pokemon_info_resource(name: str) -> TextResourceContents:
            body = await self.build_response(name, include_ids=False)
            return TextResourceContents(
                text=json.dumps(body, indent=2),
                mimeType="application/json"
            )

        # Tool wrapper
        @mcp.tool()
        async def get_pokemon_info(name: str) -> dict:
            return await self.build_response(name, include_ids=False)