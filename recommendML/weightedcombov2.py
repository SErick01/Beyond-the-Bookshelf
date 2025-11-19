

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity 
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np  
import pickle
import tensorflow as tf
from BERT_TFIDF_Content import *
from collaborative_testing import *

def combinedRS(user_id, user_similarity_df, user_item_matrix, works,
               title=None, description=None, genres=None, author=None,
                weight_cf=0.4, weight_cb=0.6, top_n=10):
    
    collaborative = list()
    content_based = list()
    collaborative_recommendations = recommend_for_user(user_id, user_similarity_df, user_item_matrix, works, top_n * 2)
    for recommendation in collaborative_recommendations:
       collaborative.append(recommendation[1]) 

    #content recommendations returns df splices
    content_recommendations = recommend_content(title=title, description=description, genres=genres, author=author, top_n=top_n*2)
    for index, row in content_recommendations.iterrows():
        title = row["title"]
        content_based.append(title) 

    #both lists return only the titles of the books

    if (weight_cf + weight_cb != 1):
        num_cf = int(top_n * weight_cf)
        num_cb = top_n - num_cf
    else:
        num_cf = int(top_n * weight_cf)
        num_cb = int(top_n * weight_cb)

    recommendations = collaborative[:num_cf] + content_based[:num_cb]

    #want to make sure there are no duplicates in the list
    visited = set()
    unique_recommend = []
    for title in recommendations:
        if title not in visited:
            unique_recommend.append(title)
            visited.add(title)
    
    return unique_recommend[:top_n]
    

if __name__ == "__main__":

##example 
    works = getCSVdf("works.csv")
    users = getCSVdf("users.csv")
    ratings_5k = getCSVdf("ratings_5k.csv")

    ratings_5k = ratings_5k.drop(columns = ["rated_at"]) #time of rating does not matter
    works = works.drop(columns = ["publish_year"]) #publish year also does not matter in recc.

    ratings_works = ratings_5k.merge(works, on = "work_id", how = "left")
    fulldf = ratings_works.merge(users, on = "user_id", how = "left")
    user_item_matrix, user_similarity, user_df = getuser_item_matrix(fulldf)

    user1 = fulldf["user_id"].iloc[0]  
    print(f"\nRecommendations for user {user1}:")
    print(combinedRS(user1, user_df, user_item_matrix, works, genres = "Romance" ))
