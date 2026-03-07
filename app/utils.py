import logging
import json
from datetime import datetime
from typing import Any, Dict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('social_pilot.log')
    ]
)

logger = logging.getLogger("SocialPilot")

def log_agent_action(agent_name: str, action: str, details: Any):
    logger.info(f"[{agent_name}] {action}: {json.dumps(details, indent=2) if isinstance(details, (dict, list)) else details}")

def format_timestamp(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def save_result_to_file(client_id: str, result_type: str, data: Dict[str, Any]):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/{client_id}_{result_type}_{timestamp}.json"
    
    os.makedirs("results", exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    
    logger.info(f"Result saved to {filename}")

import os
