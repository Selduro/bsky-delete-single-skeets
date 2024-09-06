Skript, das alle Einzelskeets eines Accounts, für den man obv Nutzername und Passwort braucht, findet und löscht. Einzelskeets sind solche eigenen Skeets, auf die nicht unmittelbar ein weiterer eigener Skeet als Antwort verfasst wurde. 

Rechtsklick auf bsky-delete-single-skeets.exe oder bsky-delete-single-skeets.py => Ziel speichern unter. Exe zum Ausführen doppelklicken und ggf. in windows defender zulassen. wenn ihr mir nicht traut, was ich empfehlen würde, dann den quellcode statt der exe laden und das skript über python ausführen. 


version4 enthält 3 Filter:
Ist Teil eines Threads;
Mindestanzahl an Favs;
Mindestanzahl an Reskeets

Die Filter verhalten sich alternativ zueinander = Nur skeets, die keine der drei Bedingungen erfüllen, werden gelöscht. Die Mindestanzahlen sind konfigurierbar


keine haftung fuer irgendwas, benutzung auf eigene gefahr.
