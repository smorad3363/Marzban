[CmdletBinding()]
param(
    [switch]$RebuildImage
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dashboardRoot = Join-Path $projectRoot "app\dashboard"
$mysqlContainer = "marzban-dev-mysql"
$mysqlVolume = "marzban-dev-mysql-data"
$mysqlImage = "mysql:8.0"
$appContainer = "marzban-dev-app"
$imageName = "marzban-dev:local"
$databaseUrl = "mysql+pymysql://root:dev-root-password@host.docker.internal:33079/marzban_dev"

function Require-Command([string]$Name, [string]$InstallHint) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "$Name پیدا نشد. $InstallHint"
    }
    return $command.Source
}

$docker = Require-Command "docker" "Docker Desktop را نصب و اجرا کنید."
$code = Require-Command "code" "در VS Code گزینه Shell Command/Path را فعال کنید."

$nodeCommand = Get-Command "node" -ErrorAction SilentlyContinue
$node = if ($nodeCommand) {
    $nodeCommand.Source
} else {
    $bundledNode = "C:\Users\Saji\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    if (Test-Path -LiteralPath $bundledNode) { $bundledNode } else { $null }
}
if (-not $node) {
    throw "Node.js پیدا نشد. Node.js LTS را نصب کنید."
}

$vite = Join-Path $dashboardRoot "node_modules\vite\bin\vite.js"
if (-not (Test-Path -LiteralPath $vite)) {
    throw "وابستگی‌های Frontend نصب نیست. داخل app\dashboard دستور npm install را یک‌بار اجرا کنید."
}

& $docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop اجرا نیست. آن را باز کنید و دوباره همین دستور را بزنید."
}

$imageId = & $docker image ls --quiet $imageName
if ($RebuildImage -or -not $imageId) {
    Write-Host "ساخت image توسعه؛ فقط بار اول طولانی است..." -ForegroundColor Cyan
    $devDockerfile = Join-Path $PSScriptRoot "Dockerfile.dev"
    & $docker build --file $devDockerfile --tag $imageName $projectRoot
    if ($LASTEXITCODE -ne 0) { throw "ساخت Docker image شکست خورد." }
}

$mysqlId = & $docker ps --all --quiet --filter "name=^/$mysqlContainer$"
if (-not $mysqlId) {
    $mysqlImageId = & $docker image ls --quiet $mysqlImage
    if (-not $mysqlImageId) {
        Write-Host "دانلود MySQL 8.0؛ فقط بار اول..." -ForegroundColor Cyan
        & $docker pull $mysqlImage
        if ($LASTEXITCODE -ne 0) { throw "دانلود MySQL 8.0 شکست خورد." }
    }
    & $docker volume create $mysqlVolume *> $null
    & $docker run --detach `
        --name $mysqlContainer `
        --publish "127.0.0.1:33079:3306" `
        --volume "${mysqlVolume}:/var/lib/mysql" `
        --env "MYSQL_ROOT_PASSWORD=dev-root-password" `
        --env "MYSQL_DATABASE=marzban_dev" `
        --health-cmd "mysqladmin ping -h 127.0.0.1 -uroot -pdev-root-password --silent" `
        --health-interval "2s" `
        --health-timeout "2s" `
        --health-retries "60" `
        $mysqlImage *> $null
    if ($LASTEXITCODE -ne 0) { throw "ساخت MySQL آزمایشی شکست خورد؛ پورت 33079 را بررسی کنید." }
} else {
    $mysqlRunning = & $docker inspect --format "{{.State.Running}}" $mysqlContainer
    if ($mysqlRunning -ne "true") {
        & $docker start $mysqlContainer *> $null
    }
}

$mysqlReady = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    $health = & $docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}" $mysqlContainer
    if ($health -eq "healthy") {
        $mysqlReady = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $mysqlReady) { throw "MySQL آزمایشی آماده نشد. docker logs $mysqlContainer" }

$dockerCommon = @(
    "--rm",
    "--add-host", "host.docker.internal:host-gateway",
    "--volume", "${projectRoot}:/code",
    "--workdir", "/code",
    "--env", "SQLALCHEMY_DATABASE_URL=$databaseUrl",
    "--env", "TEST_MYSQL_DATABASE_URL=$databaseUrl",
    "--env", "XRAY_JSON=/code/xray_config.json",
    "--entrypoint", "python",
    $imageName
)

Write-Host "اجرای migration و ساخت داده نمونه..." -ForegroundColor Cyan
& $docker run @dockerCommon -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic migration شکست خورد." }
& $docker run @dockerCommon -m scripts.dev_seed
if ($LASTEXITCODE -ne 0) { throw "ساخت داده نمونه شکست خورد." }

$oldAppId = & $docker ps --all --quiet --filter "name=^/$appContainer$"
if ($oldAppId) {
    & $docker rm --force $appContainer *> $null
}

& $docker run --detach `
    --rm `
    --name $appContainer `
    --publish "127.0.0.1:8000:8000" `
    --add-host "host.docker.internal:host-gateway" `
    --volume "${projectRoot}:/code" `
    --workdir "/code" `
    --env "SQLALCHEMY_DATABASE_URL=$databaseUrl" `
    --env "TEST_MYSQL_DATABASE_URL=$databaseUrl" `
    --env "XRAY_JSON=/code/xray_config.json" `
    --env "UVICORN_HOST=0.0.0.0" `
    --env "UVICORN_PORT=8000" `
    --env "DOCS=true" `
    --env "ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000" `
    --env "STAGE11_BACKUP_ENABLED=false" `
    --entrypoint "python" `
    $imageName `
    -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /code *> $null
if ($LASTEXITCODE -ne 0) { throw "Backend اجرا نشد؛ پورت 8000 را بررسی کنید." }

Start-Process -FilePath $code -ArgumentList @("--reuse-window", $projectRoot)

$browserScript = @"
for (`$attempt = 0; `$attempt -lt 90; `$attempt++) {
    try {
        `$response = Invoke-WebRequest -Uri 'http://127.0.0.1:3000/dashboard/index.html' -UseBasicParsing -TimeoutSec 1
        if (`$response.StatusCode -eq 200) {
            Start-Process 'http://127.0.0.1:3000/dashboard/index.html#/login'
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 1
}
"@
$browserCommand = [Convert]::ToBase64String(
    [Text.Encoding]::Unicode.GetBytes($browserScript)
)
Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-EncodedCommand",
    $browserCommand
)

$env:VITE_BASE_API = "http://127.0.0.1:8000/api/"
Write-Host ""
Write-Host "Dev آماده است؛ با Ctrl+C متوقف می‌شود." -ForegroundColor Green
Write-Host "Panel: http://127.0.0.1:3000/dashboard/index.html#/login"
Write-Host "Owner: owner / DevOwner@1405"
Write-Host "Admins: plan_admin, usage_admin, frozen_admin / DevAdmin@1405"
Write-Host "Backend logs: docker logs -f $appContainer"

Push-Location $dashboardRoot
try {
    & $node $vite --host 127.0.0.1 --port 3000 --base /dashboard/
} finally {
    Pop-Location
    & $docker stop $appContainer *> $null
}
