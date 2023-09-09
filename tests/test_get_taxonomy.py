"""
Tests  photo_id/get_taxonomy.py
"""
import unittest
import photo_id.get_taxonomy

class TestGetTaxonomy(unittest.TestCase):

    def test_ebird_taxonomy(self):
        taxonomy = photo_id.get_taxonomy.ebird_taxonomy()
        self.assertTrue(len(taxonomy)>0)

