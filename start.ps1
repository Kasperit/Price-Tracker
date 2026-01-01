# Start both backend and frontend
$backend = Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\venv\Scripts\Activate.ps1; python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000" -PassThru
$frontend = Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev" -PassThru

Write-Host "Started backend (PID: $($backend.Id)) and frontend (PID: $($frontend.Id))"
Write-Host "Press Ctrl+C to stop this script (servers will keep running)"
Write-Host "To stop servers, close their terminal windows or run: Stop-Process -Id $($backend.Id),$($frontend.Id)"
