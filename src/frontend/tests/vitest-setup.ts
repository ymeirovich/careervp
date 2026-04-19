// Provide required env vars so api/client.ts initialises without throwing
process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID = 'us-east-1_testpool';
process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID = 'testclientid';
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:3000';
