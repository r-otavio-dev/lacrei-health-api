# API de gerenciamento de consultas — Lacrei Saúde

[![CI](https://github.com/r-otavio-dev/lacrei-health-api/actions/workflows/ci.yml/badge.svg)](https://github.com/r-otavio-dev/lacrei-health-api/actions/workflows/ci.yml)

API REST para cadastrar profissionais de saúde e gerenciar consultas vinculadas a essas pessoas. O projeto foi desenhado para ser reproduzível localmente, seguro por padrão e preparado para entrega contínua em ambientes separados de staging e produção.

## Funcionalidades

- CRUD de profissionais de saúde;
- CRUD de consultas, sempre vinculadas a um profissional existente;
- filtro de consultas por ID do profissional;
- autenticação da API;
- validação consistente e respostas somente em JSON;
- documentação OpenAPI interativa;
- logs de acesso e erro (JSON em produção) sem corpo, token ou query string;
- PostgreSQL, Poetry, Docker e pipeline de CI/CD.

## Arquitetura

```mermaid
flowchart LR
    Client[Cliente da API] -->|HTTPS + token| ALB[Application Load Balancer]
    ALB --> API[Django REST Framework\nECS/Fargate]
    API --> DB[(PostgreSQL / RDS)]
    API --> Logs[CloudWatch Logs]
    GHA[GitHub Actions] -->|imagem versionada| ECR[Amazon ECR]
    ECR --> API
    Secrets[AWS Secrets Manager] --> API
```

O detalhamento de componentes, decisões e limites está em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Pré-requisitos

Escolha uma das formas de execução:

- Docker Desktop com Docker Compose; ou
- Python compatível com a versão definida em `pyproject.toml`, Poetry e PostgreSQL.

## Configuração

Copie o arquivo de exemplo e ajuste somente o necessário:

```bash
cp .env.example .env
```

O Docker Compose lê `.env` automaticamente. Em execução local sem Docker, exporte as mesmas variáveis no terminal antes de iniciar o Django; o projeto não carrega arquivos `.env` por conta própria. Nunca envie `.env`, credenciais, chaves ou tokens ao repositório.

| Variável | Finalidade | Exemplo local |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | assinatura criptográfica do Django/JWT | valor longo e aleatório |
| `DJANGO_DEBUG` | modo de depuração | `true` somente localmente |
| `DJANGO_ALLOWED_HOSTS` | hosts HTTP aceitos, separados por vírgula | `localhost,127.0.0.1` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | origens web permitidas | `http://localhost:3000` |
| `DATABASE_URL` | conexão PostgreSQL, com precedência sobre componentes; aceita opções SSL na query string | `postgresql://lacrei:senha@localhost:5432/lacrei` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | alternativa em componentes ao `DATABASE_URL` | conforme seu PostgreSQL |
| `POSTGRES_SSLMODE` | modo TLS do PostgreSQL; em produção o padrão é `require` | `require` |

## Executar com Docker

```bash
docker compose up --build
```

O entrypoint aguarda o banco e, por padrão, executa migrações e coleta arquivos estáticos. Para executar comandos administrativos em outro terminal:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

A API ficará disponível em `http://localhost:8000`. Para encerrar:

```bash
docker compose down
```

Use `docker compose down -v` apenas quando quiser apagar também o banco local.

## Executar localmente

Com um PostgreSQL acessível e as variáveis de ambiente configuradas:

```bash
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver
```

Para criar uma conta administrativa:

```bash
poetry run python manage.py createsuperuser
```

## Testes, lint e qualidade

```bash
poetry run python manage.py test
poetry run ruff check .
poetry run ruff format --check .
```

Os testes de API usam `APITestCase` e cobrem os CRUDs, o filtro por profissional, autenticação e cenários inválidos. Se o projeto expuser cobertura, execute:

```bash
poetry run coverage run manage.py test
poetry run coverage report --fail-under=90
```

## API e autenticação

As rotas e exemplos completos estão em [docs/API.md](docs/API.md). Visão rápida:

| Método | Rota | Descrição |
| --- | --- | --- |
| `POST` | `/api/v1/auth/token/` | obter tokens de acesso e renovação |
| `POST` | `/api/v1/auth/token/refresh/` | renovar token de acesso |
| `POST` | `/api/v1/auth/token/verify/` | verificar um token |
| `GET`, `POST` | `/api/v1/professionals/` | listar ou criar profissionais |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/v1/professionals/{id}/` | operar em um profissional |
| `GET` | `/api/v1/professionals/{id}/appointments/` | consultas do profissional |
| `GET`, `POST` | `/api/v1/appointments/` | listar ou criar consultas |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/v1/appointments/{id}/` | operar em uma consulta |
| `GET` | `/api/v1/appointments/?professional={id}` | buscar consultas por profissional |
| `GET` | `/api/schema/` | especificação OpenAPI |
| `GET` | `/api/docs/` | Swagger UI |
| `GET` | `/api/redoc/` | ReDoc |
| `GET` | `/health/live/` | liveness do processo |
| `GET` | `/health/ready/` | readiness, incluindo o banco |

Exemplo autenticado:

```bash
curl http://localhost:8000/api/v1/professionals/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

## Segurança

- consultas ao banco são feitas pelo ORM do Django, com parâmetros separados do SQL; não há concatenação de entrada do usuário em SQL;
- serializers validam tipo, tamanho, obrigatoriedade, formato, data futura e relacionamentos antes de persistir dados;
- autenticação é exigida nas rotas de negócio e a autorização deve seguir o princípio do menor privilégio;
- CORS usa uma lista explícita de origens confiáveis; curingas não são adequados em produção;
- segredos entram por variáveis de ambiente/AWS Secrets Manager;
- cookies, HTTPS, hosts e headers de segurança possuem configuração distinta para produção;
- logs são JSON em produção e não registram token, senha, segredo, corpo ou dados pessoais completos;
- imagens rodam com usuário não-root e dependências travadas pelo Poetry.

Mais detalhes e o modelo de ameaças estão em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#segurança).

## CI/CD e ambientes AWS

O fluxo previsto em GitHub Actions é:

1. **Lint:** análise estática e verificação de formatação;
2. **Test:** PostgreSQL efêmero, migrações e testes automatizados;
3. **Build:** imagem Docker imutável identificada pelo SHA do commit;
4. **Deploy staging:** publicação automática a partir da branch principal;
5. **Deploy produção:** build da mesma revisão Git já validada em staging, após aprovação protegida.

Staging e produção têm contas ou, no mínimo, VPCs, bancos, serviços e segredos separados. A aplicação roda em ECS/Fargate atrás de ALB; as imagens ficam no ECR; o banco é RDS PostgreSQL; logs ficam no CloudWatch. Produção exige certificado ACM e redireciona HTTP para HTTPS no ALB. Alarmes e domínio/DNS são melhorias operacionais recomendadas.

O passo a passo, verificações pós-deploy e permissões OIDC estão em [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Rollback

Cada release usa uma imagem imutável. Em falha de health check, o ECS interrompe o rollout e mantém a versão anterior. Para rollback manual, execute novamente o workflow escolhendo o SHA/tag previamente saudável e atualize o serviço para a task definition correspondente.

Migrações destrutivas não devem ser entregues na mesma etapa em que o código deixa de aceitar o esquema antigo. Use a estratégia **expand/contract** descrita em [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#rollback).

## Decisões e evolução

- [docs/API.md](docs/API.md): contrato HTTP e exemplos;
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): arquitetura, segurança e escolhas técnicas;
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): CI/CD, AWS, observabilidade e rollback;
- [docs/ASAAS_INTEGRATION.md](docs/ASAAS_INTEGRATION.md): proposta de split de pagamentos;
- [docs/DECISIONS_AND_IMPROVEMENTS.md](docs/DECISIONS_AND_IMPROVEMENTS.md): decisões, problemas encontrados e melhorias futuras.

## Licença e uso de dados

Este repositório é uma demonstração técnica. Não use dados reais de pacientes ou profissionais no ambiente local, nos testes ou em logs.
