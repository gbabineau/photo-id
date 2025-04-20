import json
import os
import photo_id.process_trip as process_trip
import photo_id.process_quiz as process_quiz

import photo_id.get_taxonomy as get_taxonomy

from photo_id.get_ebird_api_key import get_ebird_api_key

if __name__ == "__main__":
    ebird_api_key = get_ebird_api_key()
    ebird_username = os.getenv("EBIRD_USERNAME")
    ebird_password = os.getenv("EBIRD_PASSWORD")
    trip_directory = "trips/panama"
    trip_title = "canopy-the-birds-of-central-panama-darien-lowlands"
    taxonomy = []
    trip_data = process_trip.process_trip(
        f"{trip_directory}/{trip_title}.json",
    )
    trip_data = process_trip.get_ebird_data(
        trip_data, ebird_username, ebird_password
    )
    output_file = f"{trip_directory}/{trip_title}-ITINERARY.json"
    with open(output_file, "wt", encoding="utf-8") as f:
        json.dump(trip_data, f, indent=4)
    print(f"trip data written to {output_file}")

    with open(
        f"{trip_directory}/{trip_title}-ITINERARY.json", "rt", encoding="utf-8"
    ) as file:
        trip_data = json.load(file)

    taxonomy = get_taxonomy.get_taxonomy(ebird_api_key)

    trip_data["itinerary"] = process_trip.add_mentions(
        trip_data["itinerary"], taxonomy
    )

    trip_data["itinerary"] = process_trip.add_taxonomy(
        trip_data["itinerary"], taxonomy
    )
    output_file = f"{trip_directory}/{trip_title}-TAXONOMY.json"
    with open(output_file, "wt", encoding="utf-8") as f:
        json.dump(trip_data, f, indent=4)
    print(f"Itinerary data written to {output_file}")

    trip_data["itinerary"] = process_trip.keep_high_frequency(
        trip_data["itinerary"], 0.1
    )
    output_file = f"{trip_directory}/{trip_title}-HIGH_FREQUENCY.json"

    with open(
        "trips/panama/canopy-the-birds-of-central-panama-darien-lowlandsHIGHFREQUENCY.json",
        "wt",
        encoding="utf-8",
    ) as file:
        json.dump(trip_data, file, indent=4)
    print(f"Itinerary data written to {file}")

    trip_data["itinerary"] = process_trip.sort_species_by_taxonomy(
        trip_data["itinerary"]
    )

    # break this into quizzes by day
    max_size = 30

    quizzes = process_trip.split_quiz(trip_data)

    for quiz in quizzes:
        output_file = (
            f"{trip_directory}/quizzes/{trip_title}-Day-{quiz['day']}.json"
        )
        process_trip.write_quiz_to_file(quiz, output_file)
        if len(quiz["species"]) > max_size:
            process_quiz.split_quiz(output_file, max_size, taxonomy)
