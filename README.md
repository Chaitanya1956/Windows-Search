# Spotlight — Phase 1 (Foundation) **NOT YET COMPLETED**

A Windows desktop launcher: Alt+Space opens a floating search bar over
everything, search apps/files/folders with typo-tolerant fuzzy
matching, navigate with arrow keys, Enter to launch.

## Requirements

- Windows 10/11
- Python 3.11+

## Setup

```powershell
cd spotlight
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
cd src
python main.py
```

The app has no visible window at first — it sits in the system tray.
Press **Alt+Space** to summon the launcher. It will be centered on
your primary screen.

On first run it will:
- Discover installed apps from your Start Menu (background thread)
- Index `Desktop`, `Documents`, `Downloads`, `Pictures` (background
  thread, incremental after the first pass — it does not rescan the
  whole disk on every launch)

Both run in the background; you can search immediately, results just
get more complete as indexing finishes (typically a few seconds for a
normal user folder).

## Controls

| Key | Action |
|---|---|
| `Alt + Space` | Toggle launcher |
| `↑` / `↓` | Move selection |
| `Enter` | Launch selected item |
| `Esc` | Hide launcher |

## Where things live

- App data / index / logs: `%LOCALAPPDATA%\Spotlight\`
- Settings file: `%LOCALAPPDATA%\Spotlight\settings.json`
- Database: `%LOCALAPPDATA%\Spotlight\index.sqlite3`

## Project structure

```
src/
  core/                  business logic, no UI/Qt imports except where noted
    cache_manager.py      owns the only SQLite connection/schema in the app
    file_indexer.py       initial scan + watchdog live updates
    search_engine.py      SQL prefilter -> RapidFuzz ranking
    command_runner.py     "launch this result" via os.startfile
    settings_manager.py   JSON-backed ConfigModel persistence
    launcher.py            composition root: wires the above together

  services/
    app_service.py        Start Menu .lnk discovery + icon extraction
    window_service.py     global hotkey (Alt+Space) + window show/center
    file_service.py       NOT Phase 1 (placeholder, marked in-file)
    clipboard_service.py  NOT Phase 1 (placeholder, marked in-file)
    plugin_service.py     NOT Phase 1 (placeholder, marked in-file)

  ui/
    main_window.py        frameless floating panel, wires everything visible
    search_bar.py          the QLineEdit, styled
    result_card.py         one result row (icon/title/subtitle/tag)
    animations.py           one restrained fade in/out + height grow
    preview_panel.py        NOT Phase 1 (placeholder, marked in-file)
    settings_window.py      NOT Phase 1 (placeholder, marked in-file)

  widgets/
    keyboard_handler.py    arrow/Enter/Escape -> callbacks, as an event filter
    system_tray.py         tray icon, Show/Quit menu

  models/                  plain dataclasses, no Qt/DB imports
    result_model.py  history_model.py  config_model.py

  utils/
    constants.py  logger.py  helpers.py

  main.py                  entry point — wires QApplication, Launcher, tray, hotkey
```

## What's deliberately NOT in Phase 1

Three files exist as structural placeholders so the package layout
matches the eventual full architecture, but contain no logic — each
says so in its own docstring: `ui/preview_panel.py`,
`ui/settings_window.py`, and `services/file_service.py` /
`clipboard_service.py` / `plugin_service.py`. Natural-language commands
("shutdown pc", "open downloads"), the calculator, clipboard manager,
and plugin system are Phase 2+ as agreed.

## Notes on performance choices

- SQLite runs in WAL mode so the indexer (writer) and search (reader)
  never block each other.
- The initial folder scan runs in one background thread; live changes
  after that come from `watchdog` events, not polling or re-walking.
- Search does a cheap SQL `LIKE` prefilter (loose — just the first 1-2
  characters) to narrow the candidate pool before RapidFuzz scores it,
  so fuzzy ranking stays fast even as the index grows, while still
  tolerating typos in the rest of the query.
- Search input is debounced (60ms) so fast typing doesn't trigger a
  query per keystroke.
