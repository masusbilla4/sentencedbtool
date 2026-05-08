"""
Sentence Database Tool - Streamlit Web App
A web-based tool for managing sentence databases with filtering, export, and import capabilities.
"""

import streamlit as st
import sqlite3
import pandas as pd
import csv
import os
import random
from io import StringIO

# Page config
st.set_page_config(
    page_title="Sentence Database Tool",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .stat-card {
        background-color: #f8fafc;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
    }
    .stat-label {
        color: #64748b;
        font-size: 0.9rem;
    }
    /* Metric styling with visible text */
    div[data-testid="stMetric"] {
        background-color: #f1f5f9;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #cbd5e1;
    }
    div[data-testid="stMetric"] > label {
        color: #1e293b !important;
        font-weight: 600;
    }
    div[data-testid="stMetric"] > div {
        color: #0f172a !important;
        font-size: 1.8rem;
        font-weight: bold;
    }
    /* Dataframe styling */
    .stDataFrame {
        background-color: #ffffff;
    }
    /* Make sure text is visible in all elements */
    .stMetric label, .stMetric div {
        color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

# Database configuration
TABLE_NAME_FIL = "fil_sentences"
TABLE_NAME_ENG = "eng_sentences"

# Initialize session state
if 'db_path' not in st.session_state:
    st.session_state.db_path = None
if 'cart' not in st.session_state:
    st.session_state.cart = []

# ---------- DATABASE FUNCTIONS ----------

def connect_db():
    if st.session_state.db_path is None:
        return None
    return sqlite3.connect(st.session_state.db_path, timeout=10)

def get_table_name(language):
    return TABLE_NAME_ENG if language == "en" else TABLE_NAME_FIL

def ensure_tables_exist():
    conn = connect_db()
    if conn is None:
        return
    cursor = conn.cursor()
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME_FIL} (
            sen_id TEXT PRIMARY KEY,
            sentence TEXT,
            category TEXT,
            language TEXT,
            used INTEGER DEFAULT 0,
            char_count INTEGER,
            word_count INTEGER,
            sentence_count INTEGER
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME_ENG} (
            sen_id TEXT PRIMARY KEY,
            sentence TEXT,
            category TEXT,
            language TEXT,
            used INTEGER DEFAULT 0,
            char_count INTEGER,
            word_count INTEGER,
            sentence_count INTEGER
        )
    """)
    
    conn.commit()
    conn.close()

def generate_sen_id(language):
    prefix = "eng" if language == "en" else "fil"
    table_name = get_table_name(language)
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT sen_id FROM {table_name} ORDER BY sen_id DESC LIMIT 1")
    result = cursor.fetchone()
    
    if result:
        last_num = int(result[0].split('_')[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    
    conn.close()
    return f"{prefix}_{next_num:06d}"

def get_stats():
    conn = connect_db()
    if conn is None:
        return 0, 0, 0
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_FIL}")
    fil = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_ENG}")
    eng = cursor.fetchone()[0]
    
    conn.close()
    return fil + eng, eng, fil

def get_remaining_stats():
    conn = connect_db()
    if conn is None:
        return 0, 0
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_FIL} WHERE (used=0 OR used IS NULL)")
    fil = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_ENG} WHERE (used=0 OR used IS NULL)")
    eng = cursor.fetchone()[0]
    
    conn.close()
    return fil, eng

def get_categories():
    conn = connect_db()
    if conn is None:
        return []
    cursor = conn.cursor()
    
    categories = set()
    
    cursor.execute(f"SELECT DISTINCT category FROM {TABLE_NAME_FIL}")
    for row in cursor.fetchall():
        if row[0]:
            categories.add(row[0])
    
    cursor.execute(f"SELECT DISTINCT category FROM {TABLE_NAME_ENG}")
    for row in cursor.fetchall():
        if row[0]:
            categories.add(row[0])
    
    conn.close()
    return sorted(list(categories))

def get_category_stats():
    conn = connect_db()
    if conn is None:
        return []
    cursor = conn.cursor()
    
    categories = set()
    
    cursor.execute(f"SELECT DISTINCT category FROM {TABLE_NAME_FIL} WHERE category IS NOT NULL")
    for row in cursor.fetchall():
        categories.add(row[0])
    
    cursor.execute(f"SELECT DISTINCT category FROM {TABLE_NAME_ENG} WHERE category IS NOT NULL")
    for row in cursor.fetchall():
        categories.add(row[0])
    
    stats = []
    for cat in sorted(categories):
        entry = {"category": cat}
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_FIL} WHERE category=?", (cat,))
        entry["fil_total"] = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_FIL} WHERE category=? AND used=1", (cat,))
        entry["fil_used"] = cursor.fetchone()[0]
        entry["fil_remaining"] = entry["fil_total"] - entry["fil_used"]
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_ENG} WHERE category=?", (cat,))
        entry["eng_total"] = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_ENG} WHERE category=? AND used=1", (cat,))
        entry["eng_used"] = cursor.fetchone()[0]
        entry["eng_remaining"] = entry["eng_total"] - entry["eng_used"]
        
        stats.append(entry)
    
    conn.close()
    return stats

def get_all_sentences(language=None):
    conn = connect_db()
    if conn is None:
        return []
    cursor = conn.cursor()
    
    if language:
        table_name = get_table_name(language)
        cursor.execute(f"SELECT sen_id, sentence, category FROM {table_name} WHERE (used=0 OR used IS NULL)")
    else:
        cursor.execute(f"SELECT sen_id, sentence, category FROM {TABLE_NAME_FIL} WHERE (used=0 OR used IS NULL)")
        rows = cursor.fetchall()
        cursor.execute(f"SELECT sen_id, sentence, category FROM {TABLE_NAME_ENG} WHERE (used=0 OR used IS NULL)")
        rows.extend(cursor.fetchall())
        conn.close()
        return rows
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def search_sentences(keyword, language=None):
    conn = connect_db()
    if conn is None:
        return []
    cursor = conn.cursor()
    
    if language:
        table_name = get_table_name(language)
        cursor.execute(f"""
            SELECT sen_id, sentence, category FROM {table_name}
            WHERE sentence LIKE ? AND (used=0 OR used IS NULL)
        """, (f"%{keyword}%",))
    else:
        cursor.execute(f"""
            SELECT sen_id, sentence, category FROM {TABLE_NAME_FIL}
            WHERE sentence LIKE ? AND (used=0 OR used IS NULL)
        """, (f"%{keyword}%",))
        rows = cursor.fetchall()
        cursor.execute(f"""
            SELECT sen_id, sentence, category FROM {TABLE_NAME_ENG}
            WHERE sentence LIKE ? AND (used=0 OR used IS NULL)
        """, (f"%{keyword}%",))
        rows.extend(cursor.fetchall())
        conn.close()
        return rows
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def check_sentence_exists(sentence, language=None):
    """Check if a sentence already exists in the database.
    Returns (exists: bool, sen_id: str or None, category: str or None, language: str or None)"""
    conn = connect_db()
    if conn is None:
        return False, None, None, None
    cursor = conn.cursor()
    
    # Check in Filipino table
    cursor.execute(f"SELECT sen_id, category, language FROM {TABLE_NAME_FIL} WHERE sentence=?", (sentence,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return True, result[0], result[1], result[2]
    
    # Check in English table
    cursor.execute(f"SELECT sen_id, category, language FROM {TABLE_NAME_ENG} WHERE sentence=?", (sentence,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return True, result[0], result[1], result[2]
    
    conn.close()
    return False, None, None, None

def insert_sentence(sentence, category, language):
    conn = connect_db()
    cursor = conn.cursor()
    
    char_count = len(sentence)
    word_count = len(sentence.split())
    sentence_count = max(1, sentence.count('.') + sentence.count('?'))
    
    table_name = get_table_name(language)
    sen_id = generate_sen_id(language)
    
    cursor.execute(f"""
        INSERT INTO {table_name}
        (sen_id, sentence, category, language, used, char_count, word_count, sentence_count)
        VALUES (?, ?, ?, ?, 0, ?, ?, ?)
    """, (sen_id, sentence, category, language, char_count, word_count, sentence_count))
    
    conn.commit()
    conn.close()

def update_sentence(sen_id, text, language):
    conn = connect_db()
    cursor = conn.cursor()
    
    table_name = get_table_name(language)
    cursor.execute(f"""
        UPDATE {table_name}
        SET sentence=?
        WHERE sen_id=?
    """, (text, sen_id))
    
    conn.commit()
    conn.close()

def get_filtered_sentences(category, language, word_count):
    conn = connect_db()
    if conn is None:
        return []
    cursor = conn.cursor()
    
    table_name = get_table_name(language)
    
    query = f"SELECT sentence, category, language, word_count FROM {table_name} WHERE (used=0 OR used IS NULL)"
    params = []
    
    if category:
        query += " AND category=?"
        params.append(category)
    
    if word_count:
        query += " AND word_count=?"
        params.append(word_count)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def import_from_csv(csv_path, skip_duplicates=True):
    try:
        rows = []
        
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            for row in reader:
                if not row or not row[0].strip():
                    continue
                rows.append(row)
        
        if not rows:
            return 0, 0, "No valid sentences found in the CSV file."
        
        conn = connect_db()
        cursor = conn.cursor()
        
        start_id_en = 0
        start_id_fil = 0
        
        cursor.execute(f"SELECT sen_id FROM {TABLE_NAME_ENG} ORDER BY sen_id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            start_id_en = int(result[0].split('_')[-1])
        
        cursor.execute(f"SELECT sen_id FROM {TABLE_NAME_FIL} ORDER BY sen_id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            start_id_fil = int(result[0].split('_')[-1])
        
        imported = 0
        skipped = 0
        
        next_id_en = start_id_en
        next_id_fil = start_id_fil
        
        for row in rows:
            sentence = row[0].strip() if len(row) > 0 else ""
            category = row[1].strip() if len(row) > 1 else "imported"
            language = row[2].strip().lower() if len(row) > 2 else "fil"
            
            if language in ["en", "eng", "english"]:
                language = "en"
            elif language in ["fil", "filipino", "tagalog"]:
                language = "fil"
            else:
                language = "fil"
            
            if not sentence:
                continue
            
            table_name = get_table_name(language)
            
            if skip_duplicates:
                cursor.execute(f"SELECT sen_id FROM {table_name} WHERE sentence=?", (sentence,))
                if cursor.fetchone():
                    skipped += 1
                    continue
            
            char_count = len(sentence)
            word_count = len(sentence.split())
            sentence_count = max(1, sentence.count('.') + sentence.count('?'))
            
            if language == "en":
                next_id_en += 1
                sen_id = f"eng_{next_id_en:06d}"
            else:
                next_id_fil += 1
                sen_id = f"fil_{next_id_fil:06d}"
            
            cursor.execute(f"""
                INSERT INTO {table_name}
                (sen_id, sentence, category, language, used, char_count, word_count, sentence_count)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?)
            """, (sen_id, sentence, category, language, char_count, word_count, sentence_count))
            imported += 1
        
        conn.commit()
        conn.close()
        
        return imported, skipped, None
        
    except Exception as e:
        return 0, 0, str(e)

def mark_sentences_as_used(sentences):
    """Mark sentences as used in the database"""
    conn = connect_db()
    cursor = conn.cursor()
    
    marked_count = 0
    for sentence in sentences:
        table_name = get_table_name(sentence[2])  # sentence[2] is language
        cursor.execute(f"""
            UPDATE {table_name}
            SET used=1
            WHERE sentence=? AND category=? AND language=?
        """, (sentence[0], sentence[1], sentence[2]))
        marked_count += 1
    
    conn.commit()
    conn.close()
    return marked_count

def find_duplicate_sentences():
    """Find all duplicate sentences in the database.
    Returns a list of duplicates with their IDs and details."""
    conn = connect_db()
    if conn is None:
        return []
    cursor = conn.cursor()
    
    duplicates = []
    
    # Find duplicates in Filipino table
    cursor.execute(f"""
        SELECT sentence, COUNT(*) as count, GROUP_CONCAT(sen_id) as ids, GROUP_CONCAT(category) as categories
        FROM {TABLE_NAME_FIL}
        GROUP BY sentence
        HAVING COUNT(*) > 1
    """)
    for row in cursor.fetchall():
        sentence, count, ids, categories = row
        ids_list = ids.split(',')
        # Keep the first one, mark rest as duplicates
        duplicates.append({
            'sentence': sentence,
            'count': count,
            'ids': ids_list,
            'language': 'fil',
            'categories': categories.split(',')
        })
    
    # Find duplicates in English table
    cursor.execute(f"""
        SELECT sentence, COUNT(*) as count, GROUP_CONCAT(sen_id) as ids, GROUP_CONCAT(category) as categories
        FROM {TABLE_NAME_ENG}
        GROUP BY sentence
        HAVING COUNT(*) > 1
    """)
    for row in cursor.fetchall():
        sentence, count, ids, categories = row
        ids_list = ids.split(',')
        duplicates.append({
            'sentence': sentence,
            'count': count,
            'ids': ids_list,
            'language': 'en',
            'categories': categories.split(',')
        })
    
    conn.close()
    return duplicates

def delete_duplicate_sentences(duplicate_ids, language):
    """Delete specific duplicate sentences by their IDs.
    Returns the number of deleted records."""
    conn = connect_db()
    if conn is None:
        return 0
    cursor = conn.cursor()
    
    table_name = get_table_name(language)
    deleted_count = 0
    
    for sen_id in duplicate_ids:
        cursor.execute(f"DELETE FROM {table_name} WHERE sen_id=?", (sen_id,))
        deleted_count += 1
    
    conn.commit()
    conn.close()
    return deleted_count

def get_database_info():
    """Get detailed information about the database."""
    conn = connect_db()
    if conn is None:
        return None
    cursor = conn.cursor()
    
    info = {
        'fil_total': 0,
        'fil_used': 0,
        'fil_available': 0,
        'eng_total': 0,
        'eng_used': 0,
        'eng_available': 0,
        'categories': 0,
        'duplicates': 0
    }
    
    # Filipino stats
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_FIL}")
    info['fil_total'] = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_FIL} WHERE used=1")
    info['fil_used'] = cursor.fetchone()[0]
    info['fil_available'] = info['fil_total'] - info['fil_used']
    
    # English stats
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_ENG}")
    info['eng_total'] = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME_ENG} WHERE used=1")
    info['eng_used'] = cursor.fetchone()[0]
    info['eng_available'] = info['eng_total'] - info['eng_used']
    
    # Categories count
    cursor.execute(f"SELECT COUNT(DISTINCT category) FROM {TABLE_NAME_FIL} WHERE category IS NOT NULL")
    fil_cats = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(DISTINCT category) FROM {TABLE_NAME_ENG} WHERE category IS NOT NULL")
    eng_cats = cursor.fetchone()[0]
    info['categories'] = max(fil_cats, eng_cats)
    
    # Duplicates count
    cursor.execute(f"""
        SELECT SUM(cnt) FROM (
            SELECT COUNT(*) - 1 as cnt FROM {TABLE_NAME_FIL} GROUP BY sentence HAVING COUNT(*) > 1
        )
    """)
    result = cursor.fetchone()[0]
    fil_dups = result if result else 0
    
    cursor.execute(f"""
        SELECT SUM(cnt) FROM (
            SELECT COUNT(*) - 1 as cnt FROM {TABLE_NAME_ENG} GROUP BY sentence HAVING COUNT(*) > 1
        )
    """)
    result = cursor.fetchone()[0]
    eng_dups = result if result else 0
    
    info['duplicates'] = fil_dups + eng_dups
    
    conn.close()
    return info

# ---------- UI COMPONENTS ----------

def show_database_selector():
    st.title("📚 Sentence Database Tool")
    st.markdown("### Select or Create a Database")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📂 Open Existing Database")
        uploaded_db = st.file_uploader("Upload a .db file", type=["db"], key="db_uploader")
        
        if uploaded_db is not None:
            # Save uploaded file to temp location
            temp_path = os.path.join(os.getcwd(), uploaded_db.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_db.getbuffer())
            st.session_state.db_path = temp_path
            ensure_tables_exist()
            st.rerun()
    
    with col2:
        st.markdown("#### 📄 Create New from CSV")
        uploaded_csv = st.file_uploader("Upload a CSV file", type=["csv"], key="csv_uploader")
        
        if uploaded_csv is not None:
            new_db_name = st.text_input("New Database Name", value="sentences.db")
            
            if st.button("Create Database", type="primary"):
                # Save uploaded CSV
                temp_csv = os.path.join(os.getcwd(), "temp_upload.csv")
                with open(temp_csv, "wb") as f:
                    f.write(uploaded_csv.getbuffer())
                
                # Create database path
                st.session_state.db_path = os.path.join(os.getcwd(), new_db_name)
                ensure_tables_exist()
                
                # Import CSV
                imported, skipped, error = import_from_csv(temp_csv, skip_duplicates=True)
                
                # Clean up temp file
                os.remove(temp_csv)
                
                if error:
                    st.error(f"Error: {error}")
                else:
                    st.success(f"Database created! Imported: {imported}, Skipped: {skipped}")
                    st.rerun()

def show_home():
    st.title("📚 Sentence Database Tool")
    
    # Stats row
    total, eng, fil = get_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sentences", total)
    with col2:
        st.metric("English", eng, delta=None)
    with col3:
        st.metric("Filipino", fil, delta=None)
    
    st.divider()
    
    # Quick actions
    st.markdown("### Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Add Sentence", use_container_width=True):
            st.session_state.page = "add"
            st.rerun()
    
    with col2:
        if st.button("✏️ Edit Sentences", use_container_width=True):
            st.session_state.page = "edit"
            st.rerun()
    
    with col3:
        if st.button("🛒 Shop for Data", use_container_width=True):
            st.session_state.page = "shop"
            st.rerun()
    
    with col4:
        if st.button("📥 Import CSV", use_container_width=True):
            st.session_state.page = "import"
            st.rerun()
    
    st.divider()
    
    # Usage Distribution
    st.markdown("### 📊 Usage Distribution")
    
    stats = get_category_stats()
    
    if stats:
        # Summary stats
        fil_remaining, eng_remaining = get_remaining_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🟣 FIL Used", sum(e["fil_used"] for e in stats))
        with col2:
            st.metric("🟣 FIL Available", fil_remaining)
        with col3:
            st.metric("🟢 ENG Used", sum(e["eng_used"] for e in stats))
        with col4:
            st.metric("🟢 ENG Available", eng_remaining)
        
        # Category breakdown as DataFrame
        st.markdown("#### Category Breakdown")
        
        df_data = []
        for entry in stats:
            total_cat = entry["fil_total"] + entry["eng_total"]
            used_cat = entry["fil_used"] + entry["eng_used"]
            pct = (used_cat * 100 // total_cat) if total_cat > 0 else 0
            df_data.append({
                "Category": entry["category"],
                "FIL Total": entry["fil_total"],
                "FIL Used": entry["fil_used"],
                "ENG Total": entry["eng_total"],
                "ENG Used": entry["eng_used"],
                "Total": total_cat,
                "Used": used_cat,
                "Progress": f"{used_cat}/{total_cat} ({pct}%)"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No sentences in database yet. Add some sentences to see usage distribution!")

def show_add():
    st.title("➕ Add New Sentence")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    st.markdown("Enter a new sentence to the database")
    
    # Sentence input
    sentence = st.text_area("Sentence", height=100, placeholder="Enter your sentence here...")
    
    # Category input
    categories = get_categories()
    category = st.selectbox("Category", options=categories + ["Add New..."])
    
    if category == "Add New...":
        new_category = st.text_input("Enter New Category")
        if new_category:
            category = new_category
    
    # Language input
    language = st.radio("Language", options=["fil", "en"], format_func=lambda x: "Filipino" if x == "fil" else "English", horizontal=True)
    
    # Check for duplicates as user types
    if sentence.strip():
        exists, existing_id, existing_cat, existing_lang = check_sentence_exists(sentence.strip())
        if exists:
            st.warning(f"⚠️ **Duplicate detected!** This sentence already exists:\n\n"
                      f"- **ID:** {existing_id}\n"
                      f"- **Category:** {existing_cat}\n"
                      f"- **Language:** {'Filipino' if existing_lang == 'fil' else 'English'}")
    
    # Submit button
    if st.button("Add Sentence", type="primary"):
        if not sentence.strip():
            st.error("Sentence cannot be empty!")
        else:
            # Check for duplicate before inserting
            exists, existing_id, existing_cat, existing_lang = check_sentence_exists(sentence.strip())
            
            if exists:
                st.error(f"❌ Cannot add: This sentence already exists in the database!\n\n"
                        f"**Existing entry:**\n"
                        f"- ID: {existing_id}\n"
                        f"- Category: {existing_cat}\n"
                        f"- Language: {'Filipino' if existing_lang == 'fil' else 'English'}")
            else:
                insert_sentence(sentence.strip(), category, language)
                st.success("✅ Sentence added successfully!")
                st.rerun()

def show_edit():
    st.title("✏️ Edit Sentences")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    # Search
    search_keyword = st.text_input("🔍 Search", placeholder="Enter keyword to search...")
    
    # Get sentences
    if search_keyword:
        sentences = search_sentences(search_keyword)
    else:
        sentences = get_all_sentences()
    
    st.markdown(f"**Found: {len(sentences)} sentences**")
    
    if sentences:
        # Convert to DataFrame for display
        df = pd.DataFrame(sentences, columns=["ID", "Sentence", "Category"])
        
        # Display as editable dataframe
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Edit section
        st.markdown("### Edit Selected Sentence")
        
        selected_id = st.selectbox("Select Sentence ID to Edit", options=[s[0] for s in sentences])
        
        if selected_id:
            # Find the sentence
            selected_sentence = None
            selected_category = None
            selected_language = None
            
            for s in sentences:
                if s[0] == selected_id:
                    selected_sentence = s[1]
                    selected_category = s[2]
                    break
            
            # Determine language
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(f"SELECT language FROM {TABLE_NAME_ENG} WHERE sen_id=?", (selected_id,))
            result = cursor.fetchone()
            if result:
                selected_language = result[0]
            else:
                cursor.execute(f"SELECT language FROM {TABLE_NAME_FIL} WHERE sen_id=?", (selected_id,))
                result = cursor.fetchone()
                selected_language = result[0] if result else "fil"
            conn.close()
            
            # Edit form
            edited_sentence = st.text_area("Edit Sentence", value=selected_sentence, height=100)
            
            if st.button("Save Changes", type="primary"):
                update_sentence(selected_id, edited_sentence.strip(), selected_language)
                st.success("Sentence updated successfully!")
                st.rerun()
    else:
        st.info("No sentences found. Try a different search or add some sentences first.")

def show_shop():
    st.title("🛒 Shop for Data")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    # Remaining stats
    fil_remaining, eng_remaining = get_remaining_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📚 Remaining Filipino", fil_remaining)
    with col2:
        st.metric("📚 Remaining English", eng_remaining)
    
    st.divider()
    
    # Filter form
    st.markdown("### Filter Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = get_categories()
        category = st.selectbox("Category", options=["All"] + categories)
        category_filter = None if category == "All" else category
    
    with col2:
        language = st.radio("Language", options=["fil", "en"], format_func=lambda x: "Filipino" if x == "fil" else "English", horizontal=True)
    
    with col3:
        quantity = st.number_input("Quantity", min_value=1, max_value=1000, value=10)
    
    # Add to cart
    if st.button("🛒 Add to Cart", type="primary"):
        sentences = get_filtered_sentences(category_filter, language, None)
        
        # Filter out already in cart
        cart_sentences = set((item[0], item[1], item[2]) for item in st.session_state.cart)
        available = [s for s in sentences if (s[0], s[1], s[2]) not in cart_sentences]
        
        if available:
            selected = random.sample(available, min(quantity, len(available)))
            st.session_state.cart.extend(selected)
            st.success(f"Added {len(selected)} sentences to cart!")
        else:
            st.warning("No new sentences available (all might be in cart already)")
    
    st.divider()
    
    # Cart section
    st.markdown(f"### 🛒 Cart ({len(st.session_state.cart)} items)")
    
    if st.session_state.cart:
        # Display cart
        cart_df = pd.DataFrame(
            st.session_state.cart, 
            columns=["Sentence", "Category", "Language", "Words"]
        )
        st.dataframe(cart_df, use_container_width=True, hide_index=True)
        
        # Cart actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Clear Cart"):
                st.session_state.cart = []
                st.rerun()
        
        with col2:
            if st.button("🧹 Remove Selected"):
                st.info("To remove specific items, clear the cart and add items again.")
        
        with col3:
            # Export/Checkout
            if st.button("✅ Checkout & Export", type="primary"):
                # Prepare CSV
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["sentence", "category", "language", "word_count"])
                writer.writerows(st.session_state.cart)
                csv_buffer.seek(0)
                
                # Mark as used
                marked = mark_sentences_as_used(st.session_state.cart)
                
                # Clear cart
                st.session_state.cart = []
                
                # Download
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name="exported_sentences.csv",
                    mime="text/csv"
                )
                
                st.success(f"Checkout complete! {marked} sentences marked as used.")
    else:
        st.info("Your cart is empty. Add some sentences to get started!")

def show_import():
    st.title("📥 Import from CSV")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    # Current database info
    total, eng, fil = get_stats()
    st.markdown(f"**Current Database:** Total: {total} | English: {eng} | Filipino: {fil}")
    
    if st.session_state.db_path:
        st.markdown(f"**File:** `{st.session_state.db_path}`")
    
    st.divider()
    
    # Import options
    st.markdown("### Import CSV File")
    
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
    
    skip_duplicates = st.checkbox("Skip duplicate sentences", value=True)
    
    if uploaded_file is not None:
        # Preview
        st.markdown("#### Preview")
        
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head(10), use_container_width=True)
            st.markdown(f"**Total rows:** {len(df)}")
            
            # Import button
            if st.button("📥 Import & Merge", type="primary"):
                # Save temp file
                temp_path = os.path.join(os.getcwd(), "temp_import.csv")
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                imported, skipped, error = import_from_csv(temp_path, skip_duplicates)
                
                # Clean up
                os.remove(temp_path)
                
                if error:
                    st.error(f"Error: {error}")
                else:
                    st.success(f"Import complete! Imported: {imported}, Skipped: {skipped}")
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    
    st.divider()
    
    # Download template
    st.markdown("### 📄 CSV Template")
    
    template = "sentence,category,language\n"
    template += "Kumain ang bata ng mansanas.,Basic,fil\n"
    template += "The cat is on the table.,Basic,en\n"
    
    st.download_button(
        label="Download CSV Template",
        data=template,
        file_name="sentence_template.csv",
        mime="text/csv"
    )

# ---------- MAIN APP ----------

def main():
    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Navigation")
        
        if st.session_state.db_path:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.page = "home"
                st.rerun()
            if st.button("➕ Add Sentence", use_container_width=True):
                st.session_state.page = "add"
                st.rerun()
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state.page = "edit"
                st.rerun()
            if st.button("🛒 Shop", use_container_width=True):
                st.session_state.page = "shop"
                st.rerun()
            if st.button("📥 Import", use_container_width=True):
                st.session_state.page = "import"
                st.rerun()
            if st.button("⚙️ Manage DB", use_container_width=True):
                st.session_state.page = "manage"
                st.rerun()
            
            st.divider()
            
            if st.button("🔄 Change Database", use_container_width=True):
                st.session_state.db_path = None
                st.session_state.cart = []
                st.session_state.page = "home"
                st.rerun()
        else:
            st.info("Please select or create a database to get started.")
    
    # Main content
    if st.session_state.db_path is None:
        show_database_selector()
    else:
        if st.session_state.page == "home":
            show_home()
        elif st.session_state.page == "add":
            show_add()
        elif st.session_state.page == "edit":
            show_edit()
        elif st.session_state.page == "shop":
            show_shop()
        elif st.session_state.page == "import":
            show_import()
        elif st.session_state.page == "manage":
            show_manage()

def show_manage():
    st.title("⚙️ Database Management")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    # Database Info Section
    st.markdown("### 📊 Database Information")
    
    info = get_database_info()
    if info:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🟣 Filipino Total", info['fil_total'])
        with col2:
            st.metric("🟣 Filipino Available", info['fil_available'])
        with col3:
            st.metric("🟢 English Total", info['eng_total'])
        with col4:
            st.metric("🟢 English Available", info['eng_available'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📁 Categories", info['categories'])
        with col2:
            st.metric("⚠️ Duplicates Found", info['duplicates'])
    
    st.divider()
    
    # Duplicate Management Section
    st.markdown("### 🔍 Find & Delete Duplicates")
    
    # Scan for duplicates button
    if st.button("🔍 Scan for Duplicates", type="primary"):
        st.session_state.duplicates_found = find_duplicate_sentences()
    
    # Show duplicates if found
    if 'duplicates_found' in st.session_state:
        duplicates = st.session_state.duplicates_found
        
        if duplicates:
            st.warning(f"⚠️ Found **{len(duplicates)}** sentences with duplicates!")
            
            # Display duplicates in a table
            for i, dup in enumerate(duplicates):
                with st.expander(f"📝 Duplicate #{i+1}: {dup['sentence'][:50]}...", expanded=False):
                    st.markdown(f"**Sentence:** {dup['sentence']}")
                    st.markdown(f"**Language:** {'Filipino' if dup['language'] == 'fil' else 'English'}")
                    st.markdown(f"**Occurrences:** {dup['count']}")
                    
                    # Show all IDs
                    st.markdown("**All IDs:**")
                    for j, (sen_id, cat) in enumerate(zip(dup['ids'], dup['categories'])):
                        keep_text = "✅ (will keep)" if j == 0 else "❌ (will delete)"
                        st.markdown(f"- `{sen_id}` - Category: {cat} {keep_text}")
                    
                    # Delete button for this duplicate
                    ids_to_delete = dup['ids'][1:]  # Keep first, delete rest
                    if st.button(f"🗑️ Delete {len(ids_to_delete)} Duplicates", key=f"del_{i}"):
                        deleted = delete_duplicate_sentences(ids_to_delete, dup['language'])
                        st.success(f"✅ Deleted {deleted} duplicate(s)!")
                        # Clear the cache
                        if 'duplicates_found' in st.session_state:
                            del st.session_state.duplicates_found
                        st.rerun()
            
            # Delete all duplicates at once
            st.divider()
            if st.button("🗑️ Delete ALL Duplicates (Keep First Occurrence)", type="primary"):
                total_deleted = 0
                for dup in duplicates:
                    ids_to_delete = dup['ids'][1:]  # Keep first, delete rest
                    deleted = delete_duplicate_sentences(ids_to_delete, dup['language'])
                    total_deleted += deleted
                
                st.success(f"✅ Deleted **{total_deleted}** duplicate sentences!")
                # Clear the cache
                if 'duplicates_found' in st.session_state:
                    del st.session_state.duplicates_found
                st.rerun()
        
        else:
            st.success("✅ No duplicates found in the database!")
    
    st.divider()
    
    # Database Actions
    st.markdown("### 🗄️ Database Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Export Database")
        if st.button("📥 Export to CSV"):
            # Get all sentences
            conn = connect_db()
            cursor = conn.cursor()
            
            csv_data = "sentence,category,language,word_count,used\n"
            
            # Filipino sentences
            cursor.execute(f"SELECT sentence, category, language, word_count, used FROM {TABLE_NAME_FIL}")
            for row in cursor.fetchall():
                csv_data += f'"{row[0]}","{row[1]}","{row[2]}",{row[3]},{row[4]}\n'
            
            # English sentences
            cursor.execute(f"SELECT sentence, category, language, word_count, used FROM {TABLE_NAME_ENG}")
            for row in cursor.fetchall():
                csv_data += f'"{row[0]}","{row[1]}","{row[2]}",{row[3]},{row[4]}\n'
            
            conn.close()
            
            st.download_button(
                label="📥 Download Full Database CSV",
                data=csv_data,
                file_name="full_database_export.csv",
                mime="text/csv"
            )
    
    with col2:
        st.markdown("#### Database Statistics")
        if st.button("📊 Show Detailed Stats"):
            stats = get_category_stats()
            if stats:
                df = pd.DataFrame(stats)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No data to show.")

if __name__ == "__main__":
    main()
