"""Deterministic importance tiering based on access patterns (Phase 7A Shim)."""

from datetime import datetime, timezone, timedelta

def compute_tier(last_accessed_at: datetime, access_count: int) -> str:
    """Compute tier based on last access time and access count.
    
    HOT: accessed in last 24h or access_count >= 5
    WARM: accessed in last 14 days
    COLD: everything else
    """
    now = datetime.now(timezone.utc)
    if access_count >= 5:
        return "HOT"
    if last_accessed_at:
        time_since_access = now - last_accessed_at
        if time_since_access <= timedelta(hours=24):
            return "HOT"
        elif time_since_access <= timedelta(days=14):
            return "WARM"
    return "COLD"

def _tier_to_importance(tier: str) -> float:
    return {"HOT": 1.0, "WARM": 0.5, "COLD": 0.0}.get(tier, 0.0)

def _importance_to_tier(importance: float) -> str:
    if importance > 0.8:
        return "HOT"
    if importance > 0.3:
        return "WARM"
    return "COLD"

def retier_all(store: "MemoryStore") -> dict:
    """Recompute importance for all rows in the memories table.
    
    Compatibility shim for Phase 5 tests.
    """
    import sys
    try:
        moved = {"HOT": 0, "WARM": 0, "COLD": 0}
        
        mems = store.get_memories()
        for mem in mems:
            last_accessed = None
            if mem.get("last_accessed"):
                last_accessed = datetime.fromisoformat(mem["last_accessed"])
                
            old_imp = mem.get("importance", 1.0)
            old_tier = _importance_to_tier(old_imp)
            
            new_tier = compute_tier(last_accessed, mem.get("reinforcement_count", 0))
            new_imp = _tier_to_importance(new_tier)
            
            if old_tier != new_tier:
                store._conn.execute(
                    "UPDATE memories SET importance = ? WHERE id = ?",
                    (new_imp, mem["id"])
                )
                moved[new_tier] += 1
                
        store._conn.commit()
        return moved
    except Exception as e:
        print(f"[memory] error retiering: {e}", file=sys.stderr)
        return {"HOT": 0, "WARM": 0, "COLD": 0}
