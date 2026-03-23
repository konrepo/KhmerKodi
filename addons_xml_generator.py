import os
import hashlib


class Generator:
    def __init__(self):
        self.root = os.getcwd()
        self.addons_xml_path = os.path.join(self.root, "addons.xml")
        self.md5_path = os.path.join(self.root, "addons.xml.md5")
        self.excludes = {".git", ".github", "zips", "__pycache__"}

    def run(self):
        addons_xml = self._generate_addons_file()
        self._save_file(self.addons_xml_path, addons_xml)
        self._save_file(self.md5_path, self._generate_md5(addons_xml))
        print("Finished generating addons.xml and addons.xml.md5")

    def _generate_addons_file(self):
        addons = []

        for item in sorted(os.listdir(self.root)):
            item_path = os.path.join(self.root, item)

            if not os.path.isdir(item_path):
                continue

            if item in self.excludes:
                continue

            addon_xml_path = os.path.join(item_path, "addon.xml")
            if not os.path.isfile(addon_xml_path):
                continue

            with open(addon_xml_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            content = self._strip_xml_declaration(content)
            addons.append(content)

        xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
        xml.extend(addons)
        xml.append("</addons>")
        xml.append("")

        return "\n".join(xml)

    @staticmethod
    def _strip_xml_declaration(content):
        lines = content.splitlines()
        if lines and lines[0].strip().startswith("<?xml"):
            lines = lines[1:]
        return "\n".join(lines).strip()

    @staticmethod
    def _generate_md5(text):
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _save_file(path, content):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)


if __name__ == "__main__":
    Generator().run()