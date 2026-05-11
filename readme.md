# InkControl

Sistema web para gestão de estúdio de tatuagem (agendamentos, clientes, tatuadores, portfólio, saúde do cliente), conforme o **Documento de Visão do Produto** do projeto acadêmico.

**Stack:** React 18 · Django 5 + Django REST Framework · PostgreSQL 17 (ou SQLite para desenvolvimento rápido).

## Pré-requisitos

- Python 3.11+
- Node.js 20+ (recomendado 24+)
- Docker Desktop (opcional, para PostgreSQL)

## Configuração rápida

### 1. Ambiente Python

Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Variáveis de ambiente

```powershell
copy .env.example .env
```

Ajuste `.env` se necessário. Sem `POSTGRES_*`, o back-end usa **SQLite** em `backend/db.sqlite3`.

### 3. PostgreSQL com Docker (opcional)

```powershell
docker compose up -d
```

Depois defina no `.env` os valores de `POSTGRES_*` como em `.env.example` (`POSTGRES_HOST=localhost`).

### 4. Migrações e servidor Django

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver
```

(O `python` acima está no venv da raiz do repositório: `InkControl\.venv`.)

### 5. Front-end (Vite)

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra [http://localhost:5173](http://localhost:5173). O Vite encaminha `/api` para `http://127.0.0.1:8000`.

Teste direto da API: [http://127.0.0.1:8000/api/health/](http://127.0.0.1:8000/api/health/)

## Endpoints iniciais

- `POST /api/auth/register/` cria usuario e retorna token
- `POST /api/auth/login/` login por e-mail/senha e retorna token
- `GET /api/auth/me/` dados do usuario autenticado
- `POST /api/auth/logout/` invalida token atual
- `GET/POST /api/clients/` lista/cria clientes
- `GET/PUT/PATCH/DELETE /api/clients/{id}/` CRUD de cliente
- `GET/POST /api/tattooers/` lista/cria tatuadores
- `GET/PUT/PATCH/DELETE /api/tattooers/{id}/` CRUD de tatuador
- `GET/POST /api/appointments/` lista/cria agendamentos
- `GET/PUT/PATCH/DELETE /api/appointments/{id}/` CRUD de agendamento
- `POST /api/appointments/{id}/cancel/` cancela o agendamento (transicao permitida)
- `GET/PATCH /api/studio-settings/` expediente do estudio (PATCH apenas papel `studio`)
- `POST /api/auth/link-tattooer-profile/` vincula usuario tatuador a um cadastro `Tattooer` (apenas `studio`; corpo `user_id`, `tattooer_id`)
- `PATCH /api/auth/me/` tatuador pode enviar `tattooer` (id do cadastro ou vazio para limpar)
- `GET/POST /api/appointment-change-requests/` listar e criar solicitacoes de alteracao (conteudo/agenda)
- `POST /api/appointment-change-requests/{id}/accept/` aceita proposta e aplica no agendamento
- `POST /api/appointment-change-requests/{id}/reject/` recusa proposta
- `GET/PATCH /api/notifications/` notificacoes in-app do usuario autenticado
- `GET/POST /api/health-forms/` lista/cria formulario de saude do cliente
- `GET/PUT/PATCH/DELETE /api/health-forms/{id}/` CRUD do formulario de saude

Alteracoes de conteudo/agenda (data/hora, descricao, modalidade, tatuador, imagem de referencia, duracao) por **cliente** ou **tatuador** devem ir em `POST /api/appointment-change-requests/` com `proposed_changes` (JSON) e opcionalmente `proposed_reference_image` (multipart). O **estudio** continua podendo editar agendamentos diretamente com `PUT/PATCH`. Transicoes de **status** e **cancelamento** permanecem diretas na API de agendamentos.

Criacao de solicitacao (`proposed_changes`): chaves permitidas `scheduled_at` (ISO 8601), `description`, `appointment_kind` (`service`|`consultation`), `tattooer` (id), `clear_reference_image` (booleano), `duration_minutes` (15 a 480). Quem pode **aceitar/recusar** depende de quem pediu: pedido do **cliente** notifica estudio + tatuador vinculado; pedido do **tatuador** notifica estudio + cliente (usuario com e-mail do `Client`); pedido do **estudio** notifica tatuador vinculado + cliente.

Regra de conflito de horario:

- cada agendamento tem `duration_minutes` (padrao 60); o sistema bloqueia **sobreposicao de intervalos** `[scheduled_at, scheduled_at + duration)` entre agendamentos do mesmo tatuador
- agendamentos com status `cancelled` nao entram no bloqueio

Comando de limpeza de imagens (apos 7 dias de `done`):

- `python manage.py purge_expired_appointment_reference_images`

Filtros de agenda por periodo:

- `GET /api/appointments/?period=day&date=YYYY-MM-DD`
- `GET /api/appointments/?period=week&date=YYYY-MM-DD`
- `GET /api/appointments/?period=month&date=YYYY-MM-DD`
- se `date` nao for informado, usa a data atual

Busca e filtros:

- clientes: `GET /api/clients/?q=<texto>&is_active=true|false`
- tatuadores: `GET /api/tattooers/?q=<texto>&is_active=true|false`
- agendamentos:
  - `GET /api/appointments/?q=<texto>&status=<status>`
  - `GET /api/appointments/?tattooer=<id>&client=<id>`
  - `GET /api/appointments/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- ficha de saude: `GET /api/health-forms/?q=<texto>&client=<id>`

Paginacao:

- todas as listagens retornam formato paginado DRF (`count`, `next`, `previous`, `results`)
- tamanho padrao da pagina: `10`

Permissoes por papel (RBAC inicial):

- `studio`
  - acesso completo a clientes, tatuadores, agendamentos e formularios de saude
- `tattooer`
  - pode listar/visualizar tatuadores e agendamentos; **clientes** e **fichas de saude** apenas dos clientes com sessao com o tatuador vinculado ao perfil
  - pode atualizar **status** do agendamento diretamente; demais campos de agenda/conteudo via solicitacao de alteracao
  - nao pode criar/excluir clientes e tatuadores
- `client`
  - pode listar/visualizar tatuadores, agendamentos e formularios de saude
  - pode criar agendamentos e formularios de saude
  - nao pode criar/editar/excluir clientes e tatuadores

Transicoes de status permitidas:

- `requested` -> `waiting_budget | confirmed | cancelled`
- `waiting_budget` -> `confirmed | cancelled`
- `confirmed` -> `in_progress | cancelled`
- `in_progress` -> `done | cancelled`
- `done` e `cancelled` nao permitem avancar para outros estados

Para rotas autenticadas, envie o header:

`Authorization: Token <seu_token>`

## Estrutura

| Pasta | Conteúdo |
|--------|-----------|
| `backend/` | Projeto Django (`config/`), app `studio` (API em `/api/…`) |
| `frontend/` | React 18 + Vite |
| `requirements.txt` | Dependências Python |

## Próximos passos (DVP)

Autenticação (login, recuperação de senha), CRUD de clientes e tatuadores, agendamentos com validação de horário, formulário de saúde, upload de imagens (ex.: Cloudflare R2), notificações por e-mail.
