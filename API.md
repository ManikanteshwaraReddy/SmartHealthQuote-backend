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

### Generate Insurance Quote

**POST** `/api/quote`

Generate a personalized health insurance quote based on user profile and similar cases.

**Request Body:**
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
{
  "planName": "Comprehensive Family Health Plan",
  "premiumINR": 18500.0,
  "sumInsured": 1000000,
  "policyTermYears": 20,
  "paymentMode": "Yearly",
  "deductibleINR": 5000.0,
  "coinsurancePercent": 10.0,
  "coverageDetails": [
    "Hospitalization coverage up to sum insured",
    "Pre and post hospitalization expenses",
    "Day care procedures",
    "Ambulance charges",
    "Maternity benefits",
    "Preventive health check-ups"
  ],
  "rationale": "Based on your age (30), family size (2 members), and desired coverage (₹10L), this plan offers comprehensive coverage suitable for a young family. The premium is competitive considering no pre-existing conditions and healthy lifestyle.",
  "basedOnExamples": [
    {
      "id": 1,
      "score": 0.87,
      "snippet": "Age: 28; Gender: Female; Location: Delhi; Family size: 2; Plan type: Family; Sum insured: ₹1000000; Premium: ₹18500",
      "premium_inr": 18500.0
    },
    {
      "id": 3,
      "score": 0.82,
      "snippet": "Age: 32; Gender: Male; Location: Mumbai; Family size: 2; Plan type: Family; Sum insured: ₹800000; Premium: ₹16800",
      "premium_inr": 16800.0
    }
  ]
}
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
- `500 Internal Server Error`: Server-side issues (Ollama not available, index not found, etc.)

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