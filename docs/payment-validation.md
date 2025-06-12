# Payment Validation Documentation

## Overview

This document describes the validation rules added to the `SimplePaymentRequest` model to prevent Chapa API validation errors.

## Validation Rules

### 1. Amount Validation

**Rule**: Amount must be greater than 0

**Error Message**: "Amount must be greater than 0"

**Examples**:
- ✅ Valid: `100.0`, `50.5`, `1.0`
- ❌ Invalid: `0`, `-10.5`, `0.0`

### 2. Phone Number Validation

**Rule**: Phone number must be 10-15 digits with optional + prefix

**Pattern**: `^\+?[0-9]{10,15}$`

**Error Message**: "Invalid phone number format. We only accept numbers and a + as prefix. The length should be between 10 and 15 characters."

**Examples**:
- ✅ Valid: `0911234567`, `+251911234567`, `1234567890123`
- ❌ Invalid: `123456789` (too short), `1234567890123456` (too long), `091123456a` (contains letters)

### 3. Callback URL Validation

**Rule**: Must be a valid HTTP/HTTPS URL if provided (optional field)

**Pattern**: `^https?://.+`

**Error Message**: "The callback url must be a valid URL."

**Examples**:
- ✅ Valid: `https://example.com/callback`, `http://localhost:3000/callback`, `null` (optional)
- ❌ Invalid: `not-a-valid-url`, `ftp://example.com`

## Implementation Details

### Pydantic Validators

The validation is implemented using Pydantic V2 `@field_validator` decorators:

```python
@field_validator('amount')
@classmethod
def validate_amount(cls, v):
    if v <= 0:
        raise ValueError('Amount must be greater than 0')
    return v

@field_validator('phone_number')
@classmethod
def validate_phone_number(cls, v):
    if not re.match(r'^\+?[0-9]{10,15}$', v):
        raise ValueError('Invalid phone number format. We only accept numbers and a + as prefix. The length should be between 10 and 15 characters.')
    return v

@field_validator('callback_url')
@classmethod
def validate_callback_url(cls, v):
    if v is not None and v.strip():
        if not re.match(r'^https?://.+', v):
            raise ValueError('The callback url must be a valid URL.')
    return v
```

### Error Handling

The endpoint now handles validation errors specifically:

```python
except ValueError as e:
    # Handle validation errors specifically
    logger.error(f"Validation error in simple payment: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(e)
    )
```

## API Response Examples

### Successful Request

```json
{
  "amount": 100.0,
  "phone_number": "0911234567",
  "booking_id": "booking-123",
  "callback_url": "https://example.com/callback"
}
```

Response:
```json
{
  "checkoutUrl": "https://checkout.chapa.co/checkout/payment/...",
  "amount": 100.0
}
```

### Validation Error Examples

#### Invalid Amount

Request:
```json
{
  "amount": 0,
  "phone_number": "0911234567",
  "booking_id": "booking-123"
}
```

Response (400 Bad Request):
```json
{
  "detail": "Amount must be greater than 0"
}
```

#### Invalid Phone Number

Request:
```json
{
  "amount": 100.0,
  "phone_number": "123",
  "booking_id": "booking-123"
}
```

Response (400 Bad Request):
```json
{
  "detail": "Invalid phone number format. We only accept numbers and a + as prefix. The length should be between 10 and 15 characters."
}
```

#### Invalid Callback URL

Request:
```json
{
  "amount": 100.0,
  "phone_number": "0911234567",
  "booking_id": "booking-123",
  "callback_url": "not-a-valid-url"
}
```

Response (400 Bad Request):
```json
{
  "detail": "The callback url must be a valid URL."
}
```

## Benefits

1. **Early Validation**: Errors are caught before making API calls to Chapa
2. **Clear Error Messages**: Users get specific feedback about what's wrong
3. **Reduced API Calls**: Invalid requests don't reach Chapa, saving on API usage
4. **Better User Experience**: Immediate feedback instead of waiting for external API response
5. **Consistent Error Format**: All validation errors follow the same HTTP 400 pattern

## Testing

The validation can be tested by sending requests to the `/api/payments/initiate-simple` endpoint with various invalid data combinations to ensure proper error handling.
