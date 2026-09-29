# 🚀 Serviço de Insights de Produtividade de Engenharia

Serviço backend desenvolvido em **Python** e **FastAPI** para cálculo determinístico de métricas de engenharia (como tempo médio de ciclo de PRs, contagem de PRs mergeados, deploys e incidentes) e geração de insights acionáveis via integração resiliente com LLM (Large Language Model).

---

## 📋 Pré-requisitos

* **Python 3.10+** instalado (o projeto foi desenvolvido e testado no Python 3.14).
* Gerenciador de pacotes **`pip`** ou **`uv`**.
* Git (opcional, para controle de versão).

---

## 🛠️ Passo a Passo para Execução

### 1. Clonar o Repositório e Acessar a Pasta

```bash
git clone https://github.com/gabrielffreitas94-commits/codetest.git
cd codetest
```

---

### 2. Criar e Ativar o Ambiente Virtual

Recomenda-se o uso de um ambiente virtual isolado para instalar as dependências.

#### No Windows (PowerShell):
```powershell
# Criar o ambiente virtual
python -m venv .venv

# Ativar o ambiente virtual
.\.venv\Scripts\Activate.ps1
```

> **Nota para PowerShell**: Caso receba um erro de permissão de execução de scripts, execute previamente no terminal:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

#### No Linux / macOS:
```bash
# Criar o ambiente virtual
python3 -m venv .venv

# Ativar o ambiente virtual
source .venv/bin/activate
```

---

### 3. Instalar as Dependências

Com o ambiente virtual ativado, instale os pacotes necessários:

```bash
# Usando pip padrão:
pip install -r requirements.txt

# Ou usando uv (ultra-rápido):
uv pip install -r requirements.txt
```

As principais dependências instaladas são:
* `fastapi`: Framework web assíncrono moderno e de alta performance.
* `uvicorn[standard]`: Servidor ASGI para rodar a aplicação.
* `pydantic-settings`: Gestão de configurações e variáveis de ambiente.
* `pytest`, `pytest-cov`, `httpx`: Suíte de testes automatizados e cliente de teste.

---

### 4. Executar os Testes Automatizados

O projeto conta com **35 testes automatizados com 100% de cobertura de código**, cobrindo o core de métricas determinísticas, validação de eventos, casos de borda de PRs órfãos, prompt seguro, retries com LLM e endpoints HTTP da API.

#### Executar todos os testes:
```bash
pytest
```

#### Executar os testes com relatório de cobertura (Coverage 100%):
```bash
pytest --cov=app --cov-report=term-missing
```

---

### 5. Iniciar o Servidor FastAPI

Para iniciar a API em modo de desenvolvimento (com recarregamento automático a cada alteração de código):

```bash
uvicorn app.main:app --reload
```

O servidor iniciará no endereço: `http://127.0.0.1:8000`.

---

## 📖 Documentação Interativa da API

Com o servidor rodando, acesse no navegador:

* **Swagger UI (Interativo)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📡 Como Testar os Endpoints

### 1. Health Check
Verifica se a aplicação está ativa e operante.

* **Método**: `GET`
* **URL**: `http://127.0.0.1:8000/api/v1/health`

#### Testando via cURL (Linux/macOS/Git Bash):
```bash
curl -X GET http://127.0.0.1:8000/api/v1/health
```

#### Testando via PowerShell (Windows):
```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/health"
```

**Resposta esperada (`200 OK`)**:
```json
{
  "status": "ok"
}
```

---

### 2. Geração de Insights de Time
Processa a lista de eventos de engenharia, calcula as métricas determinísticas e gera o insight estruturado.

* **Método**: `POST`
* **URL**: `http://127.0.0.1:8000/api/v1/generate_team_insight`
* **Header**: `Content-Type: application/json`

#### Exemplo de Payload de Requisição (`body.json`):
```json
{
  "team_id": "platform",
  "events": [
    {
      "type": "pr_opened",
      "id": "pr-1",
      "timestamp": "2026-01-01T09:00:00Z"
    },
    {
      "type": "pr_merged",
      "id": "pr-1",
      "timestamp": "2026-01-02T09:00:00Z"
    },
    {
      "type": "deployment",
      "timestamp": "2026-01-03T12:00:00Z"
    },
    {
      "type": "incident",
      "timestamp": "2026-01-04T12:00:00Z"
    }
  ]
}
```

#### Testando via cURL:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/generate_team_insight \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "platform",
    "events": [
      {"type": "pr_opened", "id": "pr-1", "timestamp": "2026-01-01T09:00:00Z"},
      {"type": "pr_merged", "id": "pr-1", "timestamp": "2026-01-02T09:00:00Z"},
      {"type": "deployment", "timestamp": "2026-01-03T12:00:00Z"},
      {"type": "incident", "timestamp": "2026-01-04T12:00:00Z"}
    ]
  }'
```

#### Resposta Esperada (`200 OK`):
```json
{
  "team_id": "platform",
  "metrics": {
    "merged_prs": 1,
    "average_pr_cycle_time_hours": 24.0,
    "deployments": 1,
    "incidents": 1
  },
  "insight": {
    "summary": "The team merged one pull request with an average cycle time of 24 hours.",
    "recommendations": [
      "Continue monitoring pull request cycle time."
    ]
  }
}
```

---

## 🏛️ Estrutura do Código

```text
codetest/
├── app/
│   ├── main.py                                  # Ponto de entrada da aplicação FastAPI
│   ├── core/
│   │   ├── config.py                            # Configurações de ambiente (BaseSettings)
│   │   └── generate_team_insight.py             # Lógica pura de negócio (Stdlib Only)
│   └── api/v1/
│       ├── router.py                            # Agregador de rotas da API v1
│       └── endpoints/
│           ├── health.py                        # Endpoint de verificação de integridade
│           └── generate_team_insight.py         # Endpoint REST com injeção de dependência
├── tests/
│   ├── api/
│   │   └── test_endpoints.py                    # Testes de integração dos endpoints FastAPI
│   └── core/
│       ├── fixtures.py                          # Massa de dados mockada para testes
│       └── test_generate_team_insight.py        # Testes unitários do core (27 testes)
├── Dockerfile                                   # Imagem base oficial AWS Lambda (Python 3.12)
├── .dockerignore                                # Arquivos ignorados no build do container
├── deploy_lambda.ps1                            # Script PowerShell para build, teste local e deploy ECR/Lambda
├── pytest.ini                                   # Configuração de descoberta do pytest
├── requirements.txt                             # Dependências do projeto (FastAPI, Mangum, etc.)
└── README.md                                    # Guia completo do projeto
```

---

## 🐳 Executando com Docker e Deploy no AWS Lambda

A aplicação utiliza o adaptador **Mangum** (`handler = Mangum(app)`) em `app/main.py`, permitindo rodar tanto em servidores ASGI tradicionais (Uvicorn) quanto em funções serverless do AWS Lambda através de **Lambda Container Images**.

### 1. Build da Imagem Docker Localmente
```bash
docker build -t engineering-insight-service:latest .
```

### 2. Testar o Container Localmente com o AWS Lambda Emulator
A imagem oficial da AWS já inclui o *Runtime Interface Emulator (RIE)* na porta 8080. Você pode mapeá-la para a porta 9000 local:

```bash
docker run --rm -p 9000:8080 engineering-insight-service:latest
```

Em outro terminal, envie uma chamada de teste:
```bash
# Testar o Health Check:
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"version": "2.0", "rawPath": "/api/v1/health", "requestContext": {"http": {"method": "GET"}}}'
```

### 3. Deploy no AWS Lambda via Amazon ECR

Você pode usar o script automatizado `deploy_lambda.ps1`:
```powershell
.\deploy_lambda.ps1 -AwsAccountId "123456789012" -Region "us-east-1"
```

Ou executar manualmente os passos da AWS CLI:
```bash
# 1. Login no ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# 2. Taggear a imagem
docker tag engineering-insight-service:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/engineering-insight-service:latest

# 3. Enviar para o repositório
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/engineering-insight-service:latest

# 4. Atualizar o Lambda
aws lambda update-function-code \
  --function-name generate-team-insight \
  --image-uri <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/engineering-insight-service:latest \
  --region us-east-1
```


---

## 🔒 Princípios de Design & Boas Práticas

1. **Core Isolado (Standard Library Only)**:
   * Toda a lógica de negócio em `app/core/generate_team_insight.py` usa estritamente a biblioteca padrão do Python (`datetime`, `json`, `typing`).
2. **Privacidade e Minimização de Dados**:
   * O prompt enviado ao LLM contém **exclusivamente as métricas agregadas** e o `team_id`.
   * Registros brutos de eventos, timestamps individuais e IDs de PRs **nunca são enviados ao modelo**.
3. **Resiliência e Bounded Retry**:
   * Em caso de falha transitória (timeout, rede ou resposta malformada do LLM), a função realiza **no máximo 1 retry** (total de 2 tentativas).
4. **Validação Rigorosa**:
   * Timestamps devem obrigatoriamente estar no padrão ISO-8601 UTC terminado em `Z`.
   * Eventos malformados geram `400 Bad Request` com explicação clara do erro.
   * Respostas do LLM que não contenham `summary` (string) e `recommendations` (lista de strings) são rejeitadas.

---

## 🏭 Considerações de Produção

* **FastAPI vs AWS Lambda**:
  * *FastAPI (Containers / ECS / Cloud Run)*: Ideal para APIs de baixa latência e tráfego constante, permitindo conexão persistente com Redis/bancos de dados.
  * *AWS Lambda (Serverless)*: Excelente para execuções esporádicas ou batches noturnos de cálculo de times, mas requer atenção a cold starts e limite de 29s no API Gateway.
* **Timeouts em Camadas**:
  * LLM Client: 10s $\rightarrow$ Serviço da API: 25s $\rightarrow$ Gateway/Load Balancer: 29s.
* **Idempotência e Caching**:
  * Usar Redis ou DynamoDB para armazenar em cache os insights calculados por hash de métricas/data, evitando gastos duplicados com chamadas ao LLM.
