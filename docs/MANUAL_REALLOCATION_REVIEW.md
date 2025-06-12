# Manual Reallocation Review Endpoint

## Overview

A new endpoint has been added to allow control center admins to manually review and process reallocation requests without relying on AI automation. This provides full manual control over the approval, rejection, or pending status of reallocation requests.

## Endpoint Details

**URL:** `POST /api/control-center/reallocation-requests/{request_id}/review`

**Authentication:** Requires `CONTROL_CENTER_ADMIN` role

**Request Body:** `ReviewReallocationRequest`

## Request Schema

```json
{
  "action": "APPROVE" | "REJECT" | "PENDING",
  "route_id": "string (optional - required for APPROVE)",
  "reason": "string (optional - notes/reason for the action)"
}
```

## Actions

### 1. APPROVE
- **Required:** `route_id` must be provided
- **Effect:** 
  - Updates bus assignment to the specified route
  - Sets request status to "COMPLETED"
  - Sends route reallocation notifications to affected users
  - Records review details (reviewer, timestamp, notes)

### 2. REJECT
- **Optional:** `reason` can be provided for rejection details
- **Effect:**
  - Sets request status to "REJECTED"
  - Sends reallocation request discarded notification to requesting regulator
  - Records review details with rejection reason

### 3. PENDING
- **Optional:** `reason` can be provided for review notes
- **Effect:**
  - Keeps request status as "PENDING"
  - Updates review information (reviewer, timestamp, notes)
  - No notifications sent (request remains in queue)

## Response Examples

### Successful Approval
```json
{
  "message": "Reallocation request approved successfully",
  "status": "COMPLETED",
  "bus_id": "bus_123",
  "old_route_id": "route_001",
  "new_route_id": "route_002",
  "route_name": "Downtown Express"
}
```

### Successful Rejection
```json
{
  "message": "Reallocation request rejected successfully",
  "status": "REJECTED",
  "reason": "Insufficient resources on requested route"
}
```

### Successful Pending
```json
{
  "message": "Reallocation request kept pending for further review",
  "status": "PENDING",
  "notes": "Needs traffic analysis before decision"
}
```

## Error Responses

### 400 Bad Request
- Missing `route_id` for APPROVE action
- Invalid route (not found or inactive)
- Request already processed
- Invalid action value

### 403 Forbidden
- User is not CONTROL_CENTER_ADMIN

### 404 Not Found
- Reallocation request not found
- Bus not found (during approval)

## Comparison with Existing Endpoints

| Endpoint | Purpose | Control Level |
|----------|---------|---------------|
| `/process` | AI-automated processing | AI decides route |
| `/discard` | Manual rejection only | Admin can only reject |
| `/review` | **Full manual control** | **Admin decides everything** |

## Usage Examples

### Approve with Custom Route
```bash
curl -X POST "http://localhost:8000/api/control-center/reallocation-requests/req_123/review" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "APPROVE",
    "route_id": "route_456",
    "reason": "Optimal route selected after traffic analysis"
  }'
```

### Reject with Reason
```bash
curl -X POST "http://localhost:8000/api/control-center/reallocation-requests/req_123/review" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "REJECT",
    "reason": "Requested route is under maintenance"
  }'
```

### Keep Pending for Later Review
```bash
curl -X POST "http://localhost:8000/api/control-center/reallocation-requests/req_123/review" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "PENDING",
    "reason": "Waiting for route capacity analysis"
  }'
```

## Notifications

The endpoint integrates with the existing notification system:

- **APPROVE:** Sends route reallocation notifications to bus driver, old route regulators, and new route regulators
- **REJECT:** Sends reallocation request discarded notification to the requesting regulator
- **PENDING:** No notifications sent

## Database Updates

All actions update the reallocation request document with:
- `reviewed_by`: Admin user ID
- `reviewed_at`: Timestamp of review
- `review_notes`: Action reason or notes
- `status`: Updated status based on action

For approvals, also updates:
- `requested_route_id`: The approved route ID
- Bus document: `assigned_route_id` field

## Testing

A test script `test_review_reallocation.py` has been created to verify the endpoint functionality. Run it after starting the server:

```bash
python test_review_reallocation.py
```

The test covers:
- Successful approval with route assignment
- Successful rejection with reason
- Successful pending status update
- Validation error handling
- Authentication requirements
