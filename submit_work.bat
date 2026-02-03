@echo off
cd /d "C:\Users\Samue\OneDrive\Documents\OneDrive\Projecs\ai-skills-challenge-log"

echo.
echo === Submitting your completed challenge work ===
echo.

git add .
git commit -m "Complete challenge - %date%"
git push

echo.
echo === Done! Your work has been pushed to GitHub ===
echo.
pause
