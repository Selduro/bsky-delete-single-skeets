Skript, das alle Einzelskeets eines Accounts, für den man obv Nutzername und Passwort braucht, findet und löscht. Einzelskeets sind solche eigenen Skeets, auf die nicht unmittelbar ein weiterer eigener Skeet als Antwort verfasst wurde. 

Rechtsklick auf bsky-delete-single-skeets.exe oder bsky-delete-single-skeets.py => Ziel speichern unter. Exe zum Ausführen doppelklicken und ggf. in windows defender zulassen. wenn ihr mir nicht traut, was ich empfehlen würde, dann den quellcode statt der exe laden und das skript über python ausführen. 


version4 enthält 3 Filter:
- Ist Teil eines Threads ja/nein = was nicht Teil eines eigenen Threads ist, wird gelöscht, wenn nicht von anderem Filter erfasst;
- Mindestanzahl an Favs = Alles darunter wird gelöscht, wenn nicht von anderem Filter umfasst;
- Mindestanzahl an Reskeets = Alles darunter wird gelöscht, wenn nicht von anderem Filter umfasst

Die Filter verhalten sich alternativ zueinander = Nur skeets, die keine der drei Bedingungen erfüllen, werden gelöscht. Die Mindestanzahlen sind konfigurierbar

Bekannte Fehler: Mindestanzahl kann nicht auf Null gesetzt werden. Fix kommt.


keine haftung fuer irgendwas, benutzung auf eigene gefahr!!!
