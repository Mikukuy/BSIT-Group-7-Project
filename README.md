# MoneyMate

A blue-themed Python desktop app for personal income, expense, and monthly budget tracking. Includes light and dark modes, account-scoped records, explicit logout, cancellable forms, and a recoverable transaction archive.

## Run in VS Code on Windows

1. Install Python 3.10 or newer, including Tcl/Tk support, and open this project folder in VS Code.
2. Open a terminal in the project folder:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

3. Create an account, log in, and add your own transactions. No demonstration credentials or accounts are included in the clean download.

On macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Tkinter is part of most Python desktop installations. On Linux you may need the distribution's `python3-tk` package. A graphical desktop is required. SQLAlchemy handles data storage, and Pillow loads the app logos; charts are drawn directly in Tkinter.

To change the visible brand logo, replace the image files in the project root (for example `moneymate.jpg` and `white logo.png`) or set `logo` and `sidebar_logo` in `app_data/settings.json` to new file paths or names. Relative paths are resolved from the project folder.

## What changed

- Consistent blue light and dark themes, financial summary cards, spending chart, clear period labels, sidebar navigation, scrollable pages, and empty states.
- Search, type/date filters, reset filters, and clear selection on Transactions and Archive.
- Add and edit transactions with amount, category, date, and notes.
- Cancel buttons, Escape, and window-close actions on forms. Unsaved edits require confirmation before discarding. Cancelling the confirmation keeps the draft intact.
- Archive instead of permanent transaction deletion; Restore reverses an archive action and recalculates totals.
- Explicit logout confirmation ends the in-memory login session, clears account state and visible records, and returns to login. Relaunching never logs in automatically.
- Custom categories are saved per account and shared across forms. Expense categories are available in budgets too. Removing one hides it from new choices without erasing history; adding the same name restores it.
- Budgets persist per user, category, and month. The budget summary distinguishes all monthly spending from spending in budgeted categories.
- An overspending confirmation occurs **before** saving. Cancel keeps the draft open without writing a transaction. Restoring an archived record restores its actual historical spending even if this puts a budget over its limit.
- Exact integer centavos for new or edited records, finite positive input validation, and at most two decimal places. Original Float amounts remain readable for compatibility.
- Salted PBKDF2 password storage. Existing SHA-256 accounts are upgraded only after their next successful login.

## User controls

| Action | Cancel or reverse it |
| --- | --- |
| New or edited transaction, budget, or category | Cancel, Esc, or close the form; confirm discard if changed |
| Go over budget | Cancel the warning to keep editing without saving |
| Archive or restore records | Cancel confirmation; archive can later be reversed with Restore |
| Remove a budget or category | Cancel confirmation before committing |
| Registration | Cancel and return to login; confirmation protects a filled draft |
| Logout or application exit | Cancel the confirmation to remain in the application |
| Search, filters, or row selection | Reset filters or clear selection |
| Theme | Toggle back; entered login/registration information is preserved |

A successful Save commits immediately. Cancel does not roll back already saved records; use Edit, Archive, or Restore to correct them. Removing a budget is confirmed but is not an undo history; it can be set again. Theme settings are cosmetic preferences, not login sessions.

## Existing project and database

The data file is `moneymate.db` beside `models.py`, regardless of the working directory. It is created automatically if absent. Your existing database stays in place. Before running the refreshed app for the first time, close the old app and make a separate copy of `moneymate.db` as a backup. The upgrade adds archive and centavo columns and a budget table without deleting existing users, transactions, or categories. Before adding columns, it also makes a SQLite backup inside `.backups/`. Do not run the old and new apps against the same database at the same time.

Saved budgets from the old schema are carried into the current month during migration; budgets and custom categories held only in the old app's memory cannot be recovered from its database. Legacy transaction amounts are interpreted to the nearest centavo when read; a saved edit writes integer centavos. Existing users must log in with their original password; there is no password reset flow in this version.

`MONEYMATE_DB_PATH` and `MONEYMATE_SETTINGS_PATH` can override database and preference locations for tests. Preferences contain only the theme and normally live in `app_data/settings.json`.

SQLite remains a local, unencrypted file. Account filtering is application-level separation, not protection against someone who can directly access the computer's database file. This is a first-year desktop prototype, without bank integration, email OTP, or cloud synchronization.

## Files

- `app.py`: Tkinter screens, themes, and confirmation/cancellation behavior.
- `services.py`: authentication, validation, account-scoped operations, and calculations.
- `models.py`: SQLite models, password verification, and safe additive upgrades.
- `tests/test_services.py`: regression checks using temporary databases.
- `tests/gui_smoke.py`: optional graphical smoke checks, including cancellation and logout.
- `app_streamlit_old.py`: historical version only; do not run it with your active database. It does not implement the refreshed account-isolation and archive rules.

## Verify

```bash
python -m unittest discover -s tests -v
python tests/gui_smoke.py
```

GUI checks require an available display. On Linux CI they can run with `xvfb-run -a python tests/gui_smoke.py`. Test data is fictional and databases are temporary.

See `CHANGELOG.md` for the implementation scope and validation results.
