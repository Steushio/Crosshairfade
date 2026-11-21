"""
Unit tests for Valorant Crosshair Fade application
"""

import unittest
import os
import json
from crosshair_config import CrosshairConfig, PRESETS
from renderer import render_crosshair_image, render_preview_image
from PIL import Image

class TestCrosshairApp(unittest.TestCase):
    def setUp(self):
        self.test_config_path = "test_crosshair_config.json"
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def tearDown(self):
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def test_default_config(self):
        config = CrosshairConfig()
        self.assertEqual(config.fade_mode, "Hidden Until Released")
        self.assertTrue(config.start_minimized)
        self.assertTrue(config.inner_lines_enabled)
        self.assertEqual(config.inner_line_color, "#00FFFF")
        self.assertEqual(config.outer_line_color, "#FFFF00")
        self.assertEqual(config.outline_color, "#000000")

    def test_save_and_load_profile(self):
        config = CrosshairConfig()
        config.inner_line_color = "#FF0000"
        config.outer_line_color = "#FFFF00"
        config.inner_line_length = 8
        config.save_custom_profile("TestSniper")

        self.assertIn("TestSniper", config.custom_profiles)
        self.assertEqual(config.custom_profiles["TestSniper"]["inner_line_color"], "#FF0000")
        self.assertEqual(config.custom_profiles["TestSniper"]["outer_line_color"], "#FFFF00")

        # Create fresh config and load profile
        new_config = CrosshairConfig()
        new_config.custom_profiles = dict(config.custom_profiles)
        success = new_config.load_profile_by_name("TestSniper")
        self.assertTrue(success)
        self.assertEqual(new_config.inner_line_color, "#FF0000")
        self.assertEqual(new_config.outer_line_color, "#FFFF00")
        self.assertEqual(new_config.inner_line_length, 8)
        self.assertEqual(new_config.current_profile_name, "TestSniper")

        # Clean up custom profile
        new_config.delete_custom_profile("TestSniper")
        self.assertNotIn("TestSniper", new_config.custom_profiles)

    def test_rendering(self):
        config = CrosshairConfig()
        config.inner_lines_enabled = True
        config.outer_lines_enabled = True
        config.center_dot_enabled = True
        config.outlines_enabled = True
        config.inner_line_color = "#00FF00"
        config.outer_line_color = "#FF00FF"
        config.outline_color = "#000000"
        config.center_dot_color = "#FFFFFF"

        img = render_crosshair_image(config, canvas_size=100)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (100, 100))

        # Check that canvas has drawn pixels with alpha > 0
        extrema = img.getextrema()
        # Alpha channel extrema should have max > 0
        self.assertGreater(extrema[3][1], 0)

    def test_preview_rendering(self):
        config = CrosshairConfig()
        preview_img = render_preview_image(config, preview_size=160, zoom=4, bg_mode="Dark Gray")
        self.assertIsInstance(preview_img, Image.Image)
        self.assertEqual(preview_img.size, (160, 160))

    def test_startup_manager(self):
        import startup_manager
        initial = startup_manager.is_run_on_startup_enabled()
        self.assertIsInstance(initial, bool)
        
        # Test enabling
        ok_enable = startup_manager.set_run_on_startup(True)
        self.assertTrue(ok_enable)
        self.assertTrue(startup_manager.is_run_on_startup_enabled())

        # Test disabling
        ok_disable = startup_manager.set_run_on_startup(False)
        self.assertTrue(ok_disable)
        self.assertFalse(startup_manager.is_run_on_startup_enabled())

        # Restore initial
        startup_manager.set_run_on_startup(initial)

    def test_json_export_import(self):
        config = CrosshairConfig()
        config.inner_line_color = "#123456"
        config.outer_line_color = "#654321"
        config.save_custom_profile("ExportTest")

        export_file = "test_export.json"
        try:
            ok_exp = config.export_to_json_file(export_file)
            self.assertTrue(ok_exp)
            self.assertTrue(os.path.exists(export_file))

            # Import into fresh config
            new_config = CrosshairConfig()
            ok_imp = new_config.import_from_json_file(export_file)
            self.assertTrue(ok_imp)
            self.assertIn("ExportTest", new_config.custom_profiles)
            self.assertEqual(new_config.custom_profiles["ExportTest"]["inner_line_color"], "#123456")
            self.assertEqual(new_config.custom_profiles["ExportTest"]["outer_line_color"], "#654321")
        finally:
            if os.path.exists(export_file):
                os.remove(export_file)

if __name__ == "__main__":
    unittest.main()
