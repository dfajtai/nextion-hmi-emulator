"""Builder GUI: a small PySide6 window around the generator (everything GUI-specific lives in this package).

``main.ui`` is the Qt Designer layout, ``texts.json`` holds the hu/en texts by object name, ``app`` binds the widgets to the actions,
``jobs`` runs the generation (no Qt imports, testable headlessly). PySide6 is an optional dependency (``code/requirements-gui.txt``).
Start it with ``nextion_parser gui``.
"""
