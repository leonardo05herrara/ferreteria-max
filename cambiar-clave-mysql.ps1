$ErrorActionPreference = "Stop"
$clave = "FerreteriaMax2026"
$mysqld = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe"
$mysqladmin = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqladmin.exe"
$defaults = "C:\ProgramData\MySQL\MySQL Server 8.0\my.ini"
$init = Join-Path $env:TEMP "ferreteria-mysql-init.txt"

@"
ALTER USER 'root'@'localhost' IDENTIFIED BY '$clave';
FLUSH PRIVILEGES;
"@ | Set-Content -Path $init -Encoding ASCII

Write-Host "Deteniendo MySQL80..."
Stop-Service MySQL80 -Force
Start-Sleep -Seconds 3

Write-Host "Aplicando la contraseña nueva..."
$proc = Start-Process -FilePath $mysqld -ArgumentList @(
    "--defaults-file=$defaults",
    "--init-file=$init"
) -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 18

try {
    & $mysqladmin --defaults-file=$defaults -u root "-p$clave" shutdown 2>$null
} catch {
}

Start-Sleep -Seconds 3
Get-Process mysqld -ErrorAction SilentlyContinue | Where-Object { $_.Id -eq $proc.Id } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "Iniciando MySQL80..."
Start-Service MySQL80
Start-Sleep -Seconds 3

Remove-Item $init -Force -ErrorAction SilentlyContinue

$configPath = Join-Path $PSScriptRoot "config.json"
$cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$cfg.password = $clave
$cfg | ConvertTo-Json -Depth 6 | Set-Content $configPath -Encoding UTF8

python -c "import pymysql,json; c=json.load(open(r'''$configPath''',encoding='utf-8')); pymysql.connect(host=c['host'],port=int(c['port']),user=c['user'],password=c['password']); print('Conexion OK')"
