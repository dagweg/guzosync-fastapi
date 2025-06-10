// Simple script to test if the FastAPI backend is running and accessible
const axios = require('axios');

const API_BASE_URL = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws';

async function testBackendConnection() {
  console.log('🔍 Testing GuzoSync FastAPI Backend Connection...\n');

  // Test 1: Basic API Health Check
  try {
    console.log('1. Testing API health...');
    const response = await axios.get(`${API_BASE_URL}/config/languages`, { timeout: 5000 });
    console.log('   ✅ API is responding');
  } catch (error) {
    console.log('   ❌ API connection failed:', error.message);
    console.log('   💡 Make sure your FastAPI server is running on http://localhost:8000');
    return;
  }

  // Test 2: Check if buses endpoint exists
  try {
    console.log('2. Testing buses endpoint...');
    const response = await axios.get(`${API_BASE_URL}/buses`, { timeout: 5000 });
    console.log(`   ✅ Buses endpoint working (${response.data.length || 0} buses found)`);
  } catch (error) {
    if (error.response?.status === 401) {
      console.log('   ⚠️  Buses endpoint requires authentication (this is expected)');
    } else {
      console.log('   ❌ Buses endpoint error:', error.message);
    }
  }

  // Test 3: Check if bus stops endpoint exists
  try {
    console.log('3. Testing bus stops endpoint...');
    const response = await axios.get(`${API_BASE_URL}/buses/stops`, { timeout: 5000 });
    console.log(`   ✅ Bus stops endpoint working (${response.data.length || 0} stops found)`);
  } catch (error) {
    if (error.response?.status === 401) {
      console.log('   ⚠️  Bus stops endpoint requires authentication (this is expected)');
    } else {
      console.log('   ❌ Bus stops endpoint error:', error.message);
    }
  }

  // Test 4: Check WebSocket endpoint (basic connection test)
  console.log('4. Testing WebSocket endpoint...');
  try {
    const WebSocket = require('ws');
    const ws = new WebSocket(`${WS_URL}/connect?token=test`);
    
    ws.on('open', () => {
      console.log('   ✅ WebSocket endpoint is accessible');
      ws.close();
    });

    ws.on('error', (error) => {
      if (error.code === 'ECONNREFUSED') {
        console.log('   ❌ WebSocket connection refused - check if backend is running');
      } else {
        console.log('   ⚠️  WebSocket connection error (may be due to invalid token):', error.message);
      }
    });

    ws.on('close', (code, reason) => {
      if (code === 4001) {
        console.log('   ✅ WebSocket endpoint working (authentication required)');
      }
    });

    // Give WebSocket time to connect
    await new Promise(resolve => setTimeout(resolve, 2000));
    
  } catch (error) {
    console.log('   ❌ WebSocket test failed:', error.message);
  }

  console.log('\n🎉 Backend connection test completed!');
  console.log('\n📋 Next steps:');
  console.log('   1. Make sure you have demo users in your database');
  console.log('   2. Get a Mapbox access token');
  console.log('   3. Update .env.local with your Mapbox token');
  console.log('   4. Run: npm run dev');
  console.log('   5. Open: http://localhost:3000');
}

// Run the test
testBackendConnection().catch(console.error);
