"""SRT Voice Studio 1.5.1 UI lifetime hotfix.

PySide can invalidate a QAction that was created through a temporary QMenu
wrapper (``menuBar().addMenu(...).addAction(...)``). 1.5.0 kept a Python
reference to the QAction but not to the Help QMenu wrapper, so after wrapper
collection the stored action could raise ``Internal C++ object ... already
deleted`` when preview/render tried to disable it.

Keep strong references to top-level menus and recreate the diagnostic action
with an explicitly owned Help menu. This changes no TTS/render behaviour.
"""
from __future__ import annotations


def stabilize_qactions(window):
    """Make menu/action ownership explicit and return *window*."""
    owned = []
    help_menu = None

    for top_action in list(window.menuBar().actions()):
        try:
            menu = top_action.menu()
        except RuntimeError:
            continue
        if menu is None:
            continue
        owned.append(menu)
        try:
            if top_action.text() == 'Trợ giúp':
                help_menu = menu
        except RuntimeError:
            pass

    if help_menu is None:
        help_menu = window.menuBar().addMenu('Trợ giúp')
        owned.append(help_menu)

    # Remove the short-lived 1.5.0 diagnostic action and recreate it with an
    # explicitly retained QMenu owner. The attribute is replaced immediately,
    # so start()/finished() always target a valid QAction.
    try:
        help_menu.clear()
    except RuntimeError:
        help_menu = window.menuBar().addMenu('Trợ giúp')
        owned.append(help_menu)

    window.help_menu = help_menu
    window._owned_top_menus = owned
    window.diagnostic_action = help_menu.addAction('Kiểm tra ứng dụng')
    window.diagnostic_action.triggered.connect(lambda: window.start('diagnose', {}))
    return window
