import datetime
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from photo_id import process_trip


class TestProcessTrip(unittest.TestCase):
    def test_process_trip_reads_valid_json(self):
        trip_data = {"itinerary": [{"day": 1}]}
        with tempfile.TemporaryDirectory() as directory:
            trip_file = pathlib.Path(directory) / "trip.json"
            trip_file.write_text(json.dumps(trip_data), encoding="utf-8")

            self.assertEqual(
                process_trip.process_trip(str(trip_file)), trip_data
            )

    def test_process_trip_missing_file_exits(self):
        with self.assertLogs("root", level="ERROR"):
            with self.assertRaises(SystemExit) as error:
                process_trip.process_trip("missing-trip.json")
        self.assertEqual(error.exception.code, 1)

    def test_process_trip_invalid_json_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            trip_file = pathlib.Path(directory) / "trip.json"
            trip_file.write_text("{invalid", encoding="utf-8")

            with self.assertLogs("root", level="ERROR"):
                with self.assertRaises(SystemExit) as error:
                    process_trip.process_trip(str(trip_file))
        self.assertEqual(error.exception.code, 1)

    def test_process_trip_rejects_data_without_itinerary(self):
        with tempfile.TemporaryDirectory() as directory:
            trip_file = pathlib.Path(directory) / "trip.json"
            trip_file.write_text('{"name": "Trip"}', encoding="utf-8")

            with self.assertLogs("root", level="ERROR"):
                with self.assertRaises(SystemExit) as error:
                    process_trip.process_trip(str(trip_file))
        self.assertEqual(error.exception.code, 1)

    def test_process_trip_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as directory:
            trip_file = pathlib.Path(directory) / "trip.json"
            trip_file.write_text("[]", encoding="utf-8")

            with self.assertLogs("root", level="ERROR"):
                with self.assertRaises(SystemExit) as error:
                    process_trip.process_trip(str(trip_file))
        self.assertEqual(error.exception.code, 1)


class TestHotspotSpecies(unittest.TestCase):
    def test_update_species_frequency_filters_below_minimum(self):
        hotspot_species = []
        process_trip.update_species_frequency(
            {"comName": "Species A", "frequency": 9.9},
            {"minimum_frequency": 10},
            hotspot_species,
        )
        self.assertEqual(hotspot_species, [])

    def test_update_species_frequency_adds_and_accumulates(self):
        hotspot_species = []
        trip_data = {"minimum_frequency": 10}
        process_trip.update_species_frequency(
            {"comName": "Species A", "frequency": 10},
            trip_data,
            hotspot_species,
        )
        process_trip.update_species_frequency(
            {"comName": "Species A", "frequency": 20},
            trip_data,
            hotspot_species,
        )
        self.assertEqual(
            hotspot_species,
            [{"comName": "Species A", "frequency": [10, 20]}],
        )

    @mock.patch("photo_id.process_trip.get_cached_species_from_hotspot_website")
    def test_get_hotspot_species_averages_frequency(self, mock_get_species):
        mock_get_species.side_effect = [
            [{"comName": "Species A", "frequency": 10}],
            [
                {"comName": "Species A", "frequency": 20},
                {"comName": "Species B", "frequency": 5},
            ],
        ]
        result = process_trip.get_hotspot_species(
            [
                {"name": "First", "hotspotId": "L1"},
                {"name": "Second", "hotspotId": "L2"},
            ],
            {"start_month": 1, "end_month": 12, "minimum_frequency": 5},
            "cache",
            "user",
            "password",
        )
        self.assertEqual(
            result,
            [
                {"comName": "Species A", "frequency": 15.0},
                {"comName": "Species B", "frequency": 5.0},
            ],
        )
        self.assertEqual(mock_get_species.call_count, 2)

    @mock.patch("photo_id.process_trip.webdriver.Chrome")
    def test_get_species_from_hotspot_website_parses_results(self, mock_chrome):
        driver = mock_chrome.return_value
        driver.page_source = """
            <ul>
              <li class="ResultsStats ResultsStats--action ResultsStats--toEdge">
                <div class="ResultsStats-title">Species A Exotic</div>
                <div class="ResultsStats-stats">12.5%</div>
              </li>
            </ul>
        """
        result = process_trip.get_species_from_hotspot_website(
            "Hotspot Name", "L123", "user", "password", 3, 9
        )

        self.assertEqual(result, [{"comName": "Species A", "frequency": 12.5}])
        driver.get.assert_called_once_with(
            "https://ebird.org/targets?r1=L123&bmo=3&emo=9&r2=L123&t2=year&mediaType="
        )
        driver.find_element.assert_any_call("id", "input-user-name")
        driver.find_element.assert_any_call("id", "input-password")
        driver.find_element.assert_any_call("id", "form-submit")
        driver.quit.assert_called_once()

    @mock.patch("photo_id.process_trip.webdriver.Chrome")
    def test_get_species_from_hotspot_website_quits_when_no_results(
        self, mock_chrome
    ):
        driver = mock_chrome.return_value
        driver.page_source = "<html></html>"
        result = process_trip.get_species_from_hotspot_website(
            "Hotspot Name", "L123", "user", "password", 3, 9
        )
        self.assertEqual(result, [])
        driver.save_screenshot.assert_called_once_with("no_species_found.png")
        driver.quit.assert_called_once()


class TestHotspotCache(unittest.TestCase):
    @mock.patch("photo_id.process_trip.get_species_from_hotspot_website")
    def test_cached_species_retries_until_species_are_found(self, mock_fetch):
        mock_fetch.side_effect = [
            [],
            [{"comName": "Species A", "frequency": 5}],
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = process_trip.get_cached_species_from_hotspot_website(
                directory, "Hotspot", "region-L123", "user", "password", 1, 2
            )
            cache_file = pathlib.Path(directory) / "hotspots" / "L123.json"
            self.assertEqual(result, [{"comName": "Species A", "frequency": 5}])
            self.assertEqual(
                json.loads(cache_file.read_text(encoding="utf-8")), result
            )
        self.assertEqual(mock_fetch.call_count, 2)

    @mock.patch("photo_id.process_trip.get_species_from_hotspot_website")
    def test_cached_species_reads_existing_cache(self, mock_fetch):
        with tempfile.TemporaryDirectory() as directory:
            cache_directory = pathlib.Path(directory) / "hotspots"
            cache_directory.mkdir()
            cache_file = cache_directory / "L123.json"
            expected = [{"comName": "Species A", "frequency": 5}]
            cache_file.write_text(json.dumps(expected), encoding="utf-8")

            result = process_trip.get_cached_species_from_hotspot_website(
                directory, "Hotspot", "L123", "user", "password", 1, 2
            )

        self.assertEqual(result, expected)
        mock_fetch.assert_not_called()


class TestTripTransformations(unittest.TestCase):
    def test_get_file_modification_time_returns_iso_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = pathlib.Path(directory) / "trip.json"
            file_path.write_text("{}", encoding="utf-8")
            expected = datetime.datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat(sep=" ", timespec="seconds")
            self.assertEqual(
                process_trip.get_file_modification_time(file_path), expected
            )

    def test_get_file_modification_time_returns_empty_for_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = pathlib.Path(directory) / "missing.json"
            with self.assertLogs("root", level="WARNING"):
                self.assertEqual(
                    process_trip.get_file_modification_time(file_path), ""
                )

    def test_get_ebird_data_builds_result_and_adds_species(self):
        trip_data = {
            "name": "Trip",
            "location": "Region",
            "description": "Description",
            "website": "https://example.test",
            "date": "2026-01-01",
            "start_month": 1,
            "end_month": 2,
            "itinerary": [{"day": 1, "hotspots": []}],
        }
        expected = {
            "name": "Trip",
            "location": "Region",
            "description": "Description",
            "website": "https://example.test",
            "date": "2026-01-01",
            "start_month": 1,
            "end_month": 2,
            "minimum_frequency": 0.0,
            "itinerary": [{"day": 1, "hotspots": [], "hotspot species": []}],
        }
        with mock.patch(
            "photo_id.process_trip.get_hotspot_species", return_value=[]
        ) as mock_get_species:
            result = process_trip.get_ebird_data(
                trip_data, "user", "password", "cache"
            )
        self.assertEqual(result, expected)
        mock_get_species.assert_called_once()

    def test_add_taxonomy_only_adds_missing_fields(self):
        trip_data = [
            {"hotspot species": [{"comName": "Species A", "frequency": 25}]}
        ]
        taxonomy = [
            {
                "comName": "Species A",
                "taxonOrder": 10,
                "sciName": "Species alpha",
            }
        ]
        result = process_trip.add_taxonomy(trip_data, taxonomy)
        self.assertEqual(
            result[0]["hotspot species"][0],
            {
                "comName": "Species A",
                "frequency": 25,
                "taxonOrder": 10,
                "sciName": "Species alpha",
            },
        )

    def test_add_mentions_adds_taxonomy_matched_species_once(self):
        trip_data = [
            {
                "mentioned": ["Species A", "Species A"],
                "hotspot species": [{"comName": "Species A", "frequency": 25}],
            }
        ]
        result = process_trip.add_mentions(
            trip_data, [{"comName": "Species A", "taxonOrder": 1}]
        )
        self.assertEqual(
            result[0]["hotspot species"],
            [
                {
                    "comName": "Species A",
                    "frequency": 25,
                    "notes": "Mentioned in trip data",
                }
            ],
        )

    def test_add_mentions_warns_for_unknown_taxon(self):
        trip_data = [{"mentioned": ["Unknown"], "hotspot species": []}]
        with self.assertLogs("root", level="WARNING"):
            result = process_trip.add_mentions(trip_data, [])
        self.assertEqual(result[0]["hotspot species"], [])

    def test_keep_high_frequency_keeps_mentioned_species(self):
        trip_data = [
            {
                "hotspot species": [
                    {"comName": "Common", "frequency": 1},
                    {"comName": "Rare", "frequency": 0.99},
                    {"comName": "Mentioned", "notes": "Mentioned in trip data"},
                ]
            }
        ]
        result = process_trip.keep_high_frequency(trip_data, 0.01)
        self.assertEqual(
            [species["comName"] for species in result[0]["hotspot species"]],
            ["Common", "Mentioned"],
        )

    def test_sort_species_by_taxonomy_sorts_missing_orders_first(self):
        trip_data = [
            {
                "hotspot species": [
                    {"comName": "Second", "taxonOrder": 2},
                    {"comName": "Unranked"},
                    {"comName": "First", "taxonOrder": 1},
                ]
            }
        ]
        result = process_trip.sort_species_by_taxonomy(trip_data)
        self.assertEqual(
            [species["comName"] for species in result[0]["hotspot species"]],
            ["Unranked", "First", "Second"],
        )

    def test_split_trip_uses_trip_defaults_and_day_notes(self):
        trip_data = {
            "location": "Region",
            "start_month": 4,
            "end_month": 6,
            "itinerary": [
                {
                    "day": 2,
                    "AM_title": "Morning walk",
                    "PM_title": "Evening watch",
                    "hotspot species": [{"comName": "Species A"}],
                }
            ],
        }
        self.assertEqual(
            process_trip.split_trip(trip_data),
            [
                {
                    "start_month": 4,
                    "end_month": 6,
                    "location": "Region",
                    "basis": "Trip data automatically generated from trip file",
                    "species": [{"comName": "Species A"}],
                    "day": 2,
                    "notes": "Morning: Morning walk. Afternoon: Evening watch",
                }
            ],
        )

    def test_split_trip_falls_back_to_day_values_and_full_day_title(self):
        trip_data = {
            "start_month": None,
            "end_month": None,
            "itinerary": [
                {
                    "start_month": 8,
                    "end_month": 9,
                    "location": "Day location",
                    "Full day title": "All-day survey",
                    "hotspot species": [],
                }
            ],
        }
        quiz = process_trip.split_trip(trip_data)[0]
        self.assertEqual(quiz["start_month"], 8)
        self.assertEqual(quiz["end_month"], 9)
        self.assertEqual(quiz["location"], "Day location")
        self.assertEqual(quiz["day"], 1)
        self.assertEqual(quiz["notes"], "Full: All-day survey.")

    def test_remove_species_shared_in_common_keeps_higher_frequency(self):
        trip_data = [
            {
                "hotspot species": [
                    {"comName": "Shared", "frequency": 20},
                    {"comName": "First only", "frequency": 5},
                ]
            },
            {
                "hotspot species": [
                    {"comName": "Shared", "frequency": 10},
                    {"comName": "Second only", "frequency": 5},
                ]
            },
        ]
        result = process_trip.remove_species_shared_in_common(trip_data)
        self.assertEqual(
            [species["comName"] for species in result[0]["hotspot species"]],
            ["Shared", "First only"],
        )
        self.assertEqual(
            [species["comName"] for species in result[1]["hotspot species"]],
            ["Second only"],
        )

    def test_remove_shared_species_prefers_trip_mention(self):
        trip_data = [
            {"hotspot species": [{"comName": "Shared", "frequency": 20}]},
            {
                "hotspot species": [
                    {
                        "comName": "Shared",
                        "notes": "Mentioned in trip data",
                    }
                ]
            },
        ]
        result = process_trip.remove_species_shared_in_common(trip_data)
        self.assertEqual(result[0]["hotspot species"], [])
        self.assertEqual(len(result[1]["hotspot species"]), 1)


class TestTripCache(unittest.TestCase):
    def test_update_writes_json_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = process_trip.Cache(directory, "Trip", "2026-01-01 00:00:00")
            cache.update("ITINERARY", {"itinerary": []})
            cache_file = pathlib.Path(directory) / "Trip_ITINERARY.json"
            self.assertTrue(cache_file.exists())
            self.assertEqual(
                json.loads(cache_file.read_text(encoding="utf-8")),
                {"itinerary": []},
            )
            self.assertFalse(cache.cache_valid)

    def test_available_reads_current_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_file = pathlib.Path(directory) / "Trip_EBIRD.json"
            expected = {"itinerary": []}
            cache_file.write_text(json.dumps(expected), encoding="utf-8")
            cache = process_trip.Cache(directory, "Trip", "2000-01-01 00:00:00")
            self.assertEqual(cache.available("EBIRD"), expected)

    @mock.patch("photo_id.process_trip.get_file_modification_time")
    def test_available_removes_stale_cache(self, mock_mtime):
        mock_mtime.return_value = "2000-01-01 00:00:00"
        with tempfile.TemporaryDirectory() as directory:
            cache_file = pathlib.Path(directory) / "Trip_EBIRD.json"
            cache_file.write_text("{}", encoding="utf-8")
            cache = process_trip.Cache(directory, "Trip", "2026-01-01 00:00:00")
            self.assertEqual(cache.available("EBIRD"), {})
            self.assertFalse(cache_file.exists())


if __name__ == "__main__":
    unittest.main()
