# Registro de decisões, problemas e melhorias

Este arquivo registra escolhas e lacunas de forma transparente. Atualize cada item com data, contexto, decisão e consequência; não apague decisões antigas, marque-as como substituídas.

## Decisões

| ID | Decisão | Motivo | Consequência |
| --- | --- | --- | --- |
| ADR-001 | monólito modular em Django/DRF | domínio pequeno e prazo curto | operação simples; limites internos devem ser preservados |
| ADR-002 | PostgreSQL e ORM do Django | integridade, transações e SQL parametrizado | mudanças de schema passam por migrations |
| ADR-003 | JWT de curta duração | API desacoplada e sem sessão de servidor | exige expiração, rotação e tratamento seguro no cliente |
| ADR-004 | filtro de consultas via query string | representa filtragem da coleção | contrato simples: `?professional={id}` |
| ADR-005 | imagem imutável promovida entre ambientes | reduz diferença entre staging e produção | release identificado por SHA/digest, não por `latest` |
| ADR-006 | migrations expand/contract | preserva rollback do código | remoções de schema exigem mais de uma release |
| ADR-007 | integração Asaas atrás de adapter | isola domínio de detalhes externos | adiciona uma pequena camada, facilita mock e troca |
| ADR-008 | UUID como chave pública | evita IDs sequenciais previsíveis na API | clientes tratam IDs como strings opacas |
| ADR-009 | exclusão protegida de profissional | preservar integridade e histórico de consultas | exclusão com consultas retorna `409` |
| ADR-010 | consulta futura e horário único por profissional | impedir agenda inválida/duplicada no modelo mínimo | validação na API e constraint no banco |

## Problemas e riscos encontrados

| ID | Situação | Tratamento |
| --- | --- | --- |
| ERR-001 | enunciado não define paciente, status, duração nem conflito de agenda | manter modelo mínimo e registrar evolução, sem inventar regra clínica |
| ERR-002 | campo “Data” não esclarece data versus data/hora/timezone | usar instante ISO 8601 com timezone; o projeto adota `America/Sao_Paulo` por padrão |
| ERR-003 | formato de contato e endereço não é especificado | validar obrigatoriedade/tamanho sem impor padrão brasileiro não solicitado |
| ERR-004 | política de exclusão de profissional com consultas não é definida | usar `PROTECT`, devolver `409` e cobrir o comportamento em teste |
| ERR-005 | autenticação é aberta a alternativas | adotar um mecanismo único e proteger todas as rotas de negócio por padrão |
| ERR-006 | split e eventos exatos dependem do contrato/API atual do Asaas | manter como proposta e validar documentação vigente antes de implementar |
| ERR-007 | refresh tokens são rotacionados, mas a blacklist não está habilitada | access token curto reduz exposição; adicionar blacklist/revogação antes de uso real |

## Melhorias priorizadas

### Curto prazo

- adicionar busca textual e ordenação com allowlists (a paginação e o filtro por profissional já existem);
- adotar throttling distribuído em Redis e proteção específica no login;
- publicar o schema OpenAPI validado pela CI como artefato versionado;
- ampliar testes de autorização por objeto, timezone e concorrência real no PostgreSQL;
- adicionar SAST, SBOM, assinatura da imagem e política para achados do scanner do ECR;
- criar alarmes e smoke tests automáticos pós-deploy.

### Evolução de produto

- modelar paciente com autorização por objeto e minimização de dados;
- definir status e máquina de estados da consulta;
- duração, especialidade, timezone e regras de disponibilidade;
- prevenção de sobreposição com transação/constraint apropriada;
- cancelamento, reagendamento e trilha de auditoria;
- notificações assíncronas com consentimento e preferências;
- política clara para retenção, anonimização e exclusão de dados.

### Operação

- SLOs de disponibilidade e latência;
- dashboards, tracing e alarmes acionáveis;
- exercícios de restauração do RDS e de rollback;
- autoscaling orientado por CPU, memória e latência;
- WAF e regras de bloqueio conforme perfil real de tráfego;
- mover tasks para subnets privadas e usar NAT/VPC endpoints conforme o modelo de custo e ameaça;
- configurar domínio, certificado ACM obrigatório e redirecionamento integral para HTTPS;
- criar alarmes CloudWatch acionáveis para 5xx, latência, tasks e RDS;
- rotação automatizada de segredos e revisão periódica de acessos.

## Checklist antes de produção

- [ ] `DEBUG` desabilitado e hosts/origens explícitos;
- [ ] credenciais exclusivas por ambiente e fora do repositório;
- [ ] migrations testadas com volume representativo;
- [ ] backup, PITR e restauração validados;
- [ ] health checks e alarmes ativos;
- [ ] rate limits e política de autenticação revisados;
- [ ] logs revisados contra vazamento de dados;
- [ ] imagem verificada e executada como usuário não-root;
- [ ] smoke test e rollback exercitados;
- [ ] responsáveis e runbook de incidente definidos.
