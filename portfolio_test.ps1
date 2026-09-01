# Portfolio API Test Script
$baseUrl = "http://localhost:8001"
$token = $null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PORTFOLIO API TEST SUITE" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Test 0: Login to get token
Write-Host "TEST 0: Login to get access token" -ForegroundColor Yellow
Write-Host "POST $baseUrl/api/auth/login"
$loginBody = @{
    email = "testuser12345@test.com"
    password = "TestPass123!"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/api/auth/login" -Method POST -ContentType "application/json" -Body $loginBody
    $token = $loginResponse.access_token
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Token received: $($token.Substring(0, 20))..." -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $token"
}

# Test 1: Check Portfolio Setup Status
Write-Host "TEST 1: Check Portfolio Setup Status (Before)" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/portfolio/setup"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/portfolio/setup" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    
    if ($response.setup_complete -eq $false) {
        Write-Host "PASS: setup_complete is FALSE (new user)" -ForegroundColor Green
    } else {
        Write-Host "WARN: setup_complete is already TRUE" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 2: Save Portfolio Setup
Write-Host "TEST 2: Save Portfolio Setup" -ForegroundColor Yellow
Write-Host "POST $baseUrl/api/portfolio/setup"
$setupBody = @{
    cash_balance = 500000
    holdings = @(
        @{ symbol = "RELIANCE.NS"; qty = 10; price = 2450 }
        @{ symbol = "TCS.NS"; qty = 5; price = 3450 }
    )
    setup_complete = $true
} | ConvertTo-Json -Depth 5

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/portfolio/setup" -Method POST -Headers (@{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }) -Body $setupBody
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    Write-Host "PASS: Portfolio setup saved" -ForegroundColor Green
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $reader.BaseStream.Position = 0
    $reader.DiscardBufferedData()
    Write-Host "Body: $($reader.ReadToEnd())" -ForegroundColor Red
}
Write-Host ""

# Test 3: Get Portfolio Summary After Setup
Write-Host "TEST 3: Get Portfolio Summary" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/portfolio/summary"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/portfolio/summary" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 5)" -ForegroundColor Gray
    
    if ($response.cash_balance -eq 500000) {
        Write-Host "PASS: Cash balance is 500000" -ForegroundColor Green
    } else {
        Write-Host "FAIL: Cash balance is $($response.cash_balance)" -ForegroundColor Red
    }
    
    if ($response.positions -and $response.positions.Count -gt 0) {
        Write-Host "PASS: Positions are created ($($response.positions.Count) positions)" -ForegroundColor Green
    } else {
        Write-Host "FAIL: No positions found" -ForegroundColor Red
    }
    
    Write-Host "Total Value: $($response.total_value)" -ForegroundColor Cyan
    Write-Host "Total P&L: $($response.total_pnl)" -ForegroundColor Cyan
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 4: Get Daily P&L
Write-Host "TEST 4: Get Daily P&L" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/portfolio/daily-pnl"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/portfolio/daily-pnl" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    
    if ($response.daily_pnl -ne $null) {
        Write-Host "PASS: Daily P&L data returned" -ForegroundColor Green
    } else {
        Write-Host "WARN: No daily P&L data yet" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 5: Get Earnings Potential
Write-Host "TEST 5: Get Earnings Potential" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/portfolio/earnings-potential"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/portfolio/earnings-potential" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    
    if ($response.earnings_potential -ne $null) {
        Write-Host "PASS: Earnings potential data returned" -ForegroundColor Green
    } else {
        Write-Host "INFO: Earnings potential response received" -ForegroundColor Gray
    }
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 6: Get Performance Metrics
Write-Host "TEST 6: Get Performance Metrics" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/portfolio/performance-metrics"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/portfolio/performance-metrics" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    
    Write-Host "PASS: Performance metrics returned" -ForegroundColor Green
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 7: Check Setup Status Again
Write-Host "TEST 7: Check Portfolio Setup Status (After)" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/portfolio/setup"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/portfolio/setup" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    
    if ($response.setup_complete -eq $true) {
        Write-Host "PASS: setup_complete is now TRUE" -ForegroundColor Green
    } else {
        Write-Host "FAIL: setup_complete is still FALSE" -ForegroundColor Red
    }
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 8: Get Watchlist
Write-Host "TEST 8: Get Watchlist" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/watchlists"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/watchlists" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    Write-Host "PASS: Watchlist data returned" -ForegroundColor Green
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

# Test 9: Get Alerts
Write-Host "TEST 9: Get Alerts" -ForegroundColor Yellow
Write-Host "GET $baseUrl/api/alerts"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/alerts" -Method GET -Headers $headers
    Write-Host "Status: 200 OK" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Gray
    Write-Host "PASS: Alerts data returned" -ForegroundColor Green
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "TEST SUITE COMPLETED" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
