## Capstone Fall 2025
## BetterReads: A Better Recommendation System
# Content-Based Modeling using both TF-IDF and Text Embeddings via Bert

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity 
from sklearn.feature_extraction.text import TfidfVectorizer
# import tensorflow as tf
# import tensorflow_hub as hub
from transformers import BertTokenizer, TFBertModel #pip install transformers==4.41.2
import numpy as np  
import pickle
from pathlib import Path
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent


## https://www.youtube.com/watch?v=e-I_G9QhHTA&list=PL2iCg75NbOIphVypF1BTGNQrwujM0X2L4

@lru_cache(maxsize=None)
def getCSVdf  (filename, encoding_type = "utf-8"):
    "When given a filename, this method reads the csv file as a dataframe."
    csv_path = BASE_DIR / filename
    book_dataframe = pd.read_csv(csv_path, encoding = encoding_type)
    return book_dataframe


@lru_cache(maxsize=1)
def get_bert_model():
    """Load BERT tokenizer + model once and cache them."""
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = TFBertModel.from_pretrained("bert-base-uncased", from_pt=True)
    return tokenizer, model


def get_BERT_embeds (text, batch_size = 1000):
    "When given text, this method uses the uncased BERT model to create an array of the created embeddings."

    #BERT Tokenizer & Model via HuggingFace and Tensorflow
    #was originally tensorflow model -- but had to downgrade python to use it
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    # model = TFBertModel.from_pretrained("bert-base-uncased", from_pt=True)
    
    #need batch size otherwise it will overload CPU --do it in parts
    bert = []
    ##ran into error; where the value was not a str, but was expecting one
    cleaned_texts = []
    for t in text:
        if pd.notna(t): #if its not na or null
            if isinstance(t, str): #if t is a str
                cleaned_texts.append(t)
            else:
                cleaned_texts.append(str(t))
        else:
            cleaned_texts.append("")
    
    for i in range(0, len(text), batch_size):
        batch = cleaned_texts[i:i+ batch_size] #start from i then cont until batch size
        encodings = tokenizer(batch, padding=True, truncation=True,return_tensors="tf", max_length=512)
        outputs = model(encodings)
        embedding_batch = outputs.pooler_output #no longer need iterate w/ huggingface outputs
        bert.append(embedding_batch.numpy())
    return np.vpstack(bert)

#TF-IDF Vectorization
def get_TFIDF_Vector(text, maxfeat = 2000):
    "This method returns the TF-IDF Matrix of any given text"
    bookdefVector = TfidfVectorizer(stop_words = "english", max_features = maxfeat) 
    vectorMatrix = bookdefVector.fit_transform(text)
    return bookdefVector, vectorMatrix

def getDF_matricies(filename = "book_details.csv"):
    "This method gets the matricies, embeddings, and related vectors of the original dataset and saves them within pickle files."
    df = getCSVdf(filename, "latin1")

    #for warning for trying to set on a copy
    BookDetails_df = df[['title', 'author', 'genres','description']].copy() 

    #removed 'avg ratings' as that is not necessarily an atttirbute of the item -- but rather a quality more for collaborative filtering

    BookDetails_df['title'] = BookDetails_df['title'].fillna('') #BERT
    BookDetails_df['description'] = BookDetails_df['description'].fillna('')

    BookDetails_df['genres'] = BookDetails_df['genres'].fillna('') #TF-IDF
    BookDetails_df['author'] = BookDetails_df['author'].fillna('')

    #only the title and the description will be embedded 
    bert_inputs = (df['title'] + ' ' + df['description']).tolist() #list of the titles and descriptions of books
    embeddings = get_BERT_embeds(bert_inputs, 512)
    tfidf_texts  = (BookDetails_df['genres'] + ' ' + BookDetails_df['author']).tolist()
    vectorizer, vector_Matrix= get_TFIDF_Vector(tfidf_texts)

    with open("book_embeddings.pkl", "wb") as f:
        pickle.dump(embeddings, f)
    with open("tfidf_matrix.pkl", "wb") as f:
        pickle.dump(vector_Matrix, f)
    with open("tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open("book_details.pkl", "wb") as f:
        pickle.dump(BookDetails_df, f)

@lru_cache(maxsize=1)
def load_matricies():
    "This method loads the associated matrices and dataframes associated with the original dataset."
    with open(BASE_DIR / "book_embeddings.pkl", "rb") as f:
        embeddings = pickle.load(f)
    with open(BASE_DIR / "tfidf_matrix.pkl", "rb") as f:
        vector_Matrix = pickle.load(f)
    with open(BASE_DIR / "tfidf_vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(BASE_DIR / "book_details.pkl", "rb") as f:
        BookDetails_df = pickle.load(f)
    return embeddings, vector_Matrix, vectorizer, BookDetails_df

def recommend_content(title=None, description=None, genres=None, author=None, top_n=5):
    "This method returns suggested books based off of a given title, description, genre, or author."
    embeddings, vector_Matrix, vectorizer, BookDetails_df = load_matricies()
    
    if title or description: #Bert Fields
        bert_input = [f"{title or ''} {description or ''}"]
        new_bert_embed = get_BERT_embeds(bert_input, batch_size=1)
        bert_sim = cosine_similarity(new_bert_embed, (embeddings))[0]
    else:
        bert_sim = np.zeros(len(BookDetails_df))
    
    
    if genres or author: #Genres & Author Fields (TF-IDF Section)
        tfidf_input = [f"{genres or ''} {author or ''}"]
        new_tfidf_vector = vectorizer.transform(tfidf_input) #was expecting array not tuple
        tfidf_sim = cosine_similarity(new_tfidf_vector, vector_Matrix)[0]
    else:
        tfidf_sim = np.zeros(len(BookDetails_df))

    num_sources = int(bool(title or description)) + int(bool(genres or author))
    if num_sources > 0:
        combined_sim = (bert_sim + tfidf_sim) / num_sources
    else:
        combined_sim = np.zeros(len(BookDetails_df)) #makes sure there is no division of zero
    
    top_indices = combined_sim.argsort()[::-1][:top_n]
    return BookDetails_df.iloc[top_indices][['title', 'author', 'genres', 'description']]

if __name__ == "__main__":
    ## getDF_matricies() only needs to be run the first time!
    ### getDF_matricies(filename = "book_details.csv")
    print(recommend_content(title="Lost in the Stars", description="A poetic journey through space and time."))
