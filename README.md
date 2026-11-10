# 🤖 Python Job Hunter Bot

Automatyczny asystent monitorujący oferty pracy dla **Junior / Intern Python Developer (Backend / Fullstack)**.

Pobiera najświeższe oferty, zapamiętuje je w lokalnej bazie SQLite, analizuje za pomocą **Gemini AI** (odrzuca fałszywych juniorów wymagających 3+ lat doświadczenia) i wysyła **natychmiastowe powiadomienie push na Twój telefon przez Telegram** – wyłącznie wtedy, gdy pojawi się nowa oferta.

---

## 🚀 Jak to działa?

1. **Zbieranie ofert:** Skrypt odpytuje bezpośrednie API portali (domyślnie NoFluffJobs) pod kątem kategorii `backend`, technologii `python` oraz poziomów `trainee, junior`.
2. **Deduplikacja:** Łączy regionalne powtórzenia (gdy firma wystawia tę samą ofertę na 10 miast) i sprawdza w bazie `data/jobs.db`, czy oferta nie była już przetwarzana.
3. **Analiza AI (Gemini):** Bada treść oferty i odsiewa ogłoszenia niezwiązane z programowaniem lub wymagające wieloletniego doświadczenia komercyjnego. Generuje 2-zdaniowe podsumowanie.
4. **Powiadomienie PUSH:** Jeśli oferta jest nowa i wartościowa, dostajesz wiadomość na Telegramie z bezpośrednim linkiem, widełkami i technologiami.
5. **Cisza przy braku nowości:** Jeśli danego dnia nie pojawi się żadna nowa oferta – bot nie wysyła nic.

---

## 🛠 Szybki start (Konfiguracja w 3 minuty)

### 1. Pobranie zależności
```bash
pip install -r requirements.txt
```

### 2. Utworzenie pliku `.env`
Skopiuj plik `.env.example` jako `.env`:
```bash
cp .env.example .env
```

### 3. Konfiguracja powiadomień (Wybierz Discord LUB Telegram):

#### Opcja A: Discord (Najprostsza – zalecana! Zajmuje 1 minutę)
Nie musisz rejestrować żadnego bota, wystarczy wbudowany **Webhook**:
1. Na swoim prywatnym serwerze Discord (lub stwórz nowy darmowy serwer jednym kliknięciem) wejdź w ustawienia dowolnego kanału tekstowego (np. `#oferty-pracy`).
2. Wybierz zakładkę **Integracje** -> **Webhooki** -> **Nowy webhook**.
3. Nadaj mu nazwę (np. `Job Hunter`) i kliknij **Kopiuj adres URL webhooka**.
4. Wklej ten adres do pliku `.env` jako `DISCORD_WEBHOOK_URL`.

#### Opcja B: Telegram (Alternatywa)
1. Wyszukaj bota **`@BotFather`** na Telegramie i wyślij `/newbot` -> skopiuj Token API do `TELEGRAM_BOT_TOKEN`.
2. Wyszukaj bota **`@userinfobot`**, kliknij Start i wklej swój identyfikator do `TELEGRAM_CHAT_ID`.
3. Wyślij do swojego nowo stworzonego bota wiadomość "Cześć".

### 4. Konfiguracja Gemini AI (opcjonalnie):
* Pobierz darmowy klucz API z [Google AI Studio](https://aistudio.google.com/app/apikey).
* Wklej go do `.env` jako `GEMINI_API_KEY`.
*(Jeśli nie podasz klucza, bot zadziała w trybie regułowym bez AI)*.

---

## 🧪 Przydatne komendy

* **Test powiadomień Discord:**
  ```bash
  python main.py --test-discord
  ```
* **Test powiadomień Telegram:**
  ```bash
  python main.py --test-telegram
  ```
* **Uruchomienie sprawdzania ofert:**
  ```bash
  python main.py
  ```
* **Zresetowanie bazy zapamiętanych ofert:**
  ```bash
  python main.py --reset-db
  ```

---

## ⏰ Jak zautomatyzować codzienne uruchamianie?

### Opcja A: Darmowa chmura (GitHub Actions - Polecane)
Bot może działać w chmurze bez włączania Twojego komputera:
1. Umieść kod w prywatnym repozytorium na GitHubie.
2. W ustawieniach repozytorium (**Settings -> Secrets and variables -> Actions**) dodaj:
   * `TELEGRAM_BOT_TOKEN`
   * `TELEGRAM_CHAT_ID`
   * `GEMINI_API_KEY`
3. Gotowy przepływ w `.github/workflows/check_jobs.yml` będzie sam uruchamiał bota 3 razy dziennie (np. 8:00, 13:00, 18:00) i automatycznie zapisywał stan bazy danych.

### Opcja B: Lokalnie na Windows (Harmonogram zadań / Task Scheduler)
1. Otwórz **Harmonogram zadań** w systemie Windows.
2. Utwórz zadanie podstawowe -> Uruchamiaj codziennie o wybranej godzinie.
3. Akcja: Uruchom program:
   * Program: `python` (lub pełna ścieżka do `python.exe`)
   * Argumenty: `main.py`
   * Rozpocznij w: `C:\Users\kacpe\Desktop\wyszu`

