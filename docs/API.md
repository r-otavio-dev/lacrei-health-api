# Contrato da API

Base local: `http://localhost:8000`

Todos os corpos e respostas usam JSON. Datas e horários seguem ISO 8601. O servidor armazena instantes com timezone e responde com offset explícito.

## Autenticação

Obtenha um par de tokens:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "api-user",
  "password": "uma-senha-forte"
}
```

Resposta `200 OK`:

```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

Envie o access token em todas as rotas de negócio:

```http
Authorization: Bearer eyJ...
```

Renovação:

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{"refresh": "eyJ..."}
```

O access token dura 15 minutos e o refresh, 7 dias por padrão; ambos podem ser ajustados por ambiente. O refresh token é rotacionado a cada uso. A versão atual não mantém blacklist, portanto um refresh anterior continua válido até expirar; habilitar revogação é uma melhoria recomendada antes de lidar com contas reais. Clientes devem armazenar tokens em mecanismo seguro, nunca em logs ou URLs.

Para verificar sintaxe e validade de um token sem renová-lo:

```http
POST /api/v1/auth/token/verify/
Content-Type: application/json

{"token": "eyJ..."}
```

## Profissionais

### Listar

```http
GET /api/v1/professionals/
Authorization: Bearer TOKEN
Accept: application/json
```

### Criar

```http
POST /api/v1/professionals/
Authorization: Bearer TOKEN
Content-Type: application/json

{
  "social_name": "Ana Silva",
  "profession": "Psicologia",
  "address": "Rua Exemplo, 100",
  "contact": "ana@example.org"
}
```

Resposta esperada: `201 Created`, com o recurso e seu `id` no formato UUID, além de `created_at` e `updated_at`.

### Consultar, substituir, editar ou remover

```http
GET /api/v1/professionals/{id}/
PUT /api/v1/professionals/{id}/
PATCH /api/v1/professionals/{id}/
DELETE /api/v1/professionals/{id}/
```

`PUT` exige todos os campos editáveis; `PATCH` aceita atualização parcial. A remoção retorna `204 No Content` quando concluída. Um profissional com consultas vinculadas não pode ser excluído e retorna `409 Conflict` com o código `professional_has_appointments`.

Também é possível listar diretamente as consultas de uma pessoa profissional:

```http
GET /api/v1/professionals/{uuid}/appointments/
Authorization: Bearer TOKEN
```

## Consultas

### Listar e filtrar por profissional

```http
GET /api/v1/appointments/
GET /api/v1/appointments/?professional=550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer TOKEN
Accept: application/json
```

O filtro usa o UUID exato do profissional. `professional_id` é aceito como alias de `professional`. Um filtro válido sem resultados retorna `200 OK` e `results` vazio; um UUID malformado retorna `400 Bad Request`.

### Criar

```http
POST /api/v1/appointments/
Authorization: Bearer TOKEN
Content-Type: application/json

{
  "date": "2026-10-21T14:30:00-03:00",
  "professional": "550e8400-e29b-41d4-a716-446655440000"
}
```

O profissional precisa existir e a data precisa estar no futuro. O mesmo profissional não pode ter duas consultas no mesmo instante; a regra é validada pela API e por uma constraint no banco. Datas inválidas/ausentes, duplicidade e relacionamentos inexistentes retornam `400 Bad Request`.

### Consultar, substituir, editar ou remover

```http
GET /api/v1/appointments/{id}/
PUT /api/v1/appointments/{id}/
PATCH /api/v1/appointments/{id}/
DELETE /api/v1/appointments/{id}/
```

## Códigos de resposta

| Código | Uso |
| --- | --- |
| `200` | leitura ou alteração concluída |
| `201` | recurso criado |
| `204` | recurso removido, sem corpo |
| `400` | JSON, campo, filtro ou regra de negócio inválida |
| `401` | credencial ausente, inválida ou expirada |
| `403` | identidade válida, mas sem autorização |
| `404` | recurso não encontrado |
| `405` | método HTTP não aceito na rota |
| `409` | conflito com o estado atual, como exclusão protegida |
| `415` | tipo de conteúdo não suportado |
| `429` | limite de requisições excedido |
| `500` | falha interna não exposta ao cliente |

Todo erro usa um envelope consistente. `request_id` também é devolvido no header `X-Request-ID` e permite localizar a requisição nos logs:

```json
{
  "error": {
    "code": "invalid",
    "message": "Não foi possível processar a requisição.",
    "details": {
      "date": ["Este campo é obrigatório."]
    },
    "request_id": "d95dfe65-f02a-4d3f-b761-9fe7b9769855"
  }
}
```

Exemplo de autenticação ausente:

```json
{
  "error": {
    "code": "not_authenticated",
    "message": "As credenciais de autenticação não foram fornecidas.",
    "details": {
      "detail": "As credenciais de autenticação não foram fornecidas."
    },
    "request_id": "d95dfe65-f02a-4d3f-b761-9fe7b9769855"
  }
}
```

Mensagens não devem revelar stack traces, SQL, configuração ou segredos.

## Paginação e ordenação

Listagens são paginadas por padrão, com 20 itens por página salvo configuração diferente em `API_PAGE_SIZE`:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": []
}
```

Clientes não devem depender da ordem implícita do banco. Quando a API oferecer ordenação, use apenas os campos publicados no schema OpenAPI.

## OpenAPI

- schema: `/api/schema/`;
- Swagger UI: `/api/docs/`;
- ReDoc: `/api/redoc/`.

O schema publicado é a fonte de verdade para nomes de campos, formatos, paginação e filtros. Em CI, recomenda-se validar que o schema pode ser gerado sem avisos.
