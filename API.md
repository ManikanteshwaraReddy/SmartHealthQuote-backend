# API Documentation

## Base URL
- Development: `http://localhost:8000`
- Production: Your deployed server URL

## Endpoints

### Health Check

**GET** `/health`

Check if the API server is running.

**Response:**
```json
{
  "status": "ok"
}
```

### RAG Index Status

**GET** `/rag/status`

Report whether the FAISS index is loaded and return basic statistics.

Possible responses:

Loaded:
```json
{
  "status": "loaded",
  "total_vectors": 123,
  "dimension": 384,
  "metadata_count": 123
}
```

Not ready:
```json
{
  "status": "not_ready",
  "message": "RAG index not loaded. Ensure FAISS is installed and the index files exist (see INDEX_DIR)."
}
```

### Calculate Total Payable Amount

**POST** `/api/quote`

Return only the total payable annual premium in INR, computed via a cost-matrix baseline and optionally refined by an LLM.

**Request Body (examples, fields optional):**
```json
{
  "age": 30,
  "gender": "Male",
  "location": "Mumbai",
  "occupation": "Software Engineer",
  "numberOfInsuredMembers": 2,
  "familyDetails": "Married with spouse",
  "preExistingConditions": "None",
  "pastMedicalHistory": "None",
  "familyMedicalHistory": "Diabetes in family",
  "heightCm": 175.5,
  "weightKg": 70.0,
  "bmi": 22.8,
  "pregnancyStatus": "No",
  "smokingTobaccoUse": "No",
  "alcoholConsumption": "Occasional",
  "exerciseFrequency": "Regular",
  "planType": "Family",
  "sumInsured": 1000000,
  "policyTermYears": 20,
  "premiumPaymentMode": "Yearly"
}
```

**All fields are optional.** The API will work with partial information.

**Response:**
```json
{ "totalPayableINR": 18500.0 }
```

## Error Responses

All errors return appropriate HTTP status codes with JSON error details:

```json
{
  "error": "Error type",
  "details": "Detailed error message"
}
```

Common errors:
- `400 Bad Request`: Invalid request data
- `500 Internal Server Error`: Server-side issues (e.g., Ollama connection when USE_LLM_FOR_AMOUNT=true)

## Field Mappings

The API accepts both camelCase and snake_case field names:

| Frontend (camelCase) | Backend (snake_case) | Description |
|---------------------|---------------------|-------------|
| `numberOfInsuredMembers` | `number_of_insured_members` | Family size |
| `familyDetails` | `family_details` | Family composition |
| `preExistingConditions` | `pre_existing_conditions` | Current health conditions |
| `pastMedicalHistory` | `past_medical_history` | Previous medical events |
| `familyMedicalHistory` | `family_medical_history` | Hereditary conditions |
| `heightCm` | `height_cm` | Height in centimeters |
| `weightKg` | `weight_kg` | Weight in kilograms |
| `pregnancyStatus` | `pregnancy_status` | Pregnancy status |
| `smokingTobaccoUse` | `smoking_tobacco_use` | Smoking/tobacco habits |
| `alcoholConsumption` | `alcohol_consumption` | Alcohol consumption |
| `exerciseFrequency` | `exercise_frequency` | Exercise habits |
| `planType` | `plan_type` | Individual/Family plan |
| `sumInsured` | `sum_insured` | Desired coverage amount |
| `policyTermYears` | `policy_term_years` | Policy duration |
| `premiumPaymentMode` | `premium_payment_mode` | Payment frequency |

## Example cURL Commands

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Quote (Minimal)
```bash
curl -X POST http://localhost:8000/api/quote \
  -H "Content-Type: application/json" \
  -d '{"age": 30, "gender": "Male"}'
```

### Get Quote (Detailed)
```bash
curl -X POST http://localhost:8000/api/quote \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "gender": "Male",
    "location": "Mumbai",
    "occupation": "Software Engineer",
    "numberOfInsuredMembers": 2,
    "sumInsured": 1000000,
    "planType": "Family"
  }'
```