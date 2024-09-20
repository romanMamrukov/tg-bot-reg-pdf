import csv
import json
import os
import portalocker
from typing import Optional, List, Dict

GAMES_CSV_FILE = "./store/games.csv"
USER_DATA_FILE = "./store/user_data.json"


def load_json(file_path: str) -> dict:
    """Load JSON data from a file with file locking."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                portalocker.lock(file, portalocker.LOCK_SH)
                data = json.load(file)
                portalocker.unlock(file)
                return data
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_path}")
            return {}
    return {}


def save_json(file_path: str, data: dict) -> None:
    """Save JSON data to a file with file locking."""
    with open(file_path, 'w', encoding='utf-8') as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        json.dump(data, f, ensure_ascii=False, indent=4)
        portalocker.unlock(f)


def load_csv(file_path: str) -> List[Dict[str, str]]:
    """Load CSV data from a file with file locking."""
    if os.path.exists(file_path):
        try:
            with open(file_path, newline='', encoding='utf-8') as file:
                portalocker.lock(file, portalocker.LOCK_SH)
                data = list(csv.DictReader(file))
                portalocker.unlock(file)
                return data
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return []
    return []


def update_game_csv(game_id: str, spots_registered: int) -> None:
    """Update the game CSV with new registration data."""
    rows = load_csv(GAMES_CSV_FILE)
    updated = False
    for row in rows:
        if row['game_id'] == game_id:
            row['spots_registered'] = str(spots_registered)
            row['spots_left'] = str(int(row['spots_all']) - spots_registered)
            updated = True

    if updated:
        try:
            with open(GAMES_CSV_FILE, 'w', newline='',
                      encoding='utf-8') as file:
                portalocker.lock(file, portalocker.LOCK_EX)
                writer = csv.DictWriter(file, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                portalocker.unlock(file)
        except Exception as e:
            print(f"Error updating CSV: {e}")


def store_user_data(user_id: str, user_info: dict) -> None:
    """Store user data in a JSON file."""
    data = load_json(USER_DATA_FILE)
    if user_id not in data:
        data[user_id] = []
    data[user_id].append(user_info)
    save_json(USER_DATA_FILE, data)


def get_user_data(user_id: str) -> List[dict]:
    """Retrieve user data from the JSON file."""
    user_data = load_json(USER_DATA_FILE)
    return user_data.get(user_id, [])


def get_game_info(game_id: str) -> Optional[Dict[str, str]]:
    """Retrieve game information from the CSV file."""
    games = load_csv(GAMES_CSV_FILE)
    for game in games:
        if game['game_id'] == game_id:
            return game
    return None

def cancel_registration_fun(user_id: str, invoice_number: str) -> bool:
    """Cancel a registration based on invoice number."""
    user_data = load_json(USER_DATA_FILE) #Make sure to modify the global variable

    games = load_csv(GAMES_CSV_FILE)

    user_registration = None
    for registration in user_data.get(user_id, []):
        if registration.get('invoice_number') == invoice_number:
            user_registration = registration
            break
    if user_registration:
        # Update user_data with canceled flag
        user_registration['canceled'] = "canceled"

        # Update games.csv if spots were registered
        game_id = user_registration.get('game_details', {}).get('game_id')
        if game_id:
            spots_registered = int(user_registration.get('cust_amount', 0))
            update_game_csv(
                game_id,
                spots_registered=int(games[game_id]['spots_registered']) -
                spots_registered)
        save_json(USER_DATA_FILE, user_data)  # Save user data
        return True
    else:
        return False
