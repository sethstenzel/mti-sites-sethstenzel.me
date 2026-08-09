cd /d "%~dp0" && ^
git switch main && ^
git add . && ^
git commit -m "blog entry / edit" && ^
git push && ^
git switch release && ^
git merge main && ^
git push && ^
git switch main

