from data.symbol_info import SymbolInfo

@router.get("/api/symbols/search")
async def search_symbols(q: str):
    """Search for symbols matching the query."""
    symbol_info = SymbolInfo()
    results = symbol_info.search_symbols(q)
    return {"results": results}

@router.post("/api/symbols/add")
async def add_symbol(symbol: str):
    """Add a symbol to the active watchlist."""
    app = router.app
    success = await app.state.engine.add_symbol(symbol)
    if success:
        # Also add to config for persistence
        if symbol not in app.state.config['symbols']:
            app.state.config['symbols'].append(symbol)
            with open('config.json', 'w') as f:
                json.dump(app.state.config, f, indent=4)
        return {"status": "added", "symbol": symbol}
    return {"status": "failed", "symbol": symbol}

@router.delete("/api/symbols/remove")
async def remove_symbol(symbol: str):
    app = router.app
    success = await app.state.engine.remove_symbol(symbol)
    if success:
        if symbol in app.state.config['symbols']:
            app.state.config['symbols'].remove(symbol)
            with open('config.json', 'w') as f:
                json.dump(app.state.config, f, indent=4)
        return {"status": "removed", "symbol": symbol}
    return {"status": "failed", "symbol": symbol}
