import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";

const App = () => {
  const [selectedCollection, setSelectedCollection] = useState("");
  const [year, setYear] = useState("");
  const [startYear, setStartYear] = useState("");
  const [endYear, setEndYear] = useState("");
  const [queryString, setQueryString] = useState("");
  const [articles, setArticles] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false); // For loading state

  const collections = ["csAI", "csCV", "csLG", "csCL", "statML"];

  const handleSearch = async () => {
    if (!selectedCollection) {
      setError("Veuillez sélectionner une collection.");
      setArticles([]);
      return;
    }

    setLoading(true); // Start loading
    try {
      const params = {};
      if (year) params.year = year;
      if (startYear) params.start_year = startYear;
      if (endYear) params.end_year = endYear;

      const response = await axios.get(
        `http://localhost:8000/collections/${selectedCollection}/articles`,
        { params }
      );
      
      // Check if articles exist
      if (response.data.length === 0) {
        setError("Aucun article trouvé.");
        setArticles([]);
      } else {
        setArticles(response.data);
        setError("");
      }
    } catch (error) {
      if (error.response && error.response.status === 404) {
        setError("Aucun article trouvé.");
        setArticles([]);
      } else if (error.response && error.response.status === 400) {
        setError("Format de la requête invalide.");
        setArticles([]);
      } else {
        setError("Erreur lors de la récupération des articles.");
        console.error(error);
        setArticles([]);
      }
    } finally {
      setLoading(false); // End loading
    }
  };

  const handleSimilaritySearch = async () => {
    if (!selectedCollection) {
      setError("Veuillez sélectionner une collection.");
      setArticles([]);
      return;
    }

    if (!queryString) {
      setError("Veuillez entrer un terme de recherche.");
      setArticles([]);
      return;
    }

    setLoading(true); // Start loading
    try {
      const response = await axios.get(
        `http://localhost:8000/collections/${selectedCollection}/search`,
        {
          params: { query_string: queryString },
        }
      );
      
      // Check if similar articles exist
      if (response.data.length === 0) {
        setError("Aucun article similaire trouvé.");
        setArticles([]);
      } else {
        setArticles(response.data);
        setError("");
      }
    } catch (error) {
      if (error.response && error.response.status === 404) {
        setError("Aucun article similaire trouvé.");
        setArticles([]);
      } else if (error.response && error.response.status === 400) {
        setError("Format de la requête invalide.");
        setArticles([]);
      } else {
        setError("Erreur lors de la recherche par similarité.");
        console.error(error);
        setArticles([]);
      }
    } finally {
      setLoading(false); // End loading
    }
  };

  const handleCollectionChange = async (event) => {
    const collection = event.target.value;
    setSelectedCollection(collection);

    // Reset articles and error if the collection is changed
    setArticles([]);
    setError("");

    // Only load the data if no search parameter is provided
    if (!year && !startYear && !endYear) {
      try {
        const response = await axios.get(
          `http://localhost:8000/collections/${collection}/articles`
        );
        
        // If articles are found
        if (response.data.length === 0) {
          setError("Aucun article trouvé.");
        } else {
          setArticles(response.data);
        }
      } catch (error) {
        if (error.response && error.response.status === 404) {
          setError("Aucun article trouvé.");
        } else {
          setError("Erreur lors de la récupération des articles.");
          console.error(error);
        }
      }
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 className="app-title">TopSearch</h1>
        <p className="app-subtitle">Find your articles here</p>
      </header>
      <main className="app-main">
        <div className="topsearch-container">
          <h1 className="topsearch-title">TopSearch Articles</h1>
          <div className="form-section">
            <label className="form-label">Sélectionner une collection :</label>
            <div className="radio-group">
              {collections.map((collection) => (
                <div key={collection} className="radio-item">
                  <input
                    type="radio"
                    id={collection}
                    name="collection"
                    value={collection}
                    checked={selectedCollection === collection}
                    onChange={handleCollectionChange}
                    className="radio-input"
                  />
                  <label htmlFor={collection} className="radio-label">
                    {collection}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="form-section">
            <label className="form-label">Année de publication :</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="form-input"
            />
          </div>
          <div className="form-section">
            <label className="form-label">Année de début :</label>
            <input
              type="number"
              value={startYear}
              onChange={(e) => setStartYear(e.target.value)}
              className="form-input"
            />
          </div>
          <div className="form-section">
            <label className="form-label">Année de fin :</label>
            <input
              type="number"
              value={endYear}
              onChange={(e) => setEndYear(e.target.value)}
              className="form-input"
            />
          </div>
          <button onClick={handleSearch} className="search-button" disabled={loading}>
            {loading ? "Chargement..." : "Rechercher par critères"}
          </button>

          <div className="form-section">
            <label className="form-label">Recherche par similarité :</label>
            <input
              type="text"
              value={queryString}
              onChange={(e) => setQueryString(e.target.value)}
              className="form-input"
            />
            <button onClick={handleSimilaritySearch} className="search-button" disabled={loading}>
              {loading ? "Chargement..." : "Rechercher par similarité"}
            </button>
          </div>

          {error && <p className="error-message">{error}</p>}
          {loading && <p>Loading...</p>}
          
          <ul className="articles-list">
            {articles.map((article) => (
              <li key={article._id} className="article-item">
                <h2 className="article-title">{article.title}</h2>
                <p className="article-summary">{article.summary}</p>
              </li>
            ))}
          </ul>
        </div>
      </main>
      <footer className="app-footer">
        <p>© {new Date().getFullYear()} TopSearch. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default App;
