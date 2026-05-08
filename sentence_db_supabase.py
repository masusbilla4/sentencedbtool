"""
Sentence Database Tool - Streamlit Web App with Supabase
A web-based tool for managing sentence databases with real-time multi-user support.
"""

import streamlit as st
import pandas as pd
import csv
import os
import random
from io import StringIO, BytesIO
import sqlite3
from datetime import datetime

# Supabase imports
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Sentence Database Tool",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

# Table names
TABLE_FIL = "fil_sentences"
TABLE_ENG = "eng_sentences"

# Initialize session state
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'db_mode' not in st.session_state:
    st.session_state.db_mode = None  # 'supabase' or 'sqlite'
if 'supabase_client' not in st.session_state:
    st.session_state.supabase_client = None
if 'sqlite_path' not in st.session_state:
    st.session_state.sqlite_path = None

# ---------- SUPABASE FUNCTIONS ----------

def init_supabase(url: str, key: str) -> bool:
    """Initialize Supabase client."""
    try:
        st.session_state.supabase_client = create_client(url, key)
        st.session_state.db_mode = 'supabase'
        return True
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {str(e)}")
        return False

def get_supabase_client():
    """Get the Supabase client."""
    return st.session_state.supabase_client

# ---------- SQLITE FUNCTIONS ----------

def connect_sqlite():
    """Connect to local SQLite database."""
    if st.session_state.sqlite_path is None:
        return None
    return sqlite3.connect(st.session_state.sqlite_path, timeout=10)

def init_sqlite(db_path: str):
    """Initialize SQLite database."""
    st.session_state.sqlite_path = db_path
    conn = connect_sqlite()
    if conn is None:
        return False
    
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_FIL} (
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
        CREATE TABLE IF NOT EXISTS {TABLE_ENG} (
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
    st.session_state.db_mode = 'sqlite'
    return True

# ---------- UNIVERSAL DATABASE FUNCTIONS ----------

def get_table_name(language):
    return TABLE_ENG if language == "en" else TABLE_FIL

def generate_sen_id(language):
    prefix = "eng" if language == "en" else "fil"
    
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        table_name = get_table_name(language)
        
        result = client.table(table_name).select("sen_id").order("sen_id", desc=True).limit(1).execute()
        
        if result.data:
            last_num = int(result.data[0]['sen_id'].split('_')[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        
        return f"{prefix}_{next_num:06d}"
    
    else:  # SQLite
        conn = connect_sqlite()
        cursor = conn.cursor()
        table_name = get_table_name(language)
        
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
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        result_fil = client.table(TABLE_FIL).select("sen_id", count="exact").execute()
        fil = result_fil.count if hasattr(result_fil, 'count') else len(result_fil.data)
        
        result_eng = client.table(TABLE_ENG).select("sen_id", count="exact").execute()
        eng = result_eng.count if hasattr(result_eng, 'count') else len(result_eng.data)
        
        return fil + eng, eng, fil
    
    else:  # SQLite
        conn = connect_sqlite()
        if conn is None:
            return 0, 0, 0
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_FIL}")
        fil = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_ENG}")
        eng = cursor.fetchone()[0]
        
        conn.close()
        return fil + eng, eng, fil

def get_remaining_stats():
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        result_fil = client.table(TABLE_FIL).select("sen_id", count="exact").eq("used", 0).execute()
        fil = result_fil.count if hasattr(result_fil, 'count') else len(result_fil.data)
        
        result_eng = client.table(TABLE_ENG).select("sen_id", count="exact").eq("used", 0).execute()
        eng = result_eng.count if hasattr(result_eng, 'count') else len(result_eng.data)
        
        return fil, eng
    
    else:  # SQLite
        conn = connect_sqlite()
        if conn is None:
            return 0, 0
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_FIL} WHERE (used=0 OR used IS NULL)")
        fil = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_ENG} WHERE (used=0 OR used IS NULL)")
        eng = cursor.fetchone()[0]
        
        conn.close()
        return fil, eng

def get_categories():
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        result_fil = client.table(TABLE_FIL).select("category").execute()
        result_eng = client.table(TABLE_ENG).select("category").execute()
        
        categories = set()
        for row in result_fil.data:
            if row['category']:
                categories.add(row['category'])
        for row in result_eng.data:
            if row['category']:
                categories.add(row['category'])
        
        return sorted(list(categories))
    
    else:  # SQLite
        conn = connect_sqlite()
        if conn is None:
            return []
        cursor = conn.cursor()
        
        categories = set()
        
        cursor.execute(f"SELECT DISTINCT category FROM {TABLE_FIL}")
        for row in cursor.fetchall():
            if row[0]:
                categories.add(row[0])
        
        cursor.execute(f"SELECT DISTINCT category FROM {TABLE_ENG}")
        for row in cursor.fetchall():
            if row[0]:
                categories.add(row[0])
        
        conn.close()
        return sorted(list(categories))

def get_category_stats():
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        # Get all data
        result_fil = client.table(TABLE_FIL).select("*").execute()
        result_eng = client.table(TABLE_ENG).select("*").execute()
        
        categories = set()
        for row in result_fil.data:
            if row.get('category'):
                categories.add(row['category'])
        for row in result_eng.data:
            if row.get('category'):
                categories.add(row['category'])
        
        stats = []
        for cat in sorted(categories):
            entry = {"category": cat}
            
            fil_data = [r for r in result_fil.data if r.get('category') == cat]
            eng_data = [r for r in result_eng.data if r.get('category') == cat]
            
            entry["fil_total"] = len(fil_data)
            entry["fil_used"] = len([r for r in fil_data if r.get('used') == 1])
            entry["fil_remaining"] = entry["fil_total"] - entry["fil_used"]
            
            entry["eng_total"] = len(eng_data)
            entry["eng_used"] = len([r for r in eng_data if r.get('used') == 1])
            entry["eng_remaining"] = entry["eng_total"] - entry["eng_used"]
            
            stats.append(entry)
        
        return stats
    
    else:  # SQLite
        conn = connect_sqlite()
        if conn is None:
            return []
        cursor = conn.cursor()
        
        categories = set()
        
        cursor.execute(f"SELECT DISTINCT category FROM {TABLE_FIL} WHERE category IS NOT NULL")
        for row in cursor.fetchall():
            categories.add(row[0])
        
        cursor.execute(f"SELECT DISTINCT category FROM {TABLE_ENG} WHERE category IS NOT NULL")
        for row in cursor.fetchall():
            categories.add(row[0])
        
        stats = []
        for cat in sorted(categories):
            entry = {"category": cat}
            
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_FIL} WHERE category=?", (cat,))
            entry["fil_total"] = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_FIL} WHERE category=? AND used=1", (cat,))
            entry["fil_used"] = cursor.fetchone()[0]
            entry["fil_remaining"] = entry["fil_total"] - entry["fil_used"]
            
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_ENG} WHERE category=?", (cat,))
            entry["eng_total"] = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_ENG} WHERE category=? AND used=1", (cat,))
            entry["eng_used"] = cursor.fetchone()[0]
            entry["eng_remaining"] = entry["eng_total"] - entry["eng_used"]
            
            stats.append(entry)
        
        conn.close()
        return stats

def check_sentence_exists(sentence, language=None):
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        result = client.table(TABLE_FIL).select("sen_id,category,language").eq("sentence", sentence).execute()
        if result.data:
            row = result.data[0]
            return True, row['sen_id'], row['category'], row['language']
        
        result = client.table(TABLE_ENG).select("sen_id,category,language").eq("sentence", sentence).execute()
        if result.data:
            row = result.data[0]
            return True, row['sen_id'], row['category'], row['language']
        
        return False, None, None, None
    
    else:  # SQLite
        conn = connect_sqlite()
        if conn is None:
            return False, None, None, None
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT sen_id, category, language FROM {TABLE_FIL} WHERE sentence=?", (sentence,))
        result = cursor.fetchone()
        if result:
            conn.close()
            return True, result[0], result[1], result[2]
        
        cursor.execute(f"SELECT sen_id, category, language FROM {TABLE_ENG} WHERE sentence=?", (sentence,))
        result = cursor.fetchone()
        if result:
            conn.close()
            return True, result[0], result[1], result[2]
        
        conn.close()
        return False, None, None, None

def insert_sentence(sentence, category, language):
    char_count = len(sentence)
    word_count = len(sentence.split())
    sentence_count = max(1, sentence.count('.') + sentence.count('?'))
    
    table_name = get_table_name(language)
    sen_id = generate_sen_id(language)
    
    data = {
        "sen_id": sen_id,
        "sentence": sentence,
        "category": category,
        "language": language,
        "used": 0,
        "char_count": char_count,
        "word_count": word_count,
        "sentence_count": sentence_count
    }
    
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        client.table(table_name).insert(data).execute()
    
    else:  # SQLite
        conn = connect_sqlite()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            INSERT INTO {table_name}
            (sen_id, sentence, category, language, used, char_count, word_count, sentence_count)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?)
        """, (sen_id, sentence, category, language, char_count, word_count, sentence_count))
        
        conn.commit()
        conn.close()

def get_all_sentences(language=None):
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        sentences = []
        
        if language:
            table_name = get_table_name(language)
            result = client.table(table_name).select("sen_id,sentence,category").eq("used", 0).execute()
            for row in result.data:
                sentences.append((row['sen_id'], row['sentence'], row['category']))
        else:
            result_fil = client.table(TABLE_FIL).select("sen_id,sentence,category").eq("used", 0).execute()
            for row in result_fil.data:
                sentences.append((row['sen_id'], row['sentence'], row['category']))
            
            result_eng = client.table(TABLE_ENG).select("sen_id,sentence,category").eq("used", 0).execute()
            for row in result_eng.data:
                sentences.append((row['sen_id'], row['sentence'], row['category']))
        
        return sentences
    
    else:  # SQLite
        conn = connect_sqlite()
        if conn is None:
            return []
        cursor = conn.cursor()
        
        if language:
            table_name = get_table_name(language)
            cursor.execute(f"SELECT sen_id, sentence, category FROM {table_name} WHERE (used=0 OR used IS NULL)")
        else:
            cursor.execute(f"SELECT sen_id, sentence, category FROM {TABLE_FIL} WHERE (used=0 OR used IS NULL)")
            rows = cursor.fetchall()
            cursor.execute(f"SELECT sen_id, sentence, category FROM {TABLE_ENG} WHERE (used=0 OR used IS NULL)")
            rows.extend(cursor.fetchall())
            conn.close()
            return rows
        
        rows = cursor.fetchall()
        conn.close()
        return rows

def search_sentences(keyword, language=None):
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        sentences = []
        search_pattern = f"%{keyword}%"
        
        if language:
            table_name = get_table_name(language)
            result = client.table(table_name).select("sen_id,sentence,category").ilike("sentence", search_pattern).eq("used", 0).execute()
            for row in result.data:
                sentences.append((row['sen_id'], row['sentence'], row['category']))
        else:
            result_fil = client.table(TABLE_FIL).select("sen_id,sentence,category").ilike("sentence", search_pattern).eq("used", 0).execute()
            for row in result_fil.data:
                sentences.append((row['sen_id'], row['sentence'], row['category']))
            
            result_eng = client.table(TABLE_ENG).select("sen_id,sentence,category").ilike("sentence", search_pattern).eq("used", 0).execute()
            for row in result_eng.data:
                sentences.append((row['sen_id'], row['sentence'], row['category']))
        
        return sentences
    
    else:  # SQLite
        conn = connect_sqlite()
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
                SELECT sen_id, sentence, category FROM {TABLE_FIL}
                WHERE sentence LIKE ? AND (used=0 OR used IS NULL)
            """, (f"%{keyword}%",))
            rows = cursor.fetchall()
            cursor.execute(f"""
                SELECT sen_id, sentence, category FROM {TABLE_ENG}
                WHERE sentence LIKE ? AND (used=0 OR used IS NULL)
            """, (f"%{keyword}%",))
            rows.extend(cursor.fetchall())
            conn.close()
            return rows
        
        rows = cursor.fetchall()
        conn.close()
        return rows

def get_filtered_sentences(category, language, word_count):
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        table_name = get_table_name(language)
        
        query = client.table(table_name).select("sentence,category,language,word_count").eq("used", 0)
        
        if category:
            query = query.eq("category", category)
        
        result = query.execute()
        
        sentences = []
        for row in result.data:
            if word_count is None or row.get('word_count') == word_count:
                sentences.append((row['sentence'], row['category'], row['language'], row.get('word_count', 0)))
        
        return sentences
    
    else:  # SQLite
        conn = connect_sqlite()
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

def update_sentence(sen_id, text, language):
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        table_name = get_table_name(language)
        
        client.table(table_name).update({"sentence": text}).eq("sen_id", sen_id).execute()
    
    else:  # SQLite
        conn = connect_sqlite()
        cursor = conn.cursor()
        table_name = get_table_name(language)
        
        cursor.execute(f"UPDATE {table_name} SET sentence=? WHERE sen_id=?", (text, sen_id))
        
        conn.commit()
        conn.close()

def mark_sentences_as_used(sentences):
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        marked_count = 0
        
        for sentence in sentences:
            table_name = get_table_name(sentence[2])
            client.table(table_name).update({"used": 1}).eq("sentence", sentence[0]).eq("category", sentence[1]).execute()
            marked_count += 1
        
        return marked_count
    
    else:  # SQLite
        conn = connect_sqlite()
        cursor = conn.cursor()
        marked_count = 0
        
        for sentence in sentences:
            table_name = get_table_name(sentence[2])
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
    """Find duplicate sentences in the database."""
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        duplicates = []
        
        for table in [TABLE_FIL, TABLE_ENG]:
            result = client.table(table).select("*").execute()
            
            # Group by sentence
            sentence_groups = {}
            for row in result.data:
                sent = row['sentence']
                if sent not in sentence_groups:
                    sentence_groups[sent] = []
                sentence_groups[sent].append(row)
            
            # Find duplicates
            for sentence, rows in sentence_groups.items():
                if len(rows) > 1:
                    duplicates.append({
                        'sentence': sentence,
                        'count': len(rows),
                        'ids': [r['sen_id'] for r in rows],
                        'language': rows[0]['language'],
                        'categories': [r['category'] for r in rows]
                    })
        
        return duplicates
    
    else:  # SQLite
        conn = connect_sqlite()
        if conn is None:
            return []
        cursor = conn.cursor()
        duplicates = []
        
        for table in [TABLE_FIL, TABLE_ENG]:
            cursor.execute(f"""
                SELECT sentence, COUNT(*) as count, GROUP_CONCAT(sen_id) as ids, GROUP_CONCAT(category) as categories
                FROM {table}
                GROUP BY sentence
                HAVING COUNT(*) > 1
            """)
            
            for row in cursor.fetchall():
                sentence, count, ids, categories = row
                cursor2 = conn.cursor()
                cursor2.execute(f"SELECT language FROM {table} WHERE sentence=? LIMIT 1", (sentence,))
                lang_result = cursor2.fetchone()
                language = lang_result[0] if lang_result else 'fil'
                
                duplicates.append({
                    'sentence': sentence,
                    'count': count,
                    'ids': ids.split(','),
                    'language': language,
                    'categories': categories.split(',')
                })
        
        conn.close()
        return duplicates

def delete_duplicate_sentences(duplicate_ids, language):
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        table_name = get_table_name(language)
        
        deleted_count = 0
        for sen_id in duplicate_ids:
            client.table(table_name).delete().eq("sen_id", sen_id).execute()
            deleted_count += 1
        
        return deleted_count
    
    else:  # SQLite
        conn = connect_sqlite()
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
    total, eng, fil = get_stats()
    fil_remaining, eng_remaining = get_remaining_stats()
    
    categories = get_categories()
    
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        # Count duplicates
        duplicates = 0
        for table in [TABLE_FIL, TABLE_ENG]:
            result = client.table(table).select("sentence").execute()
            sentences = [r['sentence'] for r in result.data]
            dup_counts = {}
            for s in sentences:
                dup_counts[s] = dup_counts.get(s, 0) + 1
            for s, c in dup_counts.items():
                if c > 1:
                    duplicates += c - 1
        
        return {
            'fil_total': fil,
            'fil_used': fil - fil_remaining,
            'fil_available': fil_remaining,
            'eng_total': eng,
            'eng_used': eng - eng_remaining,
            'eng_available': eng_remaining,
            'categories': len(categories),
            'duplicates': duplicates
        }
    
    else:  # SQLite
        conn = connect_sqlite()
        cursor = conn.cursor()
        
        # Count duplicates
        fil_dups = 0
        eng_dups = 0
        
        cursor.execute(f"""
            SELECT SUM(cnt) FROM (
                SELECT COUNT(*) - 1 as cnt FROM {TABLE_FIL} GROUP BY sentence HAVING COUNT(*) > 1
            )
        """)
        result = cursor.fetchone()[0]
        fil_dups = result if result else 0
        
        cursor.execute(f"""
            SELECT SUM(cnt) FROM (
                SELECT COUNT(*) - 1 as cnt FROM {TABLE_ENG} GROUP BY sentence HAVING COUNT(*) > 1
            )
        """)
        result = cursor.fetchone()[0]
        eng_dups = result if result else 0
        
        conn.close()
        
        return {
            'fil_total': fil,
            'fil_used': fil - fil_remaining,
            'fil_available': fil_remaining,
            'eng_total': eng,
            'eng_used': eng - eng_remaining,
            'eng_available': eng_remaining,
            'categories': len(categories),
            'duplicates': fil_dups + eng_dups
        }

# ---------- IMPORT/EXPORT FUNCTIONS ----------

def import_from_csv_to_db(csv_content, skip_duplicates=True):
    """Import sentences from CSV content."""
    try:
        lines = csv_content.strip().split('\n')
        reader = csv.reader(lines)
        header = next(reader, None)
        
        if not header:
            return 0, 0, "Empty CSV file"
        
        imported = 0
        skipped = 0
        
        for row in reader:
            if not row or not row[0].strip():
                continue
            
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
            
            # Check for duplicates
            if skip_duplicates:
                exists, _, _, _ = check_sentence_exists(sentence, language)
                if exists:
                    skipped += 1
                    continue
            
            insert_sentence(sentence, category, language)
            imported += 1
        
        return imported, skipped, None
    
    except Exception as e:
        return 0, 0, str(e)

def export_to_csv_string():
    """Export database to CSV string."""
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["sentence", "category", "language", "word_count", "used"])
    
    if st.session_state.db_mode == 'supabase':
        client = get_supabase_client()
        
        for table in [TABLE_FIL, TABLE_ENG]:
            result = client.table(table).select("*").execute()
            for row in result.data:
                writer.writerow([
                    row['sentence'],
                    row['category'],
                    row['language'],
                    row.get('word_count', 0),
                    row.get('used', 0)
                ])
    else:
        conn = connect_sqlite()
        cursor = conn.cursor()
        
        for table in [TABLE_FIL, TABLE_ENG]:
            cursor.execute(f"SELECT sentence, category, language, word_count, used FROM {table}")
            for row in cursor.fetchall():
                writer.writerow(row)
        
        conn.close()
    
    return csv_buffer.getvalue()

def import_from_sqlite_file(uploaded_file):
    """Import sentences from an uploaded SQLite file."""
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_import_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()
        
        imported = 0
        skipped = 0
        
        for table in [TABLE_FIL, TABLE_ENG]:
            try:
                cursor.execute(f"SELECT sentence, category, language FROM {table}")
                for row in cursor.fetchall():
                    sentence, category, language = row
                    
                    exists, _, _, _ = check_sentence_exists(sentence, language)
                    if exists:
                        skipped += 1
                        continue
                    
                    insert_sentence(sentence, category or "imported", language or "fil")
                    imported += 1
            except:
                pass  # Table might not exist
        
        conn.close()
        os.remove(temp_path)
        
        return imported, skipped, None
    
    except Exception as e:
        return 0, 0, str(e)

# ---------- UI COMPONENTS ----------

def show_database_selector():
    """Show the database selection page with three options."""
    st.title("📚 Sentence Database Tool")
    st.markdown("### Choose Your Database Option")
    
    st.markdown("---")
    
    # Option 1: Cloud Database
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### ☁️ Cloud Database")
        st.markdown("Connect to Supabase for **real-time multi-user** access.")
        st.markdown("- ✅ Multiple users simultaneously")
        st.markdown("- ✅ Data persists in cloud")
        st.markdown("- ✅ Real-time updates")
        
        if st.button("🚀 Connect to Cloud", type="primary", use_container_width=True, key="btn_cloud"):
            # Initialize Supabase from secrets
            try:
                url = st.secrets.get("SUPABASE_URL", "")
                key = st.secrets.get("SUPABASE_KEY", "")
                
                if not url or not key:
                    st.error("❌ Supabase credentials not found in secrets!")
                    st.markdown("**How to add secrets:**")
                    st.markdown("1. Go to Streamlit Cloud Dashboard")
                    st.markdown("2. Click Settings → Secrets")
                    st.markdown("3. Add SUPABASE_URL and SUPABASE_KEY")
                else:
                    if init_supabase(url, key):
                        st.session_state.db_mode = 'supabase'
                        st.rerun()
            except Exception as e:
                st.error(f"Error connecting to cloud: {str(e)}")
    
    with col2:
        st.markdown("#### 🔗 Combine Databases")
        st.markdown("Upload SQLite file and **merge** with cloud database.")
        st.markdown("- ✅ Import existing data")
        st.markdown("- ✅ Keeps cloud data")
        st.markdown("- ✅ Skips duplicates")
        
        uploaded_db = st.file_uploader("Upload .db file", type=["db"], key="combine_uploader")
        
        if uploaded_db is not None:
            if st.button("📥 Import & Merge", type="primary", use_container_width=True, key="btn_combine"):
                # First connect to Supabase
                url = st.secrets.get("SUPABASE_URL", "")
                key = st.secrets.get("SUPABASE_KEY", "")
                
                if not url or not key:
                    st.error("❌ Supabase credentials not found!")
                else:
                    if init_supabase(url, key):
                        with st.spinner("Importing data to cloud..."):
                            imported, skipped, error = import_from_sqlite_file(uploaded_db)
                        
                        if error:
                            st.error(f"Error: {error}")
                        else:
                            st.success(f"✅ Imported: {imported} | Skipped (duplicates): {skipped}")
                            st.session_state.db_mode = 'supabase'
                            st.rerun()
    
    with col3:
        st.markdown("#### 📄 Import from CSV")
        st.markdown("Create database from **CSV file** upload.")
        st.markdown("- ✅ Start fresh")
        st.markdown("- ✅ Simple format")
        st.markdown("- ✅ Bulk import")
        
        uploaded_csv = st.file_uploader("Upload .csv file", type=["csv"], key="csv_uploader")
        
        if uploaded_csv is not None:
            if st.button("📥 Import CSV", type="primary", use_container_width=True, key="btn_csv"):
                # First connect to Supabase
                url = st.secrets.get("SUPABASE_URL", "")
                key = st.secrets.get("SUPABASE_KEY", "")
                
                if not url or not key:
                    st.error("❌ Supabase credentials not found!")
                else:
                    if init_supabase(url, key):
                        with st.spinner("Importing CSV to cloud..."):
                            csv_content = uploaded_csv.read().decode('utf-8')
                            imported, skipped, error = import_from_csv_to_db(csv_content, skip_duplicates=True)
                        
                        if error:
                            st.error(f"Error: {error}")
                        else:
                            st.success(f"✅ Imported: {imported} | Skipped (duplicates): {skipped}")
                            st.session_state.db_mode = 'supabase'
                            st.rerun()
    
    st.markdown("---")
    
    # CSV Format Help
    with st.expander("📋 CSV Format Guide"):
        st.markdown("""
        **Required format:**
        ```csv
        sentence,category,language
        Your sentence here.,Basic,fil
        Another sentence.,Daily,en
        ```
        
        | Column | Required | Description |
        |--------|----------|-------------|
        | sentence | ✅ Yes | The sentence text |
        | category | ✅ Yes | Category name |
        | language | Optional | `fil` or `en` (defaults to `fil`) |
        """)
    
    # Local SQLite Option (collapsed)
    with st.expander("💻 Use Local SQLite (Offline Mode)"):
        st.markdown("For offline use or local testing only. **Multi-user not supported.**")
        
        uploaded_local_db = st.file_uploader("Upload existing .db file (optional)", type=["db"], key="local_uploader")
        new_db_name = st.text_input("Database name", value="sentences.db")
        
        if st.button("📂 Open Local Database", key="btn_local"):
            if uploaded_local_db is not None:
                temp_path = os.path.join(os.getcwd(), uploaded_local_db.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_local_db.getbuffer())
                init_sqlite(temp_path)
            else:
                init_sqlite(os.path.join(os.getcwd(), new_db_name))
            st.rerun()

def show_home():
    st.title("📚 Sentence Database Tool")
    
    # Show current database mode
    if st.session_state.db_mode == 'supabase':
        st.info("☁️ **Connected to Cloud Database** - Multi-user mode")
    else:
        st.info("💻 **Local Database** - Single user mode")
    
    # Stats row
    total, eng, fil = get_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sentences", total)
    with col2:
        st.metric("English", eng)
    with col3:
        st.metric("Filipino", fil)
    
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
        if st.button("📥 Import", use_container_width=True):
            st.session_state.page = "import"
            st.rerun()
    
    st.divider()
    
    # Usage Distribution
    st.markdown("### 📊 Usage Distribution")
    
    stats = get_category_stats()
    
    if stats:
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
        st.info("No sentences in database yet. Add some sentences or import from CSV/SQLite!")

# ---------- ADDITIONAL UI PAGES ----------

def show_add():
    st.title("➕ Add New Sentence")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    st.markdown("Enter a new sentence to the database")
    
    sentence = st.text_area("Sentence", height=100, placeholder="Enter your sentence here...")
    
    categories = get_categories()
    category = st.selectbox("Category", options=categories + ["Add New..."])
    
    if category == "Add New...":
        new_category = st.text_input("Enter New Category")
        if new_category:
            category = new_category
    
    language = st.radio("Language", options=["fil", "en"], format_func=lambda x: "Filipino" if x == "fil" else "English", horizontal=True)
    
    if sentence.strip():
        exists, existing_id, existing_cat, existing_lang = check_sentence_exists(sentence.strip())
        if exists:
            st.warning(f"⚠️ **Duplicate detected!** This sentence already exists:\n\n"
                      f"- **ID:** {existing_id}\n"
                      f"- **Category:** {existing_cat}\n"
                      f"- **Language:** {'Filipino' if existing_lang == 'fil' else 'English'}")
    
    if st.button("Add Sentence", type="primary"):
        if not sentence.strip():
            st.error("Sentence cannot be empty!")
        else:
            exists, existing_id, existing_cat, existing_lang = check_sentence_exists(sentence.strip())
            
            if exists:
                st.error(f"❌ Cannot add: This sentence already exists!")
            else:
                insert_sentence(sentence.strip(), category, language)
                st.success("✅ Sentence added successfully!")
                st.rerun()

def show_edit():
    st.title("✏️ Edit Sentences")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    search_keyword = st.text_input("🔍 Search", placeholder="Enter keyword to search...")
    
    if search_keyword:
        sentences = search_sentences(search_keyword)
    else:
        sentences = get_all_sentences()
    
    st.markdown(f"**Found: {len(sentences)} sentences**")
    
    if sentences:
        df = pd.DataFrame(sentences, columns=["ID", "Sentence", "Category"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("### Edit Selected Sentence")
        
        selected_id = st.selectbox("Select Sentence ID to Edit", options=[s[0] for s in sentences])
        
        if selected_id:
            selected_sentence = None
            selected_language = None
            
            for s in sentences:
                if s[0] == selected_id:
                    selected_sentence = s[1]
                    break
            
            if st.session_state.db_mode == 'supabase':
                client = get_supabase_client()
                result = client.table(TABLE_ENG).select("language").eq("sen_id", selected_id).execute()
                if result.data:
                    selected_language = result.data[0]['language']
                else:
                    result = client.table(TABLE_FIL).select("language").eq("sen_id", selected_id).execute()
                    selected_language = result.data[0]['language'] if result.data else "fil"
            
            edited_sentence = st.text_area("Edit Sentence", value=selected_sentence, height=100)
            
            if st.button("Save Changes", type="primary"):
                update_sentence(selected_id, edited_sentence.strip(), selected_language)
                st.success("Sentence updated successfully!")
                st.rerun()
    else:
        st.info("No sentences found.")

def show_shop():
    st.title("🛒 Shop for Data")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    fil_remaining, eng_remaining = get_remaining_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📚 Remaining Filipino", fil_remaining)
    with col2:
        st.metric("📚 Remaining English", eng_remaining)
    
    st.divider()
    
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
    
    if st.button("🛒 Add to Cart", type="primary"):
        sentences = get_filtered_sentences(category_filter, language, None)
        
        cart_sentences = set((item[0], item[1], item[2]) for item in st.session_state.cart)
        available = [s for s in sentences if (s[0], s[1], s[2]) not in cart_sentences]
        
        if available:
            selected = random.sample(available, min(quantity, len(available)))
            st.session_state.cart.extend(selected)
            st.success(f"Added {len(selected)} sentences to cart!")
        else:
            st.warning("No new sentences available")
    
    st.divider()
    
    st.markdown(f"### 🛒 Cart ({len(st.session_state.cart)} items)")
    
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart, columns=["Sentence", "Category", "Language", "Words"])
        st.dataframe(cart_df, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Cart"):
                st.session_state.cart = []
                st.rerun()
        
        with col2:
            if st.button("✅ Checkout & Export", type="primary"):
                csv_buffer = StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["sentence", "category", "language", "word_count"])
                writer.writerows(st.session_state.cart)
                
                marked = mark_sentences_as_used(st.session_state.cart)
                st.session_state.cart = []
                
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name="exported_sentences.csv",
                    mime="text/csv"
                )
                
                st.success(f"Checkout complete! {marked} sentences marked as used.")
    else:
        st.info("Your cart is empty.")

def show_import():
    st.title("📥 Import Data")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
    total, eng, fil = get_stats()
    st.markdown(f"**Current Database:** Total: {total} | English: {eng} | Filipino: {fil}")
    
    st.divider()
    
    # Import SQLite
    st.markdown("### 📂 Import from SQLite")
    uploaded_db = st.file_uploader("Upload .db file", type=["db"], key="import_db")
    
    if uploaded_db is not None:
        if st.button("📥 Import SQLite", type="primary"):
            with st.spinner("Importing..."):
                imported, skipped, error = import_from_sqlite_file(uploaded_db)
            
            if error:
                st.error(f"Error: {error}")
            else:
                st.success(f"✅ Imported: {imported} | Skipped: {skipped}")
                st.rerun()
    
    st.divider()
    
    # Import CSV
    st.markdown("### 📄 Import from CSV")
    uploaded_csv = st.file_uploader("Upload .csv file", type=["csv"], key="import_csv")
    
    if uploaded_csv is not None:
        if st.button("📥 Import CSV", type="primary"):
            csv_content = uploaded_csv.read().decode('utf-8')
            imported, skipped, error = import_from_csv_to_db(csv_content, skip_duplicates=True)
            
            if error:
                st.error(f"Error: {error}")
            else:
                st.success(f"✅ Imported: {imported} | Skipped: {skipped}")
                st.rerun()
    
    st.divider()
    
    # Export
    st.markdown("### 📤 Export Database")
    if st.button("📥 Export to CSV"):
        csv_data = export_to_csv_string()
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="database_export.csv",
            mime="text/csv"
        )

def show_manage():
    st.title("⚙️ Database Management")
    
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    
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
            st.metric("⚠️ Duplicates", info['duplicates'])
    
    st.divider()
    
    st.markdown("### 🔍 Find & Delete Duplicates")
    
    if st.button("🔍 Scan for Duplicates", type="primary"):
        st.session_state.duplicates_found = find_duplicate_sentences()
    
    if 'duplicates_found' in st.session_state:
        duplicates = st.session_state.duplicates_found
        
        if duplicates:
            st.warning(f"⚠️ Found **{len(duplicates)}** sentences with duplicates!")
            
            for i, dup in enumerate(duplicates):
                with st.expander(f"📝 {dup['sentence'][:50]}...", expanded=False):
                    st.markdown(f"**Sentence:** {dup['sentence']}")
                    st.markdown(f"**Language:** {'Filipino' if dup['language'] == 'fil' else 'English'}")
                    st.markdown(f"**Occurrences:** {dup['count']}")
                    
                    ids_to_delete = dup['ids'][1:]
                    if st.button(f"🗑️ Delete {len(ids_to_delete)} Duplicates", key=f"del_{i}"):
                        deleted = delete_duplicate_sentences(ids_to_delete, dup['language'])
                        st.success(f"✅ Deleted {deleted} duplicate(s)!")
                        if 'duplicates_found' in st.session_state:
                            del st.session_state.duplicates_found
                        st.rerun()
            
            if st.button("🗑️ Delete ALL Duplicates", type="primary"):
                total_deleted = 0
                for dup in duplicates:
                    ids_to_delete = dup['ids'][1:]
                    deleted = delete_duplicate_sentences(ids_to_delete, dup['language'])
                    total_deleted += deleted
                
                st.success(f"✅ Deleted **{total_deleted}** duplicate sentences!")
                if 'duplicates_found' in st.session_state:
                    del st.session_state.duplicates_found
                st.rerun()
        else:
            st.success("✅ No duplicates found!")

# ---------- MAIN APP ----------

def main():
    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Navigation")
        
        if st.session_state.db_mode is not None:
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
                st.session_state.db_mode = None
                st.session_state.cart = []
                st.session_state.page = "home"
                st.rerun()
        else:
            st.info("Please select a database option to get started.")
    
    # Main content
    if st.session_state.db_mode is None:
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

if __name__ == "__main__":
    main()
