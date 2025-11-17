"""Track transaction lifecycle for debugging"""
from datetime import datetime
from typing import Dict, List
import json

class TransactionTracker:
    """In-memory transaction event tracker"""
    
    def __init__(self):
        self.events: Dict[str, List[Dict]] = {}
    
    def log_event(self, txid: str, event: str, details: Dict = None):
        """Log a transaction event"""
        if txid not in self.events:
            self.events[txid] = []
        
        self.events[txid].append({
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'details': details or {}
        })
    
    def get_history(self, txid: str) -> List[Dict]:
        """Get all events for a transaction"""
        return self.events.get(txid, [])
    
    def export_json(self, txid: str) -> str:
        """Export transaction history as JSON"""
        return json.dumps(self.get_history(txid), indent=2)

# Global tracker instance
tracker = TransactionTracker()
