# Render Deployment Troubleshooting Guide

## MongoDB Atlas Authentication Error Fix

### Error: "bad auth: authentication failed" (AtlasError code 8000)

This error typically occurs during deployment to Render when there's a mismatch between local and production MongoDB configurations.

## Your Specific Issue Fix

### Current Connection String (INCORRECT):

```
mongodb+srv://dagtef:123@cluster0.dwp0bxg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
```

### Corrected Connection String (SHOULD BE):

```
mongodb+srv://dagtef:123@cluster0.dwp0bxg.mongodb.net/guzosync?retryWrites=true&w=majority&appName=Cluster0
```

**Key Fix:** Added `/guzosync` before the query parameters to specify the database name.

### Step-by-Step Solutions

### 1. Check MongoDB Atlas Connection String Format

Your MongoDB connection string should follow this exact format:

```
mongodb+srv://<username>:<password>@<cluster-name>.mongodb.net/<database-name>?retryWrites=true&w=majority
```

**Common Issues:**

- Missing `+srv` (should be `mongodb+srv://`, not `mongodb://`)
- Special characters in password not URL-encoded
- Incorrect cluster name or database name
- Missing authentication parameters

### 2. URL Encode Special Characters in Password

If your MongoDB password contains special characters, they must be URL-encoded:

- `@` becomes `%40`
- `#` becomes `%23`
- `$` becomes `%24`
- `%` becomes `%25`
- `/` becomes `%2F`
- `:` becomes `%3A`
- `?` becomes `%3F`
- `&` becomes `%26`
- `=` becomes `%3D`
- `+` becomes `%2B`
- ` ` (space) becomes `%20`

### 3. Environment Variables on Render

Make sure these environment variables are set correctly in Render:

#### Required Environment Variables:

```bash
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
DATABASE_NAME=guzosync
JWT_SECRET=your-production-jwt-secret
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
CLIENT_URL=https://your-frontend-url.com
```

#### Optional but Recommended:

```bash
LOG_LEVEL=INFO
PORT=10000
NODE_ENV=production
```

### 4. MongoDB Atlas Network Access

Ensure your MongoDB Atlas cluster allows connections from Render:

1. **Go to MongoDB Atlas Dashboard**
2. **Navigate to Network Access**
3. **Add IP Address:** `0.0.0.0/0` (Allow access from anywhere)
   - Or specifically add Render's IP ranges if you want more security

### 5. MongoDB Atlas Database User

Verify your database user has the correct permissions:

1. **Go to Database Access in MongoDB Atlas**
2. **Check your user has these roles:**
   - `readWrite` on your database
   - `readWrite` on `admin` database (for authentication)

### 6. Test Connection String Locally

Before deploying, test your production connection string locally:

```python
# Create a test script: test_mongo_connection.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    try:
        # Use your production MongoDB URL
        mongodb_url = "your-production-mongodb-url-here"
        client = AsyncIOMotorClient(mongodb_url)

        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")

        # Test database access
        db = client["guzosync"]  # or your database name
        collections = await db.list_collection_names()
        print(f"✅ Database access successful! Collections: {collections}")

    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run: `python test_mongo_connection.py`

### 7. Render Build and Start Commands

Make sure your Render service is configured correctly:

**Build Command:**

```bash
pip install -r requirements.txt
```

**Start Command:**

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 8. Debug Logging

Temporarily add debug logging to see the exact connection attempt:

Add this to your main.py startup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")

        # Debug logging (remove in production)
        logger.info(f"MongoDB URL (masked): {mongodb_url[:20]}...")
        logger.info(f"Database name: {database_name}")

        if not mongodb_url or not database_name:
            logger.error("MongoDB configuration not found")
            raise RuntimeError("Database configuration missing")

        logger.info("Connecting to MongoDB...")

        app.state.mongodb_client = AsyncIOMotorClient(
            mongodb_url,
            uuidRepresentation="unspecified",
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,         # 10 second connection timeout
            maxPoolSize=10,
            minPoolSize=1
        )
        app.state.mongodb = app.state.mongodb_client[database_name]

        # Test connection
        await app.state.mongodb.command('ping')
        logger.info("Successfully connected to MongoDB")

    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}", exc_info=True)
        raise
```

### 9. Common Connection String Examples

**Correct Format:**

```
mongodb+srv://myuser:mypassword123@mycluster.ab1cd.mongodb.net/guzosync?retryWrites=true&w=majority
```

**With Special Characters (URL-encoded):**

```
mongodb+srv://myuser:my%40pass%23word@mycluster.ab1cd.mongodb.net/guzosync?retryWrites=true&w=majority
```

### 10. Alternative: Use MongoDB Atlas API Key

If password authentication continues to fail, consider using MongoDB Atlas API keys:

1. **Create API Key in Atlas**
2. **Use API key in connection string:**

```
mongodb+srv://<public-key>:<private-key>@<cluster>.mongodb.net/<database>?authSource=%24external&authMechanism=MONGODB-X509
```

## Quick Checklist

- [ ] Connection string uses `mongodb+srv://`
- [ ] Password is URL-encoded if it contains special characters
- [ ] Network access allows `0.0.0.0/0` or Render IPs
- [ ] Database user has `readWrite` permissions
- [ ] Environment variables are set in Render dashboard
- [ ] Connection string tested locally
- [ ] Build and start commands are correct in Render

## Still Having Issues?

If the problem persists:

1. **Check Render logs** for the exact error message
2. **Contact MongoDB Atlas support** if it's an Atlas-specific issue
3. **Try creating a new database user** with a simple password (no special characters)
4. **Test with a completely new cluster** to rule out cluster-specific issues

## Next Steps After Fix

Once MongoDB connection is working:

1. Remove debug logging
2. Set proper environment variables for production
3. Configure proper CORS origins (remove `allow_origins=["*"]`)
4. Set up monitoring and alerting
