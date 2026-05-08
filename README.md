# Sentence Database Tool

A web-based tool for managing sentence databases with filtering, export, and import capabilities.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

## Features

- 📊 **Dashboard** - View statistics and usage distribution
- ➕ **Add Sentences** - Add new sentences with duplicate detection
- ✏️ **Edit Sentences** - Search and modify existing sentences
- 🛒 **Shop for Data** - Filter sentences, add to cart, export to CSV
- 📥 **Import CSV** - Bulk import sentences from CSV files
- ⚙️ **Database Management** - Find and delete duplicate sentences

## Live Demo

Visit the app: [Sentence Database Tool](https://share.streamlit.io/)

## Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/sentence-database-tool.git
   cd sentence-database-tool
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   streamlit run sentence_db_app.py
   ```

4. **Open in browser**
   ```
   http://localhost:8501
   ```

## Usage

### CSV Format for Import

The CSV file should have the following format:

```csv
sentence,category,language
Kumain ang bata ng mansanas.,Basic,fil
The cat is on the table.,Basic,en
```

- `sentence` - The sentence text (required)
- `category` - Category name (required)
- `language` - Language code: `fil` for Filipino, `en` for English (optional, defaults to `fil`)

### Database Structure

The app uses SQLite with two tables:
- `fil_sentences` - Filipino sentences
- `eng_sentences` - English sentences

Each table contains:
- `sen_id` - Unique identifier
- `sentence` - The sentence text
- `category` - Category name
- `language` - Language code
- `used` - Whether sentence has been used (0 or 1)
- `char_count` - Character count
- `word_count` - Word count
- `sentence_count` - Sentence count

## Deployment

### Deploy to Streamlit Cloud (Free)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select your repository
6. Click "Deploy"

## Screenshots

### Home Dashboard
View statistics and category breakdown.

### Shop for Data
Filter sentences by category and language, add to cart, and export.

### Database Management
Find and remove duplicate sentences.

## License

This project is open source and available under the [MIT License](LICENSE).

## Author

Created by Galaxy AI Team