import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QSettings, QLocale
from qwarp.utils.system import get_asset_dir

app = QApplication(sys.argv)
lang_pref = "es"

translator = QTranslator()
qm_path = os.path.join(get_asset_dir(), "locales", f"qwarp_{lang_pref}.qm")
print(f"Loading {qm_path}: {os.path.exists(qm_path)}")

if translator.load(qm_path):
    print("Translator loaded!")
    app.installTranslator(translator)
else:
    print("Translator failed to load!")

print("Translated 'Settings':", app.translate("SettingsDialog", "Settings"))
print("Translated 'Account':", app.translate("SettingsDialog", "Account"))
