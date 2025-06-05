import streamlit as st
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables import RunnablePassthrough
import uuid
import sqlite3
import os

# --- Streamlit Pagina Configuratie (MOET HET EERSTE STREAMLIT COMMANDO ZIJN) ---
st.set_page_config(page_title="Ollama Chat", layout="centered")

# --- Configuratie voor Permanent Geheugen ---
DB_FILE = "ollama_chat_history.db" # De naam van het SQLite databasebestand
DB_CONNECTION_STRING = f"sqlite:///{DB_FILE}"

# Gebruik st.cache_resource voor de LLM, omdat deze globaal en zwaar is
@st.cache_resource
def get_ollama_llm():
    """Initialiseert en cached de Ollama LLM."""
    # Zorg ervoor dat Ollama draait en het model is gedownload (bijv. ollama run llama3:8b)
    return OllamaLLM(model="llama3:8b")

# Functie om chat componenten voor een specifieke sessie te initialiseren
def get_session_chat_components(session_id: str):
    """Initialiseert chat geheugen en de conversatieketen voor een specifieke sessie ID."""
    try:
        message_history = SQLChatMessageHistory(
            session_id=session_id,
            connection=DB_CONNECTION_STRING
        )
    except TypeError:
        message_history = SQLChatMessageHistory(
            session_id=session_id,
            connection_string=DB_CONNECTION_STRING
        )

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=message_history,
        return_messages=True
    )

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", "Je bent een behulpzame AI-assistent."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{human_input}"),
        ]
    )

    conversation_chain = (
        RunnablePassthrough.assign(
            chat_history=lambda x: memory.load_memory_variables({})["chat_history"]
        )
        | prompt_template
        | get_ollama_llm()
    )
    return memory, conversation_chain

# --- Database functies voor sessietitels ---
def create_title_table_if_not_exists():
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_titles (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Fout bij het aanmaken van de sessietitel tabel: {e}")
    finally:
        if conn:
            conn.close()

def get_session_title(session_id: str) -> str:
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM session_titles WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        st.error(f"Fout bij het ophalen van de sessietitel: {e}")
        return None
    finally:
        if conn:
            conn.close()

def save_session_title(session_id: str, title: str):
    if not title.strip(): # Voorkom opslaan van lege titels (alleen spaties)
        st.warning("Titel kan niet leeg zijn. Vul een geldige titel in.")
        return
        
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO session_titles (session_id, title) VALUES (?, ?)
        """, (session_id, title.strip())) # .strip() verwijdert witruimte aan begin/einde
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Fout bij het opslaan van de sessietitel: {e}")
    finally:
        if conn:
            conn.close()

def delete_session_title(session_id: str):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM session_titles WHERE session_id = ?", (session_id,))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Fout bij het verwijderen van de sessietitel: {e}")
    finally:
        if conn:
            conn.close()

# Functie om alle sessie ID's en hun titels op te halen
def get_all_sessions_with_titles():
    create_title_table_if_not_exists() # Zorg ervoor dat de tabel bestaat
    if not os.path.exists(DB_FILE):
        return [] # Retourneer een lege lijst als het bestand nog niet bestaat
    
    conn = None
    sessions_data = []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Haal alle unieke sessie ID's op uit message_store (omdat SQLChatMessageHistory deze maakt)
        cursor.execute("PRAGMA table_info(message_store)")
        if not cursor.fetchall(): # Tabel message_store bestaat niet
            return []
            
        cursor.execute("SELECT DISTINCT session_id FROM message_store ORDER BY session_id DESC")
        raw_session_ids = [row[0] for row in cursor.fetchall()]

        # Haal titels op voor deze sessie ID's
        for session_id in raw_session_ids:
            title = get_session_title(session_id)
            if title is None or not title.strip(): # Als er geen titel is, of leeg, gebruik dan de placeholder
                title = f"(Zonder titel) {session_id[:8]}..."
            sessions_data.append({"id": session_id, "title": title})
        
        return sessions_data
    except sqlite3.Error as e:
        st.error(f"Fout bij het ophalen van sessie ID's en titels: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Functie om sessiegegevens te verwijderen (nu ook titel verwijderen)
def delete_session_data(session_id_to_delete: str):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM message_store WHERE session_id = ?", (session_id_to_delete,))
        conn.commit()
        # Verwijder ook de titel uit de session_titles tabel
        delete_session_title(session_id_to_delete) 
        st.success(f"Sessie '{session_id_to_delete}' en bijbehorende data succesvol verwijderd.")
    except sqlite3.Error as e:
        st.error(f"Fout bij het verwijderen van sessie data: {e}")
    finally:
        if conn:
            conn.close()


# --- Hoofd App Initialisatie (voor de sidebar, voor de eerste keer laden) ---
# Dit zorgt ervoor dat er ALTIJD een session_id en bijbehorende componenten zijn
# zodra de app start of na een rerun.
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) # Start met een nieuwe ID als er geen is
    st.session_state.memory, st.session_state.conversation_chain = \
        get_session_chat_components(st.session_state.session_id)


# --- Zijbalk voor Sessiebeheer ---
with st.sidebar:
    st.header("Sessiebeheer")

    all_sessions_with_titles = get_all_sessions_with_titles()
    current_active_session_id = st.session_state.session_id

    # Formatteer de opties voor de selectbox: "Titel (UUID)"
    session_display_options = ["Nieuwe Chat"] + [
        f"{s['title']}" for s in all_sessions_with_titles
    ]
    # Maak een dictionary voor snelle lookup: display_title -> session_id
    session_id_map = {f"{s['title']}": s['id'] for s in all_sessions_with_titles}
    
    # Bepaal de standaardindex voor de selectbox
    default_index = 0
    # Zoek de titel van de huidige actieve sessie
    current_active_session_title = next(
        (s['title'] for s in all_sessions_with_titles if s['id'] == current_active_session_id),
        None # Als geen titel gevonden, dan is het misschien een nieuwe ongetitelde chat
    )
    if current_active_session_title:
        try:
            default_index = session_display_options.index(current_active_session_title)
        except ValueError:
            # Kan gebeuren als de titel net is gewijzigd en de lijst nog niet is bijgewerkt
            # of als de sessie nieuw is en nog geen titel heeft.
            pass

    selected_display_option = st.selectbox(
        "Kies een sessie of start een nieuwe:",
        options=session_display_options,
        index=default_index,
        key="session_selector"
    )

    # --- Logica om sessie te wisselen/creëren ---
    should_rerun_for_session_change = False
    
    if selected_display_option == "Nieuwe Chat":
        # Controleer of de huidige actieve sessie een 'oude' (opgeslagen) sessie is,
        # OF als de huidige sessie nieuw is maar al berichten bevat (dus niet echt leeg is).
        # In die gevallen moeten we naar een echt nieuwe, lege sessie.
        if current_active_session_id in [s['id'] for s in all_sessions_with_titles] or st.session_state.memory.buffer:
            st.session_state.session_id = str(uuid.uuid4()) # Genereer een echt nieuwe UUID
            st.session_state.memory, st.session_state.conversation_chain = \
                get_session_chat_components(st.session_state.session_id)
            should_rerun_for_session_change = True
        # Anders (current_active_session_id is al een nieuwe lege sessie): niets doen, geen rerun.
        
    else: # Een bestaande sessie titel is geselecteerd
        # Zoek de echte session_id op basis van de geselecteerde titel
        actual_selected_session_id = session_id_map.get(selected_display_option)
        if actual_selected_session_id and actual_selected_session_id != current_active_session_id:
            st.session_state.session_id = actual_selected_session_id
            st.session_state.memory, st.session_state.conversation_chain = \
                get_session_chat_components(st.session_state.session_id)
            should_rerun_for_session_change = True

    if should_rerun_for_session_change:
        st.rerun()

    # --- Huidige sessie titel bewerken ---
    st.markdown("---")
    st.subheader("Titel Huidige Sessie")
    current_session_title_in_db = get_session_title(current_active_session_id)
    
    # Bepaal de initiële waarde voor het tekstinvoerveld
    # Als een titel bestaat in de DB, gebruik die. Anders, de "(Nieuwe sessie)" placeholder.
    text_input_initial_value = current_session_title_in_db if current_session_title_in_db else f"(Nieuwe sessie) {current_active_session_id[:8]}..."

    edited_title = st.text_input(
        "Bewerk titel:",
        value=text_input_initial_value, # Gebruik de bepaalde initiële waarde
        key="title_editor"
    )

    # De opslagknop is altijd zichtbaar, maar alleen geactiveerd als de titel is gewijzigd EN niet leeg is
    save_button_disabled = (edited_title.strip() == text_input_initial_value.strip()) or (not edited_title.strip())

    if st.button("Titel Opslaan", key="save_title_button", disabled=save_button_disabled):
        save_session_title(current_active_session_id, edited_title)
        # st.success bericht wordt al door save_session_title() gegeven als succesvol
        # of een waarschuwing als leeg.
        st.rerun() # Rerun om de dropdown bij te werken met de nieuwe titel

    st.markdown("---") 
    st.subheader("Sessie verwijderen")

    # Toon de delete knop alleen als een bestaande sessie is geselecteerd
    # Check nu met de 'echte' session_id's, niet met de display_options
    if current_active_session_id in [s['id'] for s in all_sessions_with_titles]:
        current_session_display_title = next(
            (s['title'] for s in all_sessions_with_titles if s['id'] == current_active_session_id),
            current_active_session_id # Fallback
        )
        st.warning(f"Weet je zeker dat je sessie '{current_session_display_title}' wilt verwijderen? Dit is definitief!")
        if st.button(f"Verwijder Sessie: {current_session_display_title}", key="delete_session_button"):
            session_to_delete = current_active_session_id
            delete_session_data(session_to_delete)

            # Na verwijdering: Ga naar een nieuwe chat sessie
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.memory, st.session_state.conversation_chain = \
                get_session_chat_components(st.session_state.session_id)
            
            st.success("Sessie succesvol verwijderd en een nieuwe chat gestart.")
            st.rerun() # Rerun om de lijst van sessies en de hoofdweergave bij te werken
    else:
        st.info("Selecteer een bestaande sessie om deze te kunnen verwijderen.")


# --- Streamlit UI Elementen (hoofdweergave) ---
st.title("Ollama Chat met Permanent Geheugen (SQLite)")

# Toon de chatgeschiedenis in de UI voor de huidige sessie
for message in st.session_state.memory.buffer:
    if isinstance(message, HumanMessage):
        st.chat_message("user").write(message.content)
    elif isinstance(message, AIMessage):
        st.chat_message("assistant").write(message.content)

# Inputveld voor de gebruiker
user_input = st.chat_input("Stel je vraag hier...")

if user_input:
    # Zorg ervoor dat het databasebestand bestaat voordat erin wordt geschreven
    if not os.path.exists(DB_FILE):
        open(DB_FILE, 'a').close()

    st.chat_message("user").write(user_input)
    with st.spinner("AI denkt na..."):
        response = st.session_state.conversation_chain.invoke({"human_input": user_input})

        st.session_state.memory.save_context(
            {"human_input": user_input},
            {"output": response}
        )
        st.chat_message("assistant").write(response)

st.markdown("---")
st.markdown(f"Het geheugen is permanent opgeslagen in `{DB_FILE}`.")
