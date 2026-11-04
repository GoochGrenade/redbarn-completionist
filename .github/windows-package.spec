# PyInstaller recipe for the Windows download, run by .github/workflows/windows.yml on MSYS2 UCRT64.
import os

root = os.path.join(SPECPATH, "..")
a = Analysis(
    [os.path.join(root, "rs3comp_gui.py")],
    # fixtures are the two sample players --self-test uses
    datas=[(os.path.join(root, "requirements.json"), "."), (os.path.join(root, "guides.json"), "."),
           (os.path.join(root, "data"), "data"),
           (os.path.join(root, "fixtures"), "fixtures")],
    hooksconfig={"gi": {"module-versions": {"Gtk": "4.0", "Gdk": "4.0"}, "icons": ["Adwaita"], "themes": ["Adwaita"]}},
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Redbarn Completionist", console=False,
          icon=os.path.join(root, "redbarn-completionist.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name="Redbarn Completionist")
