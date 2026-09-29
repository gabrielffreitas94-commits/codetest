<#
.SYNOPSIS
    Script auxiliar para build, teste local e deploy da imagem Docker no AWS Lambda.
.DESCRIPTION
    1. Build local da imagem Docker
    2. Teste do Lambda Runtime Interface Emulator (porta 9000 -> 8080)
    3. Autenticação e Push para o Amazon ECR
    4. Atualização da função AWS Lambda
#>

param(
    [string]$AwsAccountId = "<SEU_AWS_ACCOUNT_ID>",
    [string]$Region = "us-east-1",
    [string]$RepositoryName = "engineering-insight-service",
    [string]$FunctionName = "generate-team-insight",
    [string]$ImageTag = "latest",
    [switch]$BuildOnly,
    [switch]$RunLocal
)

$EcrUri = "$AwsAccountId.dkr.ecr.$Region.amazonaws.com/$RepositoryName"

Write-Host "==> 1. Fazendo build da imagem Docker..." -ForegroundColor Cyan
docker build -t "$RepositoryName`:$ImageTag" .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha no build da imagem Docker."
    exit 1
}

if ($BuildOnly) {
    Write-Host "Build concluído com sucesso!" -ForegroundColor Green
    exit 0
}

if ($RunLocal) {
    Write-Host "==> Iniciando container localmente com o Lambda Runtime Interface Emulator..." -ForegroundColor Cyan
    Write-Host "URL de invocação local: http://localhost:9000/2015-03-31/functions/function/invocations" -ForegroundColor Yellow
    Write-Host "Pressione Ctrl+C para encerrar." -ForegroundColor Yellow
    docker run --rm -p 9000:8080 "$RepositoryName`:$ImageTag"
    exit 0
}

Write-Host "==> 2. Autenticando no Amazon ECR ($Region)..." -ForegroundColor Cyan
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "$AwsAccountId.dkr.ecr.$Region.amazonaws.com"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha na autenticação com o Amazon ECR. Verifique se o AWS CLI e as credenciais estão configurados."
    exit 1
}

Write-Host "==> 3. Taggeando e enviando imagem para o ECR ($EcrUri`:$ImageTag)..." -ForegroundColor Cyan
docker tag "$RepositoryName`:$ImageTag" "$EcrUri`:$ImageTag"
docker push "$EcrUri`:$ImageTag"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao enviar a imagem para o ECR."
    exit 1
}

Write-Host "==> 4. Atualizando código da função Lambda ($FunctionName)..." -ForegroundColor Cyan
aws lambda update-function-code `
    --function-name $FunctionName `
    --image-uri "$EcrUri`:$ImageTag" `
    --region $Region

Write-Host "Deploy no AWS Lambda concluído com sucesso!" -ForegroundColor Green
