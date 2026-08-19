# 🚀 Network Management System (NMS) - Roadmap & TODOs

## 🌟 Features to Add (New Modules)
- [ ] **Live Network Map:** Use Leaflet.js to show BTS locations on a map with live Ping status (Green=Online, Red=Offline).
- [ ] **Automated Backups:** Use Celery Beat to schedule daily config backups (`export` / `show run`) for MikroTik & Cisco at 3:00 AM.
- [ ] **Telegram/SMS Alerts:** Send instant notifications to the admin group if a critical node goes down or unauthorized access is detected.
- [ ] **Two-Factor Authentication (2FA):** Enhance security by requiring Google Authenticator OTP for admin logins.

## 🧹 Refactoring & Optimization
- [ ] **CSS Extraction:** Move all inline `<style>` tags from HTML templates into a single `main.css` file in the `/static/` folder for better caching and speed.
- [ ] **Log Rotation Task:** Create a background task to automatically delete `ConnectionLog` and `CommandHistory` older than 6 months to keep the database fast.
- [ ] **Clean Up:** Disable or hide any unused tools from the dashboard.