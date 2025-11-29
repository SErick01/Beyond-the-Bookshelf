## Capstone Fall 2025
## BetterReads: A Better Recommendation System
## Collaborative Filtering Testing and Development

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from functools import lru_cache
# from sklearn.feature_extraction.text import TfidfVectorizer
# import numpy as np  
# import pickle

# https://pandas.pydata.org/docs/user_guide/merging.html -- for info on merging w/ pandas
# https://www.geeksforgeeks.org/machine-learning/build-a-recommendation-engine-with-collaborative-filtering/
# https://softwarepatternslexicon.com/machine-learning/model-training-patterns/collaborative-filtering/user-based-collaborating-filtering/


def getCSVdf  (filename, encoding_type = "utf-8"):
    "When given a filename, this method reads the csv file as a dataframe."
    book_dataframe = pd.read_csv(filename, encoding = encoding_type)
    return book_dataframe

# based on ratings!
@lru_cache(maxsize=1)
def getuser_item_matrix(fulldf):
    "When given the fully merged dataframe, it will return the user item matrix, the similarity matrix, and the user dataframe."
    user_item_matrix = fulldf.pivot_table(index="user_id",columns="work_id",values="rating_value").fillna(0) #user-item relationship 
    user_similarity = cosine_similarity(user_item_matrix)
    user_df = pd.DataFrame(user_similarity,index=user_item_matrix.index,columns=user_item_matrix.index)

    return user_item_matrix, user_similarity, user_df


def recommend_for_user(user_id, user_similarity_df, user_item_matrix, works, top_n=5):
    "This method when given the user's id, the user similarity dataframe, user item matrix, and the "
    if user_id not in user_similarity_df.index:
        return [] #no recommendations for new users; otherwise raise errors
    
    similar_users = user_similarity_df[user_id].sort_values(ascending=False).drop(user_id)
    user_rated = set(user_item_matrix.loc[user_id][user_item_matrix.loc[user_id] > 0].index)
    
    scores = {}
    for sim_user, sim_score in similar_users.items():
        for work_id, rating in user_item_matrix.loc[sim_user].items():
            if work_id not in user_rated and rating > 0:
                scores[work_id] = scores.get(work_id, 0) + sim_score * rating
    

    top_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    recommendations = []
    for wid, score in top_items:
        title = works.loc[works["work_id"] == wid, "title"].values[0]
        recommendations.append((wid, title, score))
    return recommendations


#example test
if __name__ == "__main__":
    works = getCSVdf("works.csv")
    users = getCSVdf("users.csv")
    ratings_5k = getCSVdf("ratings_5k.csv")

    ratings_5k = ratings_5k.drop(columns = ["rated_at"]) #time of rating does not matter
    works = works.drop(columns = ["publish_year"]) #publish year also does not matter in recc.

#merging the csvs togther into one df
    ratings_works = ratings_5k.merge(works, on = "work_id", how = "left")
    fulldf = ratings_works.merge(users, on = "user_id", how = "left")
    user_item_matrix, user_similarity, user_df = getuser_item_matrix(fulldf)

    user1 = fulldf["user_id"].iloc[0]  
    print(f"\nRecommendations for user {user1}:")
    print(recommend_for_user(user1, user_df, user_item_matrix, works, top_n=5))
