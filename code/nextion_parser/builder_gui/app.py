"""The Qt window (PySide6): loads ``main.ui`` (Qt Designer, English) and binds it to the generator (``jobs``).

The window itself is English only. The language selector chooses the *default language of the generated emulator*.
"""
from __future__ import annotations

import sys
import threading
from importlib import resources
from pathlib import Path

from PySide6 import QtCore, QtGui, QtUiTools, QtWidgets

from .. import easy
from . import jobs

LANGS = ["hu", "en"]                   # emulator default language; same order as the items of comboLang in main.ui
MESSAGES = {
    "choose_hmi": "Choose a .HMI file.",
    "ready": "Ready to generate.",
    "running": "Generating…",
    "done": "Done. Result: {path}",
    "done_warn": "Done, but some scenarios do not match this HMI (see the log). Result: {path}",
    "failed": "Failed – see the log for details.",
    "file_types": "Nextion HMI (*.HMI *.hmi);;All files (*)",
    "pick_hmi": "Choose the HMI file",
    "pick_out": "Choose the output folder",
    "pick_scn": "Choose the scenarios folder",
}


def _res(name: str) -> str:
    return resources.files("nextion_parser.builder_gui").joinpath(name).read_text(encoding="utf-8")


def load_ui(xml: str) -> QtWidgets.QWidget:
    """Load a Qt Designer file given as text (so it also works from inside a .pyz); child widgets are reachable by object name."""
    data = QtCore.QByteArray(xml.encode("utf-8"))
    buf = QtCore.QBuffer(data)
    buf.open(QtCore.QIODevice.OpenModeFlag.ReadOnly)
    w = QtUiTools.QUiLoader().load(buf)
    buf.close()
    if w is None:
        raise RuntimeError("main.ui could not be loaded")
    return w


class Signals(QtCore.QObject):
    """Worker thread -> window. Signals emitted from another thread are delivered in the GUI thread (queued)."""
    log = QtCore.Signal(str)
    done = QtCore.Signal(object)


class BuilderWindow:
    def __init__(self, initial_hmi: Path | None = None, lang: str = "hu"):
        self.w: QtWidgets.QWidget = load_ui(_res("main.ui"))
        self.lang = lang                              # default language of the generated emulator
        self.launcher: Path | None = None
        self.busy = False
        self._auto_out = ""
        self.signals = Signals()
        self.signals.log.connect(self.log)
        self.signals.done.connect(self._finished)

        w = self.w
        w.btnBrowseHmi.clicked.connect(self.browse_hmi)
        w.btnBrowseOut.clicked.connect(lambda: self._pick_dir(w.editOut, "pick_out"))
        w.btnBrowseScn.clicked.connect(lambda: self._pick_dir(w.editScn, "pick_scn"))
        w.btnGenerate.clicked.connect(self.generate)
        w.btnOpenResult.clicked.connect(self.open_result)
        w.btnOpenFolder.clicked.connect(self.open_folder)
        w.editHmi.textChanged.connect(self._hmi_changed)
        w.comboLang.setCurrentIndex(LANGS.index(self.lang))
        w.comboLang.currentIndexChanged.connect(lambda i: setattr(self, "lang", LANGS[i]))

        found = initial_hmi or next(iter(easy.find_hmi(easy.base_dir())), None)
        w.editHmi.setText(str(found) if found else "")
        self.set_status("ready" if found else "choose_hmi")

    # ---- status
    def msg(self, key: str, **kw) -> str:
        return MESSAGES[key].format(**kw)

    def set_status(self, key: str, **kw) -> None:
        self.w.labelStatus.setText(self.msg(key, **kw))

    # ---- helpers
    def log(self, text: str) -> None:
        t = self.w.textLog
        t.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        t.insertPlainText(text)
        t.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def _hmi_changed(self, value: str) -> None:
        v = value.strip()
        if v and (not self.w.editOut.text() or self.w.editOut.text() == self._auto_out):   # keep a user-chosen folder
            self._auto_out = str(jobs.default_output(Path(v)))
            self.w.editOut.setText(self._auto_out)

    # ---- actions
    def browse_hmi(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self.w, self.msg("pick_hmi"), "", self.msg("file_types"))
        if path:
            self.w.editHmi.setText(path)

    def _pick_dir(self, edit: QtWidgets.QLineEdit, title_key: str) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self.w, self.msg(title_key), edit.text())
        if path:
            edit.setText(path)

    def generate(self) -> None:
        if self.busy:
            return
        hmi = self.w.editHmi.text().strip()
        if not hmi or not Path(hmi).is_file():
            self.set_status("choose_hmi")
            return
        self.busy = True
        for b in (self.w.btnGenerate, self.w.btnOpenResult, self.w.btnOpenFolder):
            b.setEnabled(False)
        self.log(f"\n=== {hmi}\n")
        self.set_status("running")
        args = dict(out=self.w.editOut.text().strip() or None, lang=self.lang, screen=self.w.editScreen.text(),
                    scenarios=self.w.editScn.text())
        threading.Thread(target=lambda: self.signals.done.emit(jobs.run_generation(hmi, emit=self.signals.log.emit, **args)),
                         daemon=True).start()

    def _finished(self, res: jobs.JobResult) -> None:
        self.busy = False
        self.launcher = res.launcher
        self.w.btnGenerate.setEnabled(True)
        for b in (self.w.btnOpenResult, self.w.btnOpenFolder):
            b.setEnabled(res.launcher is not None)
        if res.rc == 0:
            self.set_status("done", path=res.launcher)
        elif res.rc == 4 and res.launcher:
            self.set_status("done_warn", path=res.launcher)
        else:
            self.set_status("failed")

    def open_result(self) -> None:
        if self.launcher:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.launcher)))

    def open_folder(self) -> None:
        if self.launcher:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.launcher.parent)))

    def show(self) -> None:
        self.w.show()


def main(argv: list[str] | None = None) -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    win = BuilderWindow(Path(argv[0]) if argv else None)
    win.show()
    return app.exec()
