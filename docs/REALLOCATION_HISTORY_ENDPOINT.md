# Reallocation History Endpoint

## Overview

A comprehensive endpoint has been created to retrieve reallocation history with advanced filtering and enriched data. This endpoint provides a unified view of both formal reallocation requests (from regulators) and direct reallocations (from control center admins).

## Endpoint Details

**URL:** `GET /api/control-center/reallocation-history`

**Authentication:** Requires `CONTROL_CENTER_ADMIN` role

**Response Model:** `List[ReallocationHistoryResponse]`

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bus_id` | string | No | Filter by specific bus ID |
| `route_id` | string | No | Filter by route ID (matches old or new route) |
| `status_filter` | string | No | Filter by status (PENDING, APPROVED, REJECTED, COMPLETED) |
| `start_date` | string | No | Start date filter (YYYY-MM-DD format) |
| `end_date` | string | No | End date filter (YYYY-MM-DD format) |
| `skip` | integer | No | Number of records to skip (default: 0) |
| `limit` | integer | No | Maximum records to return (default: 20, max: 100) |

## Response Schema

The `ReallocationHistoryResponse` includes:

```json
{
  "id": "string",
  "bus_id": "string",
  "bus_number": "string",           // Bus license plate for display
  "old_route_id": "string",
  "old_route_name": "string",       // Resolved route name
  "new_route_id": "string", 
  "new_route_name": "string",       // Resolved route name
  "reason": "OVERCROWDING",         // ReallocationReason enum
  "description": "string",
  "priority": "NORMAL",             // NORMAL, HIGH, URGENT
  "status": "COMPLETED",            // ReallocationStatus enum
  "requested_by_user_id": "string", // For formal requests
  "requested_by_name": "string",    // Resolved user name
  "reallocated_by": "string",       // For direct reallocations
  "reallocated_by_name": "string",  // Resolved user name
  "reviewed_by": "string",
  "reviewed_by_name": "string",     // Resolved user name
  "reviewed_at": "string",
  "reallocated_at": "string",
  "review_notes": "string",
  "reallocation_type": "FORMAL_REQUEST", // or "DIRECT_REALLOCATION"
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Features

### 1. Unified Data View
- Combines both formal reallocation requests and direct reallocations
- Normalizes different data structures into a consistent response format
- Identifies reallocation type (`FORMAL_REQUEST` vs `DIRECT_REALLOCATION`)

### 2. Data Enrichment
- Resolves bus license plates for better display
- Resolves route names from route IDs
- Resolves user names from user IDs
- Provides comprehensive context for each reallocation

### 3. Advanced Filtering
- **Bus filtering:** Find all reallocations for a specific bus
- **Route filtering:** Find reallocations involving a specific route (as source or destination)
- **Status filtering:** Filter by reallocation status
- **Date range filtering:** Filter by creation or reallocation date
- **Pagination:** Efficient handling of large datasets

### 4. Performance Optimized
- Uses MongoDB aggregation pipeline for efficient data processing
- Single database query with joins for all related data
- Proper indexing support for filtering operations

## Usage Examples

### Basic Usage
```bash
GET /api/control-center/reallocation-history
```

### Filter by Bus
```bash
GET /api/control-center/reallocation-history?bus_id=bus-123
```

### Filter by Route
```bash
GET /api/control-center/reallocation-history?route_id=route-456
```

### Filter by Status
```bash
GET /api/control-center/reallocation-history?status_filter=COMPLETED
```

### Date Range Filter
```bash
GET /api/control-center/reallocation-history?start_date=2024-01-01&end_date=2024-01-31
```

### Combined Filters with Pagination
```bash
GET /api/control-center/reallocation-history?bus_id=bus-123&status_filter=COMPLETED&limit=10&skip=0
```

## Error Handling

- **403 Forbidden:** User doesn't have CONTROL_CENTER_ADMIN role
- **400 Bad Request:** Invalid date format in start_date or end_date
- **500 Internal Server Error:** Database or server error

## Testing

A test script `test_reallocation_history.py` has been provided to verify the endpoint functionality. Update the credentials in the script and run:

```bash
python test_reallocation_history.py
```

## Database Collections Used

- `reallocation_requests` - Primary collection for reallocation data
- `buses` - For bus information (license plate)
- `routes` - For route names
- `users` - For user names (requested_by, reallocated_by, reviewed_by)

## Implementation Notes

1. **Data Normalization:** The endpoint handles two different reallocation data structures:
   - Formal requests: `current_route_id` → `requested_route_id`
   - Direct reallocations: `old_route_id` → `new_route_id`

2. **Aggregation Pipeline:** Uses MongoDB's aggregation framework for:
   - Efficient filtering
   - Data enrichment through lookups
   - Field normalization and computed fields

3. **Response Consistency:** All responses follow the same schema regardless of the underlying data structure

4. **Security:** Restricted to CONTROL_CENTER_ADMIN role only

This endpoint provides comprehensive visibility into all reallocation activities, making it easier for administrators to track, analyze, and audit bus reallocation decisions.
