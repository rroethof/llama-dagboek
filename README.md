# Ollama Chat met Permanent Geheugen

Een Streamlit webapplicatie die een chatinterface biedt met een lokaal draaiende Ollama Large Language Model (LLM), zoals Llama 3. De applicatie slaat chatgeschiedenis permanent op in een SQLite database, waardoor gebruikers meerdere sessies kunnen beheren, hernoemen, laden en verwijderen.

## Functionaliteiten

-   Chatten met een Ollama LLM (standaard geconfigureerd voor `llama3:8b`).
-   Permanente opslag van chatgeschiedenis per sessie in een SQLite database (`ollama_chat_history.db`).
-   Mogelijkheid om nieuwe chatsessies te starten.
-   Laden en hervatten van eerdere chatsessies vanuit de zijbalk.
-   Hernoemen van chatsessies voor betere organisatie.
-   Verwijderen van individuele chatsessies en hun bijbehorende data.
-   Gebruiksvriendelijke interface gebouwd met Streamlit.
-   Automatisch genereren van een tijdelijke titel voor nieuwe sessies.

## Vereisten

-   Python 3.8+
-   Ollama geïnstalleerd en werkend.
-   Een Ollama model gedownload (bijv. `llama3:8b`).
    -   Commando: `ollama pull llama3:8b`
-   Pip (Python package installer).

## Installatie

1.  **Kloon de repository:**
    ```bash
    git clone <jouw-repository-url>
    cd llama-dagboek
    ```

2.  **(Aanbevolen) Maak een virtuele omgeving aan en activeer deze:**
    ```bash
    python -m venv venv
    ```
    Op macOS/Linux:
    ```bash
    source venv/bin/activate
    ```
    Op Windows:
    ```bash
    venv\Scripts\activate
    ```

3.  **Installeer de benodigde Python packages:**
    Maak eerst een `requirements.txt` bestand aan in de hoofdmap van je project met de volgende inhoud:
    ```txt
    streamlit
    langchain-ollama
    langchain-core
    langchain
    langchain-community
    ```
    Installeer vervolgens de dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Zorg ervoor dat Ollama draait en het model beschikbaar is:**
    Controleer of de Ollama service actief is op je systeem. Als je het benodigde model (bijv. `llama3:8b`) nog niet hebt gedownload, doe dit dan met:
    ```bash
    ollama pull llama3:8b
    ```
    Je kunt het model dat de applicatie gebruikt aanpassen in `app.py` bij de `OllamaLLM` initialisatie.

## Applicatie Draaien

Voer het volgende commando uit in de hoofdmap van het project (waar `app.py` zich bevindt):

```bash
streamlit run app.py
```

De applicatie zal automatisch openen in je standaard webbrowser.

## Gebruik

-   **Chatten:** Typ je bericht in het invoerveld onderaan de pagina en druk op Enter. De AI zal antwoorden en het gesprek wordt opgeslagen.
-   **Sessiebeheer (in de zijbalk):**
    -   **Nieuwe Chat:** Klik hierop of selecteer het uit de dropdown om een volledig nieuwe conversatie te starten.
    -   **Kies een sessie:** Selecteer een eerdere chat uit de dropdownlijst om deze te laden en het gesprek voort te zetten. De lijst toont de titels van de sessies.
    -   **Titel Huidige Sessie:**
        -   Bekijk de huidige titel van de actieve chat. Nieuwe sessies krijgen een placeholder titel.
        -   Bewerk de titel in het tekstveld en klik op "Titel Opslaan" om de wijziging permanent te maken.
    -   **Sessie verwijderen:**
        -   Als een bestaande sessie is geladen, verschijnt hier een knop om die specifieke sessie te verwijderen.
        -   Er wordt een waarschuwing getoond. Het verwijderen is definitief en wist zowel de chatberichten als de sessietitel.
        -   Na verwijdering wordt automatisch een nieuwe, lege chatsessie gestart.

## Database

-   De chatgeschiedenis (berichten) en sessietitels worden opgeslagen in een SQLite databasebestand genaamd `ollama_chat_history.db`. Dit bestand wordt automatisch aangemaakt in de hoofdmap van het project als het nog niet bestaat.
-   De tabel `message_store` bevat de chatberichten, gelinkt via `session_id`.
-   De tabel `session_titles` bevat de aangepaste titels voor elke `session_id`.
-   Het `.gitignore` bestand is geconfigureerd om dit databasebestand (en gerelateerde SQLite-bestanden zoals `*-journal` en `*-wal`) te negeren, zodat het niet per ongeluk wordt meegecommit naar de Git repository.

## Model Configuratie

Het gebruikte Ollama model is standaard ingesteld op `"llama3:8b"` in `app.py`:

```python
# in app.py, binnen de functie get_ollama_llm()
return OllamaLLM(model="llama3:8b")
```

Je kunt `"llama3:8b"` vervangen door de naam van een ander model dat je lokaal met Ollama hebt gedownload (bijv. `"mistral"`, `"gemma:2b"`, etc.). Zorg ervoor dat het model daadwerkelijk beschikbaar is via Ollama.

```