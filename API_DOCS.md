# 📚 Kelola Limbah & Cobalt Protocol AI Service API Documentation

Welcome to the official API Documentation for **Cobalt Protocol AI Service** (Kelola Limbah API). This service provides endpoints powered by Large Language Models (LLMs), RAG (Retrieval-Augmented Generation), and Chutes AI integrations for smart contract data processing, competition document querying, and team recommendations.

---

## 🛠️ Base Configuration & Authentication

- **Base URL**: `http://localhost:8002` (or configured via `HOST` and `PORT`)
- **Authentication**: All protected endpoints require a valid Authorization token passed via HTTP headers (verified against `BASE_URL_AUTH`).

---

## 📌 Endpoints Overview

### 1. Root & Health Check
- **URL**: `GET /`
- **Description**: Verifies service status, environment details, and running status.
- **Response Example**:
```json
{
  "message": "Welcome to the API!",
  "environment": "dev",
  "is_dev": true,
  "is_staging": false,
  "is_production": false
}
```

---

### 2. Item Lookup
- **URL**: `GET /items/{item_id}`
- **Parameters**: 
  - `item_id` (path, integer): The item identifier.
  - `q` (query, string, optional): Optional search query parameter.
- **Response Example**:
```json
{
  "item_id": 1,
  "q": "test"
}
```

---

### 3. AI Chat & RAG (Competition QA)
- **URL**: `POST /api/v1/chat/{competition_id}`
- **Description**: Sends a query/question regarding a specific competition and retrieves an AI-generated answer using RAG over the competition guidebook and embedded chunks.
- **Headers**:
  - `Authorization: Bearer <token>`
- **Request Body**:
```json
{
  "question": "untuk detail timeline lombanya ada apa saja?"
}
```
- **Response Example**:
```json
{
  "data": {
    "answer": "Detail timeline perlombaan mencakup pendaftaran dari tanggal 1 sampai 10..."
  },
  "message": "answer is found",
  "errors": null
}
```

---

### 4. Team Recommendations
- **Get Recommended Teams for User**:
  - **URL**: `GET /api/v1/recommendation-team/{competition_id}`
  - **Description**: Analyzes the current authenticated user's skills and background, performs vector similarity search, and returns a list of recommended teams matching the user profile.
  - **Headers**:
    - `Authorization: Bearer <token>`
  - **Response Example**:
```json
{
  "data": [
    {
      "team_id": "01M5Y32MGGJYQ56XP29D7QRW7N",
      "team_name": "EcoWarriors",
      "visibility": true,
      "team_requirement": "Familiar with Solidity and Python",
      "competition_id": "01M6BD2Z14HMHKJKH3W9CY1517",
      "competition_name": "Hackathon Hijau",
      "description": "Lomba inovasi pengolahan limbah berbasis blockchain.",
      "skills_team": [
        {
          "id": "...",
          "name": "Solidity",
          "team_id": "01M5Y32MGGJYQ56XP29D7QRW7N",
          "created_at": "...",
          "updated_at": "...",
          "deleted_at": null
        }
      ]
    }
  ],
  "message": "success get recommendation team",
  "errors": null
}
```

- **Get Recommended Team by Specific Team ID**:
  - **URL**: `GET /api/v1/recommendation-team/{competition_id}/{team_id}`
  - **Description**: Fetches details for a specific team recommendation after validation.
  - **Headers**:
    - `Authorization: Bearer <token>`
  - **Response Example**:
```json
{
  "data": {
    "team_id": "01M5Y32MGGJYQ56XP29D7QRW7N",
    "team_name": "EcoWarriors",
    "visibility": true,
    "team_requirement": "Familiar with Solidity and Python",
    "competition_id": "01M6BD2Z14HMHKJKH3W9CY1517",
    "competition_name": "Hackathon Hijau",
    "description": "Lomba inovasi pengolahan limbah berbasis blockchain.",
    "skills_team": []
  },
  "message": "success get recomendation team",
  "errors": null
}
```
