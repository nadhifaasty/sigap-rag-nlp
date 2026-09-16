$ErrorActionPreference = "Stop"
$email = "nadhifaasty@gmail.com"

$pass = Read-Host -AsSecureString -Prompt "Password GFW (ketik, tidak akan tampil)"
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($pass)
$plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

$tok = Invoke-RestMethod -Method Post -Uri "https://data-api.globalforestwatch.org/auth/token" `
    -Body @{ username = $email; password = $plain }
$token = $tok.access_token
if (-not $token) { Write-Host "GAGAL: respons token berisi:"; $tok | ConvertTo-Json -Depth 5; exit 1 }
Write-Host ("ACCESS TOKEN OK: " + $token.Length + " karakter")

$keyBody = @{ alias = "sigap-hutan"; email = $email; organization = "Tugas NLP"; domains = @() } | ConvertTo-Json
$keyResp = Invoke-RestMethod -Method Post -Uri "https://data-api.globalforestwatch.org/auth/apikey" `
    -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body $keyBody

$a = $keyResp.api_key
if (-not $a) { $a = $keyResp.data.api_key }
if (-not $a -and $keyResp.data -and $keyResp.data.GetType().Name -eq "String") { $a = $keyResp.data }
if (-not $a) { Write-Host "GAGAL: respons apikey belum ter-parse:"; $keyResp | ConvertTo-Json -Depth 5; exit 1 }

if (-not (Test-Path -LiteralPath ".env")) { New-Item -ItemType File -Path ".env" | Out-Null }
if (Select-String -LiteralPath ".env" -Pattern "^GFW_API_KEY=" -Quiet) {
    (Get-Content ".env") | ForEach-Object {
        if ($_ -match "^GFW_API_KEY=") { "GFW_API_KEY=$a" } else { $_ }
    } | Set-Content ".env"
} else {
    Add-Content -Path ".env" -Value "GFW_API_KEY=$a"
}
Write-Host "SUKSES. GFW_API_KEY tersimpan di .env"