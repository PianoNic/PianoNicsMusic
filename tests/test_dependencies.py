import importlib.util
import unittest
from pathlib import Path


class TestVoiceDependencies(unittest.TestCase):
    def test_voice_dependencies_are_installed(self):
        # Pycord raises only when a voice channel is joined, so importing the bot
        # cleanly proves nothing about whether it can actually play anything.
        for module in ("nacl", "davey"):
            with self.subTest(module=module):
                self.assertIsNotNone(
                    importlib.util.find_spec(module),
                    f"{module} is missing, so voice will not work",
                )

    def test_requirements_pull_the_voice_extra(self):
        requirements = Path('requirements.txt').read_text(encoding='utf-8')

        self.assertIn('py-cord[voice]', requirements)


if __name__ == '__main__':
    unittest.main()
