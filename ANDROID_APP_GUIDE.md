# Android app / installable mobile setup

This project now behaves like an Android-friendly mobile app through a Progressive Web App (PWA) setup:

1. Open the app in Chrome on an Android phone at the same server URL used by the website.
2. Tap the browser menu and choose Add to Home screen.
3. The app installs as a standalone app icon and opens in a mobile shell without the browser chrome.
4. The app uses the same backend sync endpoint as the website, so steps and calories burned are shared through the same server data file.

Sync model:
- The website and phone app both post to /api/sync.
- The backend merges activity by date and stores the latest steps and calories burned.
- The website reads the same data immediately, so synced phone data appears in the web tracker as soon as it is saved.

For local development:
- Start the backend with: python app.py
- Open: http://127.0.0.1:8000/
- On a phone on the same network, open the computer's IP instead of 127.0.0.1 to sync across devices.
