import unittest
from unittest.mock import MagicMock, patch

import requests

from photo_id.match_window import (
    MatchWindow,
    SpeciesFrame,
    VerticalScrolledFrame,
    web_browser_callback,
)


class TestVerticalScrolledFrame(unittest.TestCase):
    @patch("photo_id.match_window.ttk.Frame")
    @patch("photo_id.match_window.Scrollbar")
    @patch("photo_id.match_window.Canvas")
    def setUp(self, mock_canvas, mock_scrollbar, mock_frame):
        self.mock_canvas = mock_canvas
        self.mock_scrollbar = mock_scrollbar
        self.mock_frame = mock_frame

        self.parent = MagicMock()
        self.vs_frame = VerticalScrolledFrame(self.parent)

    def test_initialization(self):
        self.mock_frame.assert_called_once()
        self.mock_scrollbar.assert_called_once_with(
            self.vs_frame, orient="vertical"
        )
        self.mock_canvas.assert_called_once_with(
            self.vs_frame,
            bd=0,
            highlightthickness=0,
            yscrollcommand=self.mock_scrollbar.return_value.set,
        )

    def test_scrollbar_configuration(self):
        canvas = self.mock_canvas.return_value
        scrollbar = self.mock_scrollbar.return_value
        scrollbar.pack.assert_called_once_with(
            fill="y", side="right", expand=False
        )
        canvas.pack.assert_called_once_with(
            side="left", fill="both", expand=True
        )
        scrollbar.config.assert_called_once_with(command=canvas.yview)

    def test_canvas_configuration(self):
        canvas = self.mock_canvas.return_value
        canvas.xview_moveto.assert_called_once_with(0)
        canvas.yview_moveto.assert_called_once_with(0)

    def test_interior_frame_configuration(self):
        canvas = self.mock_canvas.return_value
        canvas.create_window.assert_called_once_with(
            0, 0, window=unittest.mock.ANY, anchor="nw"
        )

    def test_resize_callbacks_update_canvas_and_interior(self):
        canvas = self.mock_canvas.return_value
        interior = self.vs_frame.interior
        interior.winfo_reqwidth.return_value = 200
        interior.winfo_reqheight.return_value = 300
        canvas.winfo_width.return_value = 100
        interior_configure = getattr(interior.bind, "call_args").args[1]
        canvas_configure = canvas.bind.call_args.args[1]

        interior_configure(None)
        canvas_configure(None)

        canvas.config.assert_any_call(scrollregion="0 0 200 300")
        canvas.config.assert_any_call(width=200)
        canvas.itemconfigure.assert_called_once_with(
            canvas.create_window.return_value, width=100
        )


class TestWebBrowserCallback(unittest.TestCase):
    @patch("photo_id.match_window.webbrowser.open_new")
    def test_web_browser_callback(self, mock_open_new):
        url = "http://example.com"
        web_browser_callback(url)
        mock_open_new.assert_called_once_with(url)


class TestSpeciesFrame(unittest.TestCase):
    @patch("photo_id.match_window.Image.open")
    @patch("photo_id.match_window.requests.get")
    @patch("photo_id.match_window.StringVar")
    @patch("photo_id.match_window.Label")
    @patch("photo_id.match_window.Scrollbar")
    @patch("photo_id.match_window.Button")
    @patch("photo_id.match_window.ttk.Combobox")
    def setUp(
        self,
        #        mock_update,
        mock_combo,
        mock_button,
        mock_scrollbar,
        mock_label,
        mock_stringvar,
        mock_requests_get,
        mock_image_open,
    ):
        self.mock_requests_get = mock_requests_get
        self.mock_image_open = mock_image_open

        self.base = MagicMock()
        self.species_number = 0
        self.large_species_list = [
            {
                "speciesCode": "comchi1",
                "comName": "Common Chiffchaff",
                "frequency": 10,
                "notes": "A small bird",
            }
        ]
        self.location = "NO"
        self.start_month = "6"
        self.end_month = "8"
        self.image_width = 300
        self.life_list = True
        with (
            patch(
                "photo_id.match_window.VerticalScrolledFrame"
            ) as mock_vsframe,
            patch.object(SpeciesFrame, "update_image") as mock_update,
        ):
            mock_vsframe.tk = MagicMock()
            self.sf = SpeciesFrame(
                self.base,
                self.species_number,
                self.large_species_list,
                self.location,
                self.start_month,
                self.end_month,
                self.image_width,
                self.life_list,
            )
            self.assertEqual(mock_button.call_count, 2)
            self.assertEqual(mock_label.call_count, 5)
            mock_update.assert_called_once()

    def test_initialization(self):
        self.assertEqual(self.sf.species_code, "comchi1")
        self.assertEqual(self.sf.species_name, "Common Chiffchaff")
        self.assertEqual(self.sf.location, "NO")
        self.assertEqual(self.sf.start_month, "6")
        self.assertEqual(self.sf.end_month, "8")
        self.assertEqual(self.sf.image_width, 300)
        self.assertTrue(self.life_list)

    @patch("photo_id.match_window.ImageTk.PhotoImage")
    @patch.object(SpeciesFrame, "get_image")
    @patch.object(SpeciesFrame, "scale_image_width")
    def test_update_image(self, mock_scale, mock_get_image, mock_photo_image):
        self.sf.update_image()
        mock_get_image.assert_called_once_with("comchi1", "NO", "6", "8")
        mock_photo_image.assert_called_once()
        mock_scale.assert_called_once()

    def test_scale_image_width_preserves_aspect_ratio(self):
        from PIL import Image

        self.sf.image_width = 100
        image = Image.new("RGB", (200, 80))

        scaled_image = self.sf.scale_image_width(image)

        self.assertEqual(scaled_image.size, (100, 40))

    @patch.object(SpeciesFrame, "_extract_images", return_value=["image-url"])
    @patch.object(SpeciesFrame, "_fetch_images", return_value="page-content")
    def test_get_image_list_builds_query_and_caches_result(
        self, mock_fetch, mock_extract
    ):
        result = self.sf.get_image_list("comchi1", "NO", 6, 8)

        self.assertEqual(result, ["image-url"])
        mock_fetch.assert_called_once_with(
            "https://media.ebird.org/catalog?view=grid&taxonCode=comchi1"
            "&sort=rating_rank_desc&mediaType=photo&regionCode=NO"
            "&beginMonth=6&endMonth=8"
        )
        mock_extract.assert_called_once_with("page-content")
        self.assertEqual(self.sf.get_image_list("comchi1", "NO", 6, 8), result)
        mock_fetch.assert_called_once()

    @patch.object(SpeciesFrame, "_fetch_images")
    def test_get_image_list_extracts_only_enough_image_results(
        self, mock_fetch
    ):
        image_urls = [
            f"https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{i}/640"
            for i in range(6)
        ]
        mock_fetch.side_effect = [
            " ".join(image_urls),
            " ".join(image_urls[:4]),
        ]

        self.assertEqual(
            self.sf.get_image_list("comchi1", "", 1, 12),
            [image_urls[2], image_urls[4]],
        )
        self.sf.cached_image_list = []
        self.assertEqual(self.sf.get_image_list("comchi1", "", 1, 12), [])

    @patch("photo_id.match_window.url_cache.URLCache")
    def test_image_list_fetch_uses_cached_content(self, mock_url_cache):
        image_urls = [
            f"https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{i}/640"
            for i in range(6)
        ]
        mock_url_cache.return_value.get.return_value = " ".join(image_urls)

        result = self.sf.get_image_list("comchi1", "", 1, 12)

        self.assertEqual(result, [image_urls[2], image_urls[4]])
        mock_url_cache.return_value.set.assert_not_called()

    @patch("photo_id.match_window.playwright")
    @patch("photo_id.match_window.url_cache.URLCache")
    def test_fetch_images_loads_and_caches_page_content(
        self, mock_url_cache, mock_playwright
    ):
        mock_url_cache.return_value.get.return_value = None
        page = mock_playwright.sync_api.sync_playwright.return_value.__enter__.return_value
        browser = page.chromium.launch.return_value
        image_urls = [
            f"https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{i}/640"
            for i in range(6)
        ]
        page_content = " ".join(image_urls)
        browser.new_context.return_value.new_page.return_value.locator.return_value.inner_html.return_value = page_content

        result = self.sf.get_image_list("comchi1", "", 1, 12)

        self.assertEqual(result, [image_urls[2], image_urls[4]])
        page.chromium.launch.assert_called_once_with(headless=True)
        browser.close.assert_called_once()
        mock_url_cache.return_value.set.assert_called_once_with(
            "https://media.ebird.org/catalog?view=grid&taxonCode=comchi1"
            "&sort=rating_rank_desc&mediaType=photo",
            page_content,
        )

    @patch("photo_id.match_window.Toplevel")
    @patch("photo_id.match_window.Message")
    def test_check_selection_correct(self, mock_message, mock_toplevel):
        self.sf.selected_species.get.return_value = "Common Chiffchaff"
        self.sf.selected_species.set(self.sf.selected_species.get())
        self.sf.check_selection(None)
        mock_message.assert_not_called()

    @patch("photo_id.match_window.Toplevel")
    @patch("photo_id.match_window.Message")
    def test_check_selection_incorrect(self, mock_message, mock_toplevel):
        self.sf.selected_species.set("Incorrect Species")
        self.sf.check_selection(None)
        self.assertAlmostEqual(
            mock_message.call_args_list[0][1],
            {"text": "Incorrect. Try again.", "padx": 20, "pady": 20},
        )
        mock_toplevel.assert_called_once()

    @patch.object(SpeciesFrame, "update_image")
    def test_next_image(self, mock_update_image):
        self.sf.cached_image_list = ["image1", "image2", "image3"]
        self.sf.image_number = 0
        self.sf.next_image()
        self.assertEqual(self.sf.image_number, 1)
        mock_update_image.assert_called_once()

    @patch.object(SpeciesFrame, "update_image")
    def test_next_image_overflow(self, mock_update_image):
        self.sf.cached_image_list = ["image1", "image2", "image3"]
        self.sf.image_number = 2
        self.sf.next_image()
        self.assertEqual(self.sf.image_number, 0)
        mock_update_image.assert_called_once()

    @patch.object(SpeciesFrame, "update_image")
    def test_prior_image(self, mock_update_image):
        self.sf.cached_image_list = ["image1", "image2", "image3"]
        self.sf.image_number = 2
        self.sf.prior_image()
        self.assertEqual(self.sf.image_number, 1)
        mock_update_image.assert_called_once()

    @patch.object(SpeciesFrame, "update_image")
    def test_prior_image_underflow(self, mock_update_image):
        self.sf.cached_image_list = ["image1", "image2", "image3"]
        self.sf.image_number = 0
        self.sf.prior_image()
        self.assertEqual(self.sf.image_number, 2)
        mock_update_image.assert_called_once()

    @patch("photo_id.match_window.Image.open")
    @patch("photo_id.match_window.requests.get")
    @patch.object(SpeciesFrame, "get_image_list")
    def test_get_image_no_images(
        self, mock_get_image_list, mock_requests_get, mock_image_open
    ):
        mock_get_image_list.side_effect = [[], [], []]
        mock_image_open.return_value = "default_image"

        image = self.sf.get_image("comchi1", "NO", 6, 8)

        self.assertEqual(mock_get_image_list.call_count, 3)
        mock_get_image_list.assert_any_call("comchi1", "NO", 6, 8)
        mock_get_image_list.assert_any_call("comchi1", "", 6, 8)
        mock_get_image_list.assert_any_call("comchi1", "", 1, 12)
        mock_requests_get.assert_not_called()
        mock_image_open.assert_called_once_with(
            "photo_id/resources/Banner__Under_Construction__version_2.jpg"
        )
        self.assertEqual(image, "default_image")

    @patch("photo_id.match_window.Image.open")
    @patch("photo_id.match_window.requests.get")
    @patch.object(SpeciesFrame, "get_image_list")
    def test_get_image_request_failure(
        self, mock_get_image_list, mock_requests_get, mock_image_open
    ):
        mock_get_image_list.return_value = [
            "http://example.com/image4.jpg"
        ] * 20
        mock_requests_get.side_effect = requests.exceptions.RequestException
        mock_image_open.return_value = "default_image"

        image = self.sf.get_image("comchi1", "NO", 6, 8)

        mock_get_image_list.assert_called_once_with("comchi1", "NO", 6, 8)
        mock_requests_get.assert_called_once_with(
            "http://example.com/image4.jpg", timeout=10
        )
        mock_image_open.assert_called_once_with(
            "photo_id/resources/Banner__Under_Construction__version_2.jpg"
        )
        self.assertEqual(image, "default_image")

    @patch("photo_id.match_window.Image.open")
    @patch("photo_id.match_window.requests.get")
    @patch("photo_id.match_window.url_cache.URLCache")
    @patch.object(SpeciesFrame, "get_image_list")
    def test_get_image_downloads_and_caches_image(
        self,
        mock_get_image_list,
        mock_url_cache,
        mock_requests_get,
        mock_image_open,
    ):
        mock_get_image_list.return_value = ["https://example.test/image.jpg"]
        mock_url_cache.return_value.get.return_value = None
        mock_requests_get.return_value.content = b"image-bytes"
        mock_image_open.return_value = "image"

        result = self.sf.get_image("comchi1", "NO", 6, 8)

        self.assertEqual(result, "image")
        mock_requests_get.assert_called_once_with(
            "https://example.test/image.jpg", timeout=10
        )
        mock_requests_get.return_value.raise_for_status.assert_called_once()
        mock_url_cache.return_value.set.assert_called_once_with(
            "https://example.test/image.jpg", b"image-bytes"
        )
        mock_image_open.assert_called_once()


class TestMatchWindow(unittest.TestCase):
    @patch("photo_id.match_window.process_quiz.process_quiz_file")
    @patch("photo_id.match_window.VerticalScrolledFrame")
    @patch("photo_id.match_window.SpeciesFrame")
    @patch("photo_id.match_window.Toplevel")
    def setUp(
        self,
        mock_toplevel,
        mock_species_frame,
        mock_vsframe,
        mock_process_quiz,
    ):
        self.mock_toplevel = mock_toplevel
        self.mock_species_frame = mock_species_frame
        self.mock_vsframe = mock_vsframe
        self.mock_process_quiz = mock_process_quiz

        self.file = "test_file"
        self.taxonomy = {"species": "test_species"}
        self.have_list = ["species1", "species2"]

        self.quiz_data = {
            "species": [
                {"speciesCode": "comchi1", "comName": "Common Chiffchaff"}
            ],
            "notes": "Test notes",
            "location": "NO",
            "start_month": 6,
            "end_month": 8,
        }
        self.mock_process_quiz.return_value = self.quiz_data

        self.match_window = MatchWindow(
            self.file, self.taxonomy, self.have_list
        )

    def test_initialization(self):
        self.mock_toplevel.assert_called_once()
        self.mock_vsframe.assert_called_once_with(self.match_window.root)
        self.mock_species_frame.assert_called_once_with(
            self.mock_vsframe.return_value.interior,
            0,
            self.quiz_data["species"],
            self.quiz_data["location"],
            self.quiz_data["start_month"],
            self.quiz_data["end_month"],
            420,
            False,
        )

    def test_image_display(self):
        columns = 1
        rows = int(len(self.quiz_data["species"]) / columns) + 1

        self.assertEqual(len(self.match_window.image_display), rows + 1)
        for row in range(1, rows + 1):
            for column in range(columns):
                if (row - 1) * columns + column >= len(
                    self.quiz_data["species"]
                ):
                    break
                self.mock_species_frame.assert_any_call(
                    self.mock_vsframe.return_value.interior,
                    (row - 1) * columns + column,
                    self.quiz_data["species"],
                    self.quiz_data["location"],
                    self.quiz_data["start_month"],
                    self.quiz_data["end_month"],
                    420,
                    False,
                )
