#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Testing Loop Hospital Voice Agent API ==="
echo ""

echo "1. Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo -e "\n"

echo "2. Test Query #1: Tell me 3 hospitals around Bangalore"
curl -s -X POST "$BASE_URL/converse" \
  -H "Content-Type: application/json" \
  -d '{"text":"Tell me 3 hospitals around Bangalore"}' | python3 -m json.tool | head -20
echo -e "\n"

echo "3. Test Query #2: Manipal Sarjapur in Bangalore"
curl -s -X POST "$BASE_URL/converse" \
  -H "Content-Type: application/json" \
  -d '{"text":"Can you confirm if Manipal Sarjapur in Bangalore is in my network?"}' | python3 -m json.tool | head -20
echo -e "\n"

echo "4. Out-of-scope Query:"
curl -s -X POST "$BASE_URL/converse" \
  -H "Content-Type: application/json" \
  -d '{"text":"What is the weather today?"}' | python3 -m json.tool
echo -e "\n"

echo "=== All tests completed ===" 
