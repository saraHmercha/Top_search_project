from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import motor.motor_asyncio
from bson import ObjectId
import os
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KNeighborsRegressor
import numpy as np
import asyncio
from pymongo.errors import PyMongoError


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "TopSearch")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Article(BaseModel):
    _id: str
    title: str
    summary: str
    published: str
    pdf_link: str

    class Config:
      arbitrary_types_allowed = True
      json_encoders = {
         ObjectId: str
      }

# Global database connection
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

# Global dictionary to store the model and vectors for each collection
collection_indices = {}

async def get_database(collection_name: str):
    """Returns the database collection object."""
    try:
        await db.command("ping")
        print(f"Successfully connected to MongoDB collection: {collection_name}")
        collection = db[collection_name]
        return collection
    except PyMongoError as e:
        print(f"Error connecting to MongoDB: {e}")
        raise HTTPException(status_code=500, detail="Error connecting to the database")

async def initialize_knn_index(collection_name: str):
    """Initializes the KNN index for the given collection."""
    collection = await get_database(collection_name)
    articles = await collection.find().to_list(length=None)
    
    if not articles:
        print(f"No articles found in collection {collection_name}")
        return None

    # Prepare the documents for vectorization
    documents = [f"{article.get('title', '')} {article.get('summary', '')}" for article in articles]
    documents = [doc for doc in documents if doc.strip()]  # Remove empty documents
    
    if not documents:  # If no documents are left after cleaning, return None
        print(f"No valid documents in collection {collection_name} after processing.")
        return None

    # Initialize and fit TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(min_df=2)
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    # Initialize and fit KNN model
    knn_model = KNeighborsRegressor(n_neighbors=5, metric='cosine')
    knn_model.fit(tfidf_matrix, np.arange(len(documents)))  # Match matrix rows to indices

    # Store the index components
    collection_indices[collection_name] = {
        'vectorizer': vectorizer,
        'knn_model': knn_model,
        'articles': articles,
        'documents': documents
    }
    
    print(f"KNN index initialized for collection: {collection_name}")
    return True


@app.get("/collections/{collection_name}/articles", response_model=List[Article])
async def get_articles(
    collection_name: str,
    year: Optional[int] = Query(None, description="Year of publication (YYYY)"),
    start_year: Optional[int] = Query(None, description="Start year for the search (YYYY)"),
    end_year: Optional[int] = Query(None, description="End year for the search (YYYY)"),
):
    # Vérifiez que le nom de la collection existe bien dans la base de données
    if collection_name not in await db.list_collection_names():
        raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")
    
    collection = await get_database(collection_name)
    query = {}

    try:
        if year:
            start_date = datetime(year, 1, 1).isoformat()
            end_date = datetime(year, 12, 31, 23, 59, 59).isoformat()
            query["published"] = {"$gte": start_date, "$lte": end_date}
        elif start_year:
            start_date = datetime(start_year, 1, 1).isoformat()
            query["published"] = {"$gte": start_date}
            if end_year:
                end_date = datetime(end_year, 12, 31, 23, 59, 59).isoformat()
                query["published"]["$lte"] = end_date
        elif end_year:
            end_date = datetime(end_year, 12, 31, 23, 59, 59).isoformat()
            query["published"] = {"$lte": end_date}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid year format")

    try:
        articles = await collection.find(query).to_list(length=None)
        for article in articles:
            article["_id"] = str(article["_id"])

        if articles:
            return articles
        else:
            raise HTTPException(status_code=404, detail="No articles found")
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{collection_name}/search", response_model=List[Article])
async def search_articles(
    collection_name: str,
    query_string: Optional[str] = Query(None, description="Search query term"),
):
    if not query_string:
        raise HTTPException(status_code=400, detail="Search query must be provided")

    # Vérifiez que le nom de la collection existe bien dans la base de données
    if collection_name not in await db.list_collection_names():
        raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")

    # Check if the index is already initialized; if not, initialize it.
    if collection_name not in collection_indices:
        if not await initialize_knn_index(collection_name):
            raise HTTPException(status_code=500, detail="KNN index not available")
    
    index_data = collection_indices.get(collection_name)

    if not index_data:
        raise HTTPException(status_code=500, detail="KNN index not available")

    vectorizer = index_data['vectorizer']
    knn_model = index_data['knn_model']
    articles = index_data['articles']
    
    # Convert the query string to a vector
    query_vector = vectorizer.transform([query_string])

    # Get the k-nearest neighbors
    distances, indices = knn_model.kneighbors(query_vector)
    
    # Retrieve the corresponding articles
    similar_articles = [articles[idx] for idx in indices.flatten()]
    for article in similar_articles:
        article["_id"] = str(article["_id"])

    return similar_articles


# Initialize KNN for all collections upon application startup
@app.on_event("startup")
async def startup_event():
    collection_names = await db.list_collection_names()

    # Initialize KNN index for each collection in parallel
    await asyncio.gather(*[initialize_knn_index(collection_name) for collection_name in collection_names])
    print("All KNN indices initialized")


#uvicorn main:app --reload 