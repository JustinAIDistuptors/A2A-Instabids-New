# Vision 2.0 Feature Documentation

This document outlines the new Vision 2.0 features implemented in the Instabids platform, including enhanced image analysis, data validation, and feedback systems.

## 1. Enhanced Vision Tool

The Vision 2.0 update introduces an enhanced vision analysis tool that leverages OpenAI's GPT-4o Vision API to provide more accurate and detailed analysis of construction and home repair images.

### Features

- **Advanced Image Analysis**: Extracts structured data including labels, descriptions, and damage assessments
- **Batch Processing**: Analyze multiple images in a single operation
- **Validation**: Verify images are suitable for bid cards
- **Dimension Detection**: Automatically detect and record image dimensions

### Usage

```python
from instabids.tools.vision_tool_plus import analyse, batch_analyse, validate_image_for_bid_card

# Analyze a single image
result = await analyse("path/to/image.jpg")
print(result["labels"])  # ['roof', 'damage', 'shingles']

# Batch analyze multiple images
results = await batch_analyse(["image1.jpg", "image2.jpg"])

# Validate an image for a bid card
validation = await validate_image_for_bid_card("image.jpg")
if validation["is_valid"]:
    print("Image is suitable for bid card")
```

## 2. Pydantic Model Validation

We've implemented Pydantic models for data validation throughout the application, ensuring data consistency and integrity.

### BidCard Model

The `BidCard` model defines the structure and validation rules for bid card data:

```python
class BidCard(BaseModel):
    id: str
    user_id: str
    category: str
    job_type: str
    budget_range: tuple[int, int] = Field(..., example=[0, 10000])
    timeline: str
    location: str
    group_bidding: bool
    images: list[dict]
    description: str = ""
```

### Contract Validation

We've added a contract validation step to the CI pipeline that ensures all example bid card data conforms to the Pydantic model schema.

### Validation Script

A new validation script is available to validate bid card data:

```bash
# Validate a single file
python scripts/validate_bid_card.py examples/bid_card.json

# Validate all JSON files in a directory
python scripts/validate_bid_card.py --dir examples/

# Show detailed validation errors
python scripts/validate_bid_card.py --verbose examples/bid_card.json

# Attempt to fix common issues
python scripts/validate_bid_card.py --fix examples/bid_card.json
```

## 3. User Feedback System

The platform now includes a comprehensive user feedback system to collect and analyze user experiences.

### API Endpoints

- `POST /api/feedback`: Submit user feedback with rating and comments
- `GET /api/feedback/{user_id}`: Retrieve feedback for a specific user

### React Feedback Modal

A new `FeedbackModal` component has been added to collect user feedback:

```jsx
import FeedbackModal from '../components/FeedbackModal';

// In your component
const [showFeedback, setShowFeedback] = useState(false);

return (
  <>
    <button onClick={() => setShowFeedback(true)}>Give Feedback</button>
    
    {showFeedback && (
      <FeedbackModal 
        onClose={() => setShowFeedback(false)}
        userId={currentUser.id}
      />
    )}
  </>
);
```

## 4. WebSocket Integration

The WebSocket chat route has been updated to use the BidCard Pydantic model for data validation and serialization.

### Features

- Real-time validation of bid card data
- Structured response format
- Improved error handling

## 5. Testing

Comprehensive tests have been added for all new features:

- Unit tests for the feedback API
- Tests for the preference repository
- Tests for the enhanced vision tool
- Tests for the FeedbackModal component

## Environment Variables

The following environment variables are required:

```
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

## CI/CD Integration

The CI pipeline has been updated to include:

- Contract validation using Pydantic
- Tests for the new features
- Environment variable configuration

## Next Steps

1. Deploy the Vision 2.0 features to production
2. Monitor feedback system for user insights
3. Expand the vision analysis capabilities with additional models
4. Enhance the bid card validation with more sophisticated rules