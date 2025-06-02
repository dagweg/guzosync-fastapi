# UUID-MongoDB Integration Guide

This guide explains the UUID and ObjectID mismatch issues and provides solutions for your FastAPI-MongoDB application.

## Problem Summary

Your application uses UUIDs as primary keys in Pydantic models, but MongoDB naturally uses ObjectIDs. This creates several issues:

1. **Inconsistent Storage**: Some documents store UUIDs as strings, others as UUID objects
2. **Query Failures**: Queries fail when looking for UUIDs stored in different formats
3. **Authentication Issues**: User lookup fails due to ID format mismatches
4. **Data Integrity**: Mixed ID formats make data relationships unreliable

## Solutions Implemented

### 1. Enhanced Dependencies (`core/dependencies.py`)

The user authentication now tries multiple query formats:
```python
# Tries these queries in order:
1. {"id": user_id}           # UUID as string in id field
2. {"_id": user_id}          # UUID as string in _id field  
3. {"_id": ObjectId(user_id)} # ObjectId format (backwards compatibility)
```

### 2. Improved MongoDB Utils (`core/mongo_utils.py`)

Enhanced `transform_mongo_doc()` to handle UUID conversion:
- Converts MongoDB `_id` to Pydantic `id` field
- Handles ObjectId → UUID conversion
- Converts string UUIDs back to UUID objects
- Processes UUID fields in lists and nested objects

Enhanced `model_to_mongo_doc()` to standardize storage:
- Converts all UUID objects to strings for MongoDB
- Handles nested UUID fields in lists and objects

### 3. UUID-MongoDB Helper (`core/uuid_mongodb_helper.py`)

Created utilities for consistent UUID operations:
- `find_one_by_uuid()`: Tries multiple query formats
- `update_one_by_uuid()`: Updates with UUID format handling
- `delete_one_by_uuid()`: Deletes with UUID format handling
- `standardize_uuid_fields()`: Converts UUIDs to strings

Replace manual dictionary creation with model-based approach:

**Before:**

```python
# Old way - manual dict creation
user_dict = {
    "first_name": user_data.first_name,
    "last_name": user_data.last_name,
    "email": user_data.email,
    # ... more fields
}
result = await db.users.insert_one(user_dict)
```

**After:**

```python
# New way - using models and utilities
from core.mongo_utils import model_to_mongo_doc, transform_mongo_doc

user = User(
    first_name=user_data.first_name,
    last_name=user_data.last_name,
    email=user_data.email,
    # ... more fields
)
user_doc = model_to_mongo_doc(user)
result = await db.users.insert_one(user_doc)
```

### Step 3: Update Query Operations

**Finding by ID:**

```python
# Before
user = await db.users.find_one({"_id": ObjectId(user_id)})

# After
user = await db.users.find_one({"_id": str(user_id)})  # UUID stored as string
```

**Updating documents:**

```python
# Before
await db.users.update_one(
    {"_id": ObjectId(user_id)},
    {"$set": {"name": "New Name"}}
)

# After
await db.users.update_one(
    {"_id": str(user_id)},  # UUID as string
    {"$set": {"name": "New Name"}}
)
```

## 3. Example Router Updates

Here's how to update a typical router function:

```python
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    current_user: User = Depends(get_current_user)
):
    # Create the model instance
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        # ... other fields
    )

    # Convert to MongoDB document
    user_doc = model_to_mongo_doc(user)

    # Insert into database
    result = await request.app.state.mongodb.users.insert_one(user_doc)

    # Retrieve and return the created document
    created_user = await request.app.state.mongodb.users.find_one({"_id": result.inserted_id})
    return transform_mongo_doc(created_user, UserResponse)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(get_current_user)
):
    # Query using UUID string
    user_doc = await request.app.state.mongodb.users.find_one({"_id": str(user_id)})

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    return transform_mongo_doc(user_doc, UserResponse)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: UUID,
    user_data: UpdateUserRequest,
    current_user: User = Depends(get_current_user)
):
    # Update using UUID string
    update_data = user_data.model_dump(exclude_none=True)

    result = await request.app.state.mongodb.users.update_one(
        {"_id": str(user_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    # Return updated document
    updated_user = await request.app.state.mongodb.users.find_one({"_id": str(user_id)})
    return transform_mongo_doc(updated_user, UserResponse)
```

## 4. Important Notes

1. **String Storage**: UUIDs are stored as strings in MongoDB for better compatibility
2. **Query Format**: Always use `str(uuid_value)` when querying by ID
3. **Model Consistency**: Use the utility functions to ensure consistent conversion
4. **Existing Data**: Run the migration script to convert existing ObjectIds to UUIDs

## 5. Testing

After migration, test your endpoints to ensure:

- ✅ Creating new documents works
- ✅ Querying by ID works
- ✅ Updating documents works
- ✅ Relationships between documents are maintained
