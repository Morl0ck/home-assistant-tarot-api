"""Parse and render the dashboard example against actual reading attributes."""

from copy import deepcopy
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

from ha_test_support import install_import_stubs

install_import_stubs()

from custom_components.tarot_api.const import PROVIDER_EKELEN
from custom_components.tarot_api.readings import load_readings

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard = yaml.safe_load((ROOT / "examples/tarot_dashboard_card.yaml").read_text(encoding="utf-8"))
        cls.content = cls.dashboard["cards"][2]["content"]
        cls.template = Environment(undefined=StrictUndefined).from_string(cls.content)
        cls.catalog = load_readings()

    def render(self, attrs):
        return self.template.render(state_attr=lambda entity, key: attrs.get(key))

    def test_every_orientation_renders_one_heading_and_complete_reading(self):
        for card_id, record in self.catalog.cards.items():
            for orientation in ("upright", "reversed"):
                with self.subTest(card=card_id, orientation=orientation):
                    attrs = self.catalog.attributes_for({"name_short": card_id}, PROVIDER_EKELEN, orientation)
                    attrs.update(orientation=orientation, description="OLD PICTURE DESCRIPTION", meaning="OLD API MEANING")
                    text = self.render(attrs)
                    headings = [line for line in text.splitlines() if line.startswith("### ")]
                    self.assertEqual(headings, [f"### {record['name']} — {orientation.title()}"])
                    self.assertIn(record[orientation]["interpretation"], text)
                    self.assertIn(record[orientation]["reflection"], text)
                    self.assertIn(" · ".join(record[orientation]["keywords"]), text)
                    self.assertNotIn("OLD PICTURE DESCRIPTION", text)
                    self.assertNotIn("OLD API MEANING", text)
                    self.assertNotIn("(reversed)", text)

    def test_empty_and_unknown_card_messages(self):
        self.assertIn("Draw a card to begin.", self.render({}))
        unknown = self.catalog.attributes_for({"name_short": "unknown", "name": "Unknown draw"}, PROVIDER_EKELEN, "reversed")
        unknown["orientation"] = "reversed"
        text = self.render(unknown)
        self.assertIn("### Unknown draw — Reversed", text)
        self.assertIn("A local reading is not available for this card.", text)
        self.assertNotIn("**Reflection**", text)
        self.assertNotIn("None", text)

    def test_user_layout_controls_and_image_rotation_are_preserved(self):
        # Compare the user's pre-task dashboard, not the committed Git version.
        before_path = ROOT.parent / "before/examples/tarot_dashboard_card.yaml"
        if not before_path.exists():
            self.skipTest("Pre-task dashboard snapshot is only available in this task")
        before = yaml.safe_load(before_path.read_text(encoding="utf-8"))
        after = deepcopy(self.dashboard)
        before["cards"][2].pop("content")
        after["cards"][2].pop("content")
        self.assertEqual(after, before)
        rotation = self.dashboard["cards"][1]["card_mod"]["style"]
        template = Environment(undefined=StrictUndefined).from_string(rotation)
        self.assertIn("rotate(180deg)", template.render(state_attr=lambda *args: "reversed"))
        self.assertNotIn("rotate(180deg)", template.render(state_attr=lambda *args: "upright"))


if __name__ == "__main__":
    unittest.main()
