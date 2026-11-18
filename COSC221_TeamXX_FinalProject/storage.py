"""
storage.py - reading and writing our data files.

    cars.csv       the list of cars (read only)
    bookings.json  all bookings (read at start, saved after every change)

Nothing here talks to the user directly. Each load function gives back the
data plus a message (or None) so the menu can decide how to show it.
"""

import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from rental import Booking, Car


def load_cars(path):
    """Read cars.csv. Returns (cars_dict, message)."""
    path = Path(path)
    if not path.exists():
        return {}, f"Car list not found ({path.name}). New bookings are turned off until it's added."

    cars, skipped = {}, 0
    try:
        with open(path, newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                try:
                    car = Car(
                        car_id=row["car_id"].strip().upper(),
                        brand=row["brand"].strip(),
                        model=row["model"].strip(),
                        car_type=row["type"].strip(),
                        plate=row["plate"].strip().upper(),
                        daily_rate=int(row["daily_rate"]),
                        image=(row.get("image") or "").strip(),
                    )
                    if not car.car_id or car.daily_rate <= 0:
                        raise ValueError
                    cars[car.car_id] = car
                except (KeyError, ValueError, AttributeError, TypeError):
                    skipped += 1        # one bad row shouldn't stop the whole list
    except (OSError, csv.Error, UnicodeDecodeError) as error:
        return {}, f"Couldn't read {path.name}: {error}"

    if not cars:
        return {}, f"{path.name} has no valid cars. New bookings are turned off."
    if skipped:
        return cars, f"Skipped {skipped} row(s) in {path.name} with missing or invalid values."
    return cars, None


def load_bookings(path):
    """Read bookings.json. Returns (bookings_dict, message).

    Missing file  -> start with no bookings.
    Damaged file  -> keep a backup copy, warn the user, start with no bookings.
                     The original data is never lost.
    """
    path = Path(path)
    if not path.exists():
        return {}, f"No {path.name} found, so we're starting with an empty booking log."

    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("the file should contain one JSON object")
        bookings = {}
        for item in data.values():
            booking = Booking.from_dict(item)
            bookings[booking.booking_id] = booking
        return bookings, None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError, TypeError) as error:
        backup = path.with_name(f"{path.stem}_damaged_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
        shutil.copy2(path, backup)
        return {}, (f"{path.name} is damaged ({error}). A copy was kept as {backup.name}, "
                    "so nothing is lost. Starting with an empty log for now.")
    except OSError as error:
        return {}, f"Couldn't open {path.name}: {error}"


def save_bookings(bookings, path):
    """Write every booking to bookings.json.

    We write to a temporary file first and then swap it in, so if the program
    stops halfway through saving, the old file is still fine."""
    path = Path(path)
    data = {booking_id: bookings[booking_id].to_dict() for booking_id in sorted(bookings)}
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)
