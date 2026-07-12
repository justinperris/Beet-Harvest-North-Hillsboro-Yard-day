# Piler Crew Sign-In Tool

This is a set of static HTML pages for managing daily piler crew rosters and sign-in sheets.

## How to Use (Locally)

1. Open `piler-info.html`
2. Fill in the crew details (Name, Piler #, roles).
3. Click **Save Now** — this saves locally and downloads a dated `data.json` file.
4. Open `hillsboro-signin.html` (or use the button in the info page).
5. The sign-in will pull the latest crew data for Piler #7 and #8.
6. Use **View History** to see past daily versions.

## Setting Up on GitHub (for Sharing)

This allows you to share a public link where others can view the current roster.

### Step-by-Step Setup

1. Go to [github.com](https://github.com) and create a free account if you don't have one.

2. Click the **+** icon (top right) → **New repository**.
   - Name: something like `piler-crew-signin` (no spaces)
   - Make it **Public**
   - Do **not** check "Add a README file" yet
   - Click **Create repository**

3. Upload the files:
   - In your new repo, click **Add file** → **Upload files**
   - Drag and drop these files from your folder:
     - `piler-info.html`
     - `hillsboro-signin.html`
     - `History.html`
     - `README.md` (this file)
     - (Optional: `foreman-signin.html` and the PDF)
   - At the bottom, add a commit message like "Initial upload" and click **Commit changes**

4. Enable GitHub Pages (this creates the shareable link):
   - Go to your repo → **Settings** tab
   - Scroll down to **Pages** (in the left menu)
   - Under "Build and deployment":
     - Source: **Deploy from a branch**
     - Branch: `main` (or `master`)
     - Folder: `/ (root)`
   - Click **Save**
   - Wait 1-2 minutes

5. Get your link:
   - After it builds, you'll see a message like:
     "Your site is published at https://yourusername.github.io/piler-crew-signin/"
   - The main entry point is now:
     - https://yourusername.github.io/piler-crew-signin/ (simple landing page with big buttons)
   - Individual pages:
     - https://yourusername.github.io/piler-crew-signin/piler-info.html
     - https://yourusername.github.io/piler-crew-signin/hillsboro-signin.html

### Updating the Roster (Daily)

1. Use the HTML files locally on your computer (double-click them).
2. Fill in the piler-info page.
3. Click **Save Now** — it will download a file like `data-2026-06-18-Thursday.json`
4. Go to your GitHub repo.
5. Click **Add file** → **Upload files**
6. Drag in the downloaded JSON file.
7. **Important**: Rename it to `data.json` (or keep the dated name if you want history).
8. Commit with a message like "Updated crew for June 18".
9. The shared GitHub Pages link will now show the new data (refresh if needed).

**Note**: The pages automatically load `data.json` when opened from the GitHub link.

### Tips

- File names with spaces become `%20` in URLs (e.g. `Piler%20Information%20Input.html`). It still works.
- History is saved locally on your computer only.
- Anyone with the link can view the current roster, but changes they make stay only on their device.
- To keep a clean "current" version, always upload the latest export as `data.json`.

## Local vs Shared

- **Local use**: Works great by double-clicking the .html files. Uses browser storage.
- **Shared via GitHub**: Use the Pages link above. Data comes from the committed `data.json`.

A simple `index.html` landing page with big buttons is included for easy navigation from the shared link. Every page also has a small "← Home" link at the top.

For questions or updates, feel free to reach out!