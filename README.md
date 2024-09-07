Skript, das alle Einzelskeets eines Accounts, für den man obv Nutzername und Passwort braucht, findet und löscht. Einzelskeets sind solche eigenen Skeets, auf die nicht unmittelbar ein weiterer eigener Skeet als Antwort verfasst wurde. 

Rechtsklick auf bsky-delete-single-skeets.exe oder bsky-delete-single-skeets.py => Ziel speichern unter. Exe zum Ausführen doppelklicken und ggf. in windows defender zulassen. wenn ihr mir nicht traut, was ich empfehlen würde, dann den quellcode statt der exe laden und das skript über python ausführen. 


version8 enthält 3 Filter:
- Ist Teil eines Threads ja/nein = was nicht Teil eines eigenen Threads ist, wird gelöscht, wenn nicht von anderem Filter erfasst
- Mindestanzahl an Favs = Alles darunter wird gelöscht, wenn nicht von anderem Filter umfasst
- Mindestanzahl an Reskeets = Alles darunter wird gelöscht, wenn nicht von anderem Filter umfasst
- eigener like = Behält solche skeets, die man selbst geliket hat
- Datumsfilter = Nur Skeets vor dem eingegebenen Datum werden gelöscht und auch diese nur, soweit nicht ein anderer Filter sie behält

Die Filter verhalten sich alternativ zueinander = Nur skeets, die keine der Bedingungen erfüllen, werden gelöscht. Die Mindestanzahlen sind konfigurierbar


Das undo reposts.py macht genau das => reposts fremder skeets vor einem bestimmten datum werden rückgängig gemacht. das musste wegen anderer authentifizierung in ein separates programm (also _musste_ wahrscheinlich nicht, aber ich habs nicht sinnvoll in eine oberfläche bekommen)


keine haftung fuer irgendwas, benutzung auf eigene gefahr!!!
