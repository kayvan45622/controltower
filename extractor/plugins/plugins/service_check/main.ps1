param([string]$ServiceName,[string]$Host1=$env:COMPUTERNAME,[string]$Run_Id)

function NowUtc { (Get-Date).ToUniversalTime().ToString("s") + "Z" }

try {
  $svc = Get-Service -Name $ServiceName -ErrorAction Stop
  $status = $svc.Status
} catch {
  $status = "Unknown"
}

$rec = @{
  plugin="service_check"
  plugin_version="1.0.0"
  run_id=$Run_Id
  ts=(NowUtc)
  data=@{ service=$ServiceName; host=$Host1; status=$status }
  errors=@()
} | ConvertTo-Json -Compress

$rec
