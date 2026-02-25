import crypto from 'crypto';
import fetch from 'node-fetch';
import querystring from 'querystring';

// Configuration
const config = {
  clientId: "30d5ffe8fa5548fe826768902ad90660",
  clientSecret: "dd3b2b4e44eb4c8f9bc4cf311bba4f12",
  accessToken: "eb36e41518ca443a95005bb23c748f1a",
  accessTokenSecret: "59ace7b23b874a768184a42efdea2f74"
};

const baseUrl = "https://platform.fatsecret.com/rest/server.api";

function generateTimestamp() {
  return Math.floor(Date.now() / 1000).toString();
}

function generateNonce() {
  return crypto.randomBytes(16).toString('hex');
}

function generateSignature(method, url, params, consumerSecret, tokenSecret = '') {
  const sortedParams = Object.keys(params)
    .sort()
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');

  const signatureBaseString = [
    method.toUpperCase(),
    encodeURIComponent(url),
    encodeURIComponent(sortedParams)
  ].join('&');

  const signingKey = `${encodeURIComponent(consumerSecret)}&${encodeURIComponent(tokenSecret)}`;

  return crypto
    .createHmac('sha1', signingKey)
    .update(signatureBaseString)
    .digest('base64');
}

function dateToFatSecretFormat(dateString) {
  if (!dateString) {
    dateString = new Date().toISOString().split('T')[0];
  }
  const date = new Date(dateString + 'T00:00:00Z');
  const epochStart = new Date('1970-01-01T00:00:00Z');
  return Math.floor((date - epochStart) / (1000 * 60 * 60 * 24)).toString();
}

async function addFoodEntry(foodId, servingId, numberOfUnits, mealType, foodEntryName, date) {
  const timestamp = generateTimestamp();
  const nonce = generateNonce();
  const fatSecretDate = dateToFatSecretFormat(date);

  // Build all parameters
  const params = {
    method: "food_entry.create",
    food_id: foodId,
    food_entry_name: foodEntryName,
    serving_id: servingId,
    number_of_units: numberOfUnits.toString(),
    meal: mealType,
    date: fatSecretDate,
    format: "json",
    oauth_consumer_key: config.clientId,
    oauth_nonce: nonce,
    oauth_signature_method: "HMAC-SHA1",
    oauth_timestamp: timestamp,
    oauth_token: config.accessToken,
    oauth_version: "1.0"
  };

  // Generate signature
  const signature = generateSignature('POST', baseUrl, params, config.clientSecret, config.accessTokenSecret);
  params.oauth_signature = signature;

  try {
    const response = await fetch(baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: querystring.stringify(params)
    });

    const text = await response.text();
    console.log('Response status:', response.status);
    console.log('Response text:', text);

    try {
      const json = JSON.parse(text);
      return json;
    } catch {
      return { rawResponse: text };
    }
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}

// Fix kefir entry - use correct serving for 110g
addFoodEntry("5712907", "5547103", 110, "other", "Kéfir Hacendado 110g")
  .then(result => {
    console.log('Kefir 110g added:', JSON.stringify(result, null, 2));
  })
  .catch(error => {
    console.error('Failed to add kefir 110g:', error);
  });