# photo_id

## Quizzes

Quizzes are defined with a `.json` file of the following format:

```json
 {
    "start_month" : 2,
    "end_month" : 2,
    "location" : "EC",
    "Notes" : "Around the lodge",
    "basis":  "From this hotspot https://ebird.org/hotspot/L895012",
    "species" : [ // for each species to include at a minimum the common name
        {"comName" : "Azara's Spinetail"},
        // other optional fields include
        {
            "comName" : "American Kestrel",
            "notes" : "displayed in quiz",
            "frequency": 87.62
        }
    ]
 }
```

## Trips

Trips can be defined which can be used to automatically create quizzes.

Trips are defined with a .json file with the following format:

```json
{
    "name": "A name for the trip like Argentina and Chile January 2027",
    "description": "A longer description.",
    "website": "If this is described by a tour website, for example. ",
    "date": "2027-01-22", // The date of the trip
    "location": "AR", // The location (Two letter country or or 5 letter state code )
    "start_month": 1, // The first month of the trip
    "end_month": 2, // ending month. Both used for selecting photos with correct plumage.
    "minimum_frequency": 10.0, // When getting birds from a hotspot, what is the minimum frequency percent in reporting to include
    "itinerary": [
        {
            "day": "0", // one for each day...or could be used for a section
            "Full day title": "Buenos Aires Reserva Ecológica Costanera Sur",
            "Full day description": "Longer description",
            // hotspots to use for birds seen. Either hotspots, mentioned
            // or both are required to create a quiz for the "day"
            "hotspots": [
                {
                    "name": "Reserva Ecológica Costanera Sur",
                    "hotspotId": "https://ebird.org/hotspot/L472208"
                }
            ],
            // birds mentioned in trip advertisement, include even if not
            // reported at minimum frequency in hotspots
            "mentioned": ["Magellanic Penguin", "Dodo"]
        },
        // more days (or sections)
    ]
}
```

Then a generated_quiz will be created for each day that can be used as a quiz

## Have list

Your life list can be downloaded from your eBird account by going to [https://ebird.org/lifelist/], then downloading the list through the “Download (csv)” link near the upper-right corner of the page.

By default, store this at `tests\data\ebird_world_life_list.csv` and it will be used in the quizzes
