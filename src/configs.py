import json
import logging

heading = """
# 🚛 GPS records clustering system

👣 User guide:
1. Select a `csv` file with GPS records
2. Upload the file
3. Inspect the results

🚫 Constraints
1. Only include one unique vehicle in a file
2. Do not include any duplicate time-stamps in the GPS records
"""

MAP_HEIGHT = 700


kepler_map_config = None
try:
    with open('config/kepler_map_configuration.json') as f:
        kepler_map_config = json.load(f)
except Exception as exc:
    logging.error(f"Fail to read map config: {exc}")
