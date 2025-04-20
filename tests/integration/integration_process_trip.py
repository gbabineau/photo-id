import json
import os
import photo_id.process_trip as process_trip
import photo_id.process_quiz as process_quiz

import photo_id.get_taxonomy as get_taxonomy

from photo_id.get_ebird_api_key import get_ebird_api_key

cache_valid = True


class Cache:
    def __init__(self, cache_directory, trip_title, starting_valid=True):
        self.cache_valid = starting_valid
        self.cache_directory = cache_directory
        self.trip_title = trip_title

    def available(self, cache_type) -> dict:
        """
        Check if the cache file is available and return its content if it exists.
        """
        cache_file = os.path.join(
            self.cache_directory, f"{self.trip_title}_{cache_type}.json"
        )
        if cache_valid and os.path.exists(cache_file):
            with open(cache_file, "rt", encoding="utf-8") as input_file:
                return json.load(input_file)
        return {}

    def update(self, cache_type, data) -> None:
        """
        Update the cache file with the given data.
        """
        os.makedirs(self.cache_directory, exist_ok=True)
        cache_file = os.path.join(
            self.cache_directory, f"{self.trip_title}_{cache_type}.json"
        )
        with open(cache_file, "wt", encoding="utf-8") as output_file:
            json.dump(data, output_file, indent=4)
        self.cache_valid = False


if __name__ == "__main__":
    ebird_api_key = get_ebird_api_key()
    ebird_username = os.getenv("EBIRD_USERNAME")
    ebird_password = os.getenv("EBIRD_PASSWORD")
    trip_directory = "trips/panama"
    cache_directory = ".cache"
    trip_title = "canopy-the-birds-of-central-panama-darien-lowlands"
    taxonomy = []
    trip_cache = Cache(cache_directory, trip_title)
    if (trip_data := trip_cache.available("ITINERARY")) == {}:
        trip_data = process_trip.process_trip(
            f"{trip_directory}/{trip_title}.json",
        )

        trip_cache.update("ITINERARY", trip_data)

    if (new_data := trip_cache.available("EBIRD")) == {}:
        trip_data = process_trip.get_ebird_data(
            trip_data, ebird_username, ebird_password
        )
        trip_cache.update("EBIRD", trip_data)
    else:
        trip_data = new_data

    taxonomy = get_taxonomy.get_taxonomy(ebird_api_key)

    trip_data["itinerary"] = process_trip.add_mentions(
        trip_data["itinerary"], taxonomy
    )

    if (new_data := trip_cache.available("TAXONOMY")) == {}:
        trip_data["itinerary"] = process_trip.add_taxonomy(
            trip_data["itinerary"], taxonomy
        )

        trip_cache.update("TAXONOMY", trip_data)
    else:
        trip_data = new_data

    trip_data["itinerary"] = process_trip.keep_high_frequency(
        trip_data["itinerary"], 0.01
    )

    trip_data["itinerary"] = process_trip.sort_species_by_taxonomy(
        trip_data["itinerary"]
    )

    trip_data["itinerary"] = process_trip.remove_species_shared_in_common(
        trip_data["itinerary"]
    )

    # break this into quizzes by day
    max_size = 30

    quizzes = process_trip.split_quiz(trip_data)
    os.makedirs(f"{cache_directory}/quizzes", exist_ok=True)
    for quiz in quizzes:
        output_file = (
            f"{cache_directory}/quizzes/{trip_title}-Day-{quiz['day']}.json"
        )
        process_trip.write_quiz_to_file(quiz, output_file)
        if len(quiz["species"]) > max_size:
            process_quiz.split_quiz(output_file, max_size, taxonomy)
