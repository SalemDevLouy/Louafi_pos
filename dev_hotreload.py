"""
Hot-reload system for LouafiPOS development.

Watches view files for changes and reloads them without restarting the app.
Preserves app state (controllers, DB connections, loaded data).

Usage:
    Run the app with: python main_dev.py
    Edit any view file and save - changes appear immediately
    Press Ctrl+R to force a manual reload
"""
import sys
import os
import importlib
import traceback
from pathlib import Path
from typing import Optional, Callable

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class HotReloadManager(QObject):
    """Manages file watching and module reloading for development."""

    # Signal emitted when a view module needs to be reloaded
    reload_requested = pyqtSignal(str)  # module_name

    def __init__(self, watch_dirs=None):
        super().__init__()
        self.watch_dirs = watch_dirs or ['views']
        self.observer = None
        self._debounce_timers = {}  # path -> QTimer (prevent duplicate reloads)
        self._reload_callback: Optional[Callable] = None

    def set_reload_callback(self, callback: Callable[[str], None]):
        """Set the callback function that handles actual view rebuilding."""
        self._reload_callback = callback

    def start(self):
        """Start watching configured directories for file changes."""
        if self.observer:
            return

        handler = _FileChangeHandler(self._on_file_changed)
        self.observer = Observer()

        for watch_dir in self.watch_dirs:
            if os.path.exists(watch_dir):
                self.observer.schedule(handler, watch_dir, recursive=True)
                print(f"[HotReload] Watching: {os.path.abspath(watch_dir)}")

        self.observer.start()
        print("[HotReload] Started. Edit view files to see changes instantly.")
        print("[HotReload] Press Ctrl+R to force manual reload.")

    def stop(self):
        """Stop the file watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

    def _on_file_changed(self, file_path: str):
        """Handle file change event with debouncing."""
        # Debounce: ignore rapid successive changes (editor save quirks)
        if file_path in self._debounce_timers:
            timer = self._debounce_timers[file_path]
            if timer.isActive():
                return  # Already scheduled

        # Create debounce timer
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._reload_file(file_path))
        timer.start(200)  # 200ms debounce
        self._debounce_timers[file_path] = timer

    def _reload_file(self, file_path: str):
        """Reload the changed Python module."""
        # Convert file path to module name
        path = Path(file_path)
        if not path.suffix == '.py':
            return

        # Get module name from path (e.g., views/sales_view.py -> views.sales_view)
        try:
            rel_path = path.relative_to(Path.cwd())
            module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
        except ValueError:
            # File outside project root
            return

        print(f"\n[HotReload] File changed: {file_path}")
        print(f"[HotReload] Reloading module: {module_name}")

        try:
            # Reload the module
            if module_name in sys.modules:
                module = sys.modules[module_name]
                importlib.reload(module)
                print(f"[HotReload] ✓ Module reloaded successfully")

                # Notify the callback to rebuild affected views
                if self._reload_callback:
                    self._reload_callback(module_name)
            else:
                print(f"[HotReload] ⚠ Module not yet imported: {module_name}")

        except Exception as e:
            print(f"[HotReload] ✗ Reload failed:")
            print(f"[HotReload]   {type(e).__name__}: {e}")
            traceback.print_exc()
            print("[HotReload] Keeping previous version. Fix the error and save again.")

    def manual_reload_current_view(self):
        """Manually trigger reload of the currently visible view."""
        print("\n[HotReload] Manual reload triggered (Ctrl+R)")
        if self._reload_callback:
            self._reload_callback(None)  # None = reload current view


class _FileChangeHandler(FileSystemEventHandler):
    """Watchdog event handler that filters and forwards file changes."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only handle Python files
        if event.src_path.endswith('.py'):
            # Ignore __pycache__ and temp files
            if '__pycache__' in event.src_path or event.src_path.endswith('~'):
                return

            self.callback(event.src_path)


# Module-level instance (singleton for convenience)
_hot_reload_manager: Optional[HotReloadManager] = None


def get_hot_reload_manager() -> HotReloadManager:
    """Get or create the global hot-reload manager instance."""
    global _hot_reload_manager
    if _hot_reload_manager is None:
        _hot_reload_manager = HotReloadManager(watch_dirs=['views'])
    return _hot_reload_manager


def enable_hot_reload(main_window):
    """
    Enable hot-reload for the given MainWindow instance.

    Args:
        main_window: The MainWindow instance to enable hot-reload for
    """
    manager = get_hot_reload_manager()

    # Set up the reload callback
    def reload_callback(module_name: Optional[str]):
        if hasattr(main_window, 'reload_current_view'):
            main_window.reload_current_view(module_name)

    manager.set_reload_callback(reload_callback)
    manager.start()

    # Add keyboard shortcut for manual reload (Ctrl+R)
    from PyQt5.QtWidgets import QShortcut
    from PyQt5.QtGui import QKeySequence
    from PyQt5.QtCore import Qt

    shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_R), main_window)
    shortcut.activated.connect(manager.manual_reload_current_view)

    print("\n" + "="*60)
    print("  HOT RELOAD MODE ENABLED")
    print("="*60)
    print("  • Edit any view file and save to see changes")
    print("  • Press Ctrl+R to force reload current view")
    print("  • Errors won't crash the app - check terminal output")
    print("="*60 + "\n")
