HOW TO UPDATE STRANGENESS IS
==============================

1. Put the files Claude gives you into this upload/ folder.
   Match the project structure exactly:

   upload/app.py              → updates the backend server
   upload/admin.html          → updates the admin panel
   upload/index.html          → updates the homepage
   upload/js/chatbot.js       → updates a JS file
   upload/css/style.css       → updates a CSS file
   (any file from the project goes here at the same path)

2. Double-click DEPLOY.bat in the main folder.

3. Done. The script:
   - Uploads changed files to the server
   - Restarts the server automatically
   - Pushes the frontend to GitHub (live in ~60 seconds)
   - Archives these files to upload/archive/
   - Clears upload/ ready for next time

This README file is ignored by DEPLOY.bat.
