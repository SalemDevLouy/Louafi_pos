# Hot-Reload Development Workflow

LouafiPOS includes a hot-reload system for rapid UI development. Edit view files and see changes instantly without restarting the app or losing state.

---

## Quick Start

### 1. Install Dependencies

The hot-reload system requires the `watchdog` package:

```bash
pip install watchdog
```

### 2. Run in Dev Mode

Instead of running `main.py`, use the development entry point:

```bash
python main_dev.py
```

You'll see a banner confirming hot-reload is enabled:

```
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
  RUNNING IN DEVELOPMENT MODE WITH HOT-RELOAD
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥

============================================================
  HOT RELOAD MODE ENABLED
============================================================
  • Edit any view file and save to see changes
  • Press Ctrl+R to force reload current view
  • Errors won't crash the app - check terminal output
============================================================

[HotReload] Watching: /home/user/project/views
[HotReload] Started. Edit view files to see changes instantly.
[HotReload] Press Ctrl+R to force manual reload.
```

### 3. Edit and Save

1. Open any view file (e.g., `views/sales_view.py`)
2. Make your changes
3. Save the file (Ctrl+S)
4. Switch to the app window → changes appear instantly

---

## How It Works

### What Gets Reloaded
- **UI Layer**: Views, layouts, styling, widgets
- **Automatic**: Changes detected within ~200ms of save

### What Stays Persistent
- **Shell Layer**: QApplication, main window, event loop
- **Business Logic**: Controllers, database connections
- **Application State**: Loaded data, open transactions, navigation state

### Reload Triggers

1. **Automatic**: Save any `.py` file in the `views/` directory
2. **Manual**: Press `Ctrl+R` to force reload the current view

---

## What Happens on Reload

When you save a view file:

1. **File watcher** detects the change
2. **Module reloader** uses `importlib.reload()` to refresh the module
3. **View rebuilder** creates a new instance of the current view
4. **State preservation**: Controllers and data are passed to the new instance
5. **Widget replacement**: Old widget is swapped out, new one inserted
6. **Signal reconnection**: Connections are recreated automatically

**If there's an error:**
- The error prints to terminal with full traceback
- The app keeps running with the previous working version
- Fix the error, save again → reload succeeds

---

## Examples

### Example 1: Changing Button Text

**File**: `views/sales_view.py`

```python
# Before
self.btn_complete = QPushButton('Complete Sale')

# After - save and see instantly
self.btn_complete = QPushButton('Finalize Transaction')
```

### Example 2: Adjusting Layout

```python
# Before
layout.setSpacing(8)
layout.setContentsMargins(10, 10, 10, 10)

# After - save and spacing updates immediately
layout.setSpacing(16)
layout.setContentsMargins(20, 20, 20, 20)
```

### Example 3: Changing Colors

```python
# Before
self.setStyleSheet('background: #ffffff; border: 1px solid #e0e0e0;')

# After - save and colors change
self.setStyleSheet('background: #f8fafc; border: 2px solid #1a73e8;')
```

---

## Terminal Output

The terminal shows detailed reload information:

```
[HotReload] File changed: views/sales_view.py
[HotReload] Reloading module: views.sales_view
[HotReload] ✓ Module reloaded successfully
[HotReload] Rebuilding view at index 0...
[HotReload] ✓ View rebuilt successfully!
```

**On error:**

```
[HotReload] ✗ Reload failed:
[HotReload]   SyntaxError: invalid syntax
  File "views/sales_view.py", line 42
    self.btn = QPushButton(
                          ^
SyntaxError: invalid syntax
[HotReload] Keeping previous version. Fix the error and save again.
```

---

## Adding New Files to Watch

The system automatically watches the entire `views/` directory recursively.

To watch additional directories, edit `dev_hotreload.py`:

```python
# Change this line:
_hot_reload_manager = HotReloadManager(watch_dirs=['views'])

# To watch multiple directories:
_hot_reload_manager = HotReloadManager(watch_dirs=['views', 'utils', 'widgets'])
```

---

## Limitations

### What Hot-Reload Can't Handle

1. **Main window structure changes**: Adding/removing pages from QStackedWidget requires app restart
2. **Database schema changes**: Run migrations separately and restart
3. **Config file changes**: Restart needed for `config.ini` changes
4. **Import-time code**: Module-level code that runs on import won't re-execute cleanly

### When to Restart

Restart the app when you change:
- Main window layout (`main_window.py` structure)
- Database models or migrations
- Controller constructors or initialization
- Application-wide settings (fonts, themes loaded at startup)

---

## Troubleshooting

### Hot-Reload Not Working

**Check 1**: Is `watchdog` installed?
```bash
pip install watchdog
```

**Check 2**: Are you running `main_dev.py` (not `main.py`)?
```bash
python main_dev.py  # ✓ Correct
python main.py      # ✗ Wrong - no hot-reload
```

**Check 3**: Is the file in the `views/` directory?
Only files in watched directories trigger reloads.

### Changes Not Appearing

**Solution 1**: Press `Ctrl+R` to force manual reload

**Solution 2**: Check terminal for errors - syntax errors prevent reload

**Solution 3**: Ensure you're viewing the page you edited (navigate to it first)

### App Becomes Unresponsive

**Cause**: Infinite loop or blocking code in the reloaded view

**Solution**: 
1. Close the app (Ctrl+C in terminal)
2. Fix the blocking code
3. Restart with `python main_dev.py`

---

## Production Mode

**Never use hot-reload in production!**

For production builds, always use the standard entry point:

```bash
python main.py  # Production - stable, no file watching
```

Or build a standalone executable without `main_dev.py` included.

---

## Tips for Effective Hot-Reloading

1. **Make small, incremental changes** - easier to debug if something breaks
2. **Keep terminal visible** - watch for reload confirmations and errors
3. **Use Ctrl+R liberally** - force reload if automatic detection seems delayed
4. **Test on the actual page** - navigate to the view you're editing before saving
5. **Comment out risky code** - if testing something experimental, comment the old code first

---

## File Structure

```
Louafi_pos/
├── main.py              # Production entry point (no hot-reload)
├── main_dev.py          # Development entry point (with hot-reload)
├── dev_hotreload.py     # Hot-reload infrastructure
└── views/
    ├── main_window.py   # Contains reload_current_view() method
    ├── sales_view.py    # ← Edit this, save, see changes
    ├── products_view.py
    └── ...
```

---

## FAQ

**Q: Will hot-reload work with .ui files?**  
A: The watcher monitors `.py` files. If you're using Qt Designer `.ui` files, you'll need to run `pyuic5` to regenerate the Python file, then the reload will trigger.

**Q: Can I reload controller code?**  
A: Not safely. Controller state (data, DB connections) needs to persist. Only reload UI layer (views).

**Q: Does this work on Windows/Mac/Linux?**  
A: Yes, `watchdog` is cross-platform. Tested on Linux, should work on Windows/Mac.

**Q: What if I want to reload without Ctrl+R?**  
A: The file watcher handles it automatically. Ctrl+R is just a manual override.

**Q: Can multiple devs use this simultaneously?**  
A: Yes, each dev runs their own `main_dev.py` instance with their own file watcher.

---

## Advanced: Extending Hot-Reload

### Watch Additional File Types

Edit `dev_hotreload.py` in the `_FileChangeHandler` class:

```python
def on_modified(self, event):
    if event.is_directory:
        return

    # Add more extensions
    if event.src_path.endswith(('.py', '.qss', '.ui')):
        # Handle accordingly
        self.callback(event.src_path)
```

### Custom Reload Logic per View

Add a `reload_hook()` method to your view class:

```python
class SalesView(QWidget):
    def reload_hook(self):
        """Called after hot-reload rebuilds this view."""
        print("SalesView reloaded - custom logic here")
        # Restore scroll position, selections, etc.
```

Then update `MainWindow.reload_current_view()` to call it:

```python
if hasattr(new_widget, 'reload_hook'):
    new_widget.reload_hook()
```

---

**Happy hot-reloading! 🔥**
