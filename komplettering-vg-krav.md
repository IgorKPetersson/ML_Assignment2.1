# Komplettering — VG-krav uppfyllda

Nedan beskrivs hur varje VG-krav uppfylls i mitt GUI och min agent.

---

## VG1 — Underagenter körs parallellt

Huvudagenten kan starta upp till 3 underagenter parallellt via `ThreadPoolExecutor`.
Underagenterna är: `debug-agent` (hittar buggar), `test-agent` (föreslår testfall) och `verify-agent` (verifierar krav).

**Bevis:** Testet startar 3 simulerade agenter som var och en tar 0,3 s. Om de kördes en efter en skulle det ta 0,9 s totalt. Testet bekräftar att hela körningen slutförs på under 0,65 s — alltså parallellt.

**Demo-trigger:**
> Använd dina underagenter för att analysera workspace/hangman_game.py parallellt — en kontrollerar buggar, en föreslår testfall och en verifierar att kraven uppfylls.

---

## VG2 — Kontexten växer inte obegränsat

Konversationshistoriken trimmas till `MAX_CONTEXT_MESSAGES` innan varje modellanrop. Systemprompten och en compact notice bevaras alltid. Verktygsutdata kapas vid `MAX_TOOL_OUTPUT_CHARS` (standard 4 000 tecken) per sida.

**Bevis:** Testet fyller konversationen med 30 simulerade meddelanden och verifierar att modellen endast ser en nedkortad version. Verifierar även att lång verktygsutdata kapas vid 4 000 tecken.

**Synlig i körning:** När compaction triggar skrivs följande ut i GUI:t:
```
[CHAT COMPACTION] History: X msgs → Model sees: Y msgs (oldest Z dropped)
```

---

## VG3 — Kostnadsspårning, budgetvarning och hårt stopp

- Token-antal och uppskattad kostnad i USD visas efter varje steg.
- En varning injiceras i agentens kontext vid `TOKEN_WARNING_RATIO` (standard 80 %).
- Ett hårt stopp finns på **två ställen** i koden: före och efter varje modellanrop.

**Bevis:** Testet kontrollerar att användningssammanfattningen innehåller token-antal, kostnad och förbrukningstakt. Verifierar att varningen utlöses vid 80 % av budgeten och att det hårda stoppet finns på båda ställena i koden.

---

## VG4 — Farliga kommandon blockeras

Bash-kommandon valideras innan de når skalet via en tillåtningslista och en blockeringslista.

**Blockerat:** `rm`, `mv`, `cp`, `chmod`, `curl`, `wget`, `ssh` med flera.  
**Blockerade mönster:** `&&`, `|`, `;`, backticks, `$`, `>`, `<`, absoluta sökvägar, `.env`-filer, `find -delete`, `sed -i`.

**Bevis:** Testet försöker köra `rm -rf`, `cat /etc/passwd`, `cat .env`, kommandon med `&&`, `|`, `;`, backticks, `$HOME` och omdirigeringar — samtliga avvisas innan de når skalet.

---

## VG5 — Bash körs på riktigt

Agenten kör verkliga skalkommandon via `execute_bash` inuti Docker-containern med `workspace/` som arbetskatalog.

**Bevis:** Testet kör ett riktigt `ls` och verifierar att det returnerar faktisk utdata. Kör även `rm` och bekräftar att arbetskatalogen fortfarande finns (kommandot blockerades och kördes alltså inte).

---

## VG6 — Filredigering är kirurgisk

`edit_file_section` ersätter ett exakt avsnitt av en fil (find-and-replace av ett område), inte en hel filöverskrivning.

**Bevis:** Testet skapar en testfil med två funktioner, redigerar enbart den ena och verifierar att den andra funktionen är helt oförändrad.

---

## VG7 — Deploybar paketering

Hela agenten körs i Docker via `docker compose`. En `README.md` dokumenterar installationssteget: kopiera `.env.example`, bygg imagen och starta GUI:t. En icke-författare kan följa stegen utan hjälp.

```bash
docker compose build
python gui/server.py
```

Webbläsaren öppnas automatiskt på `http://localhost:8765`.

---

## VG8 — Konfiguration hämtas från miljön

All konfiguration finns i `config.py` och läses in från miljövariabler. Hemligheter kommer från `.env` (git-ignorerad). Ingen API-nyckel är hårdkodad någonstans i källkoden.

**Bevis:** Testet sätter `MODEL=_test_sentinel_` och verifierar att applikationen läser in värdet. Verifierar även att ingen API-nyckel är hårdkodad i källkoden.

---

## VG9 — Agenten avgör själv när den ska stanna

Modellen väljer varje tur om den ska anropa ett verktyg eller ge tillbaka kontrollen till användaren via `yield`. Ramverket tvingar aldrig ett stopp — enbart modellens eget `yield`-beslut eller det hårda token-taket avslutar en session.

**Bevis:** Testet kontrollerar att `yield` finns som en giltig åtgärd och att beslutet fattas inifrån loopen — alltså av modellen, inte av ett hårdkodat skript.
