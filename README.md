# Course Odoo (`curso_odoo`)

Study addon to register lessons in Odoo and expose CRUD operations via a JSON-RPC API.

## Technologies and Versions

- Odoo 16.0, defined by the `odoo:16.0` image in `compose.yaml`.
- PostgreSQL 15.
- pgAdmin via the `dpage/pgadmin4:latest` image.
- Python `>=3.12` declared in `pyproject.toml` and fixed in `.python-version` (local environment; the Odoo server runs inside the Docker image).
- No external application Python dependencies declared in `pyproject.toml`; `requirements.txt` installs the project locally in editable mode.

The only custom addon found in the repository is `curso_odoo`. The installation state of modules in an Odoo database cannot be confirmed solely by project files; it requires verifying the running database.

## Structure

```text
addons/curso_odoo/
├── controllers/
│   ├── lessons_api.py
│   ├── controllers.py
│   └── __init__.py
├── models/
│   ├── lesson.py
│   └── __init__.py
├── security/
│   ├── ir.model.access.csv
│   └── models.py
├── views/
├── demo/
│   └── demo.xml
└── __manifest__.py

compose.yaml
config/odoo.conf
.env.example
src/odoo/__init__.py
```

`src/odoo/__init__.py` is a demo entrypoint printing "Hello from odoo!"; it is not the Odoo server. `security/models.py`, `views/templates.xml`, `views/views.xml`, and `demo/demo.xml` are empty, and the manifest does not load demo or empty XML files. No repositories, services, custom groups, or record rules (`ir.rule`) are defined. Persistence logic resides in the ORM model, and controllers access this model directly.

## Lesson Model

The Python `Lesson` model is located at `addons/curso_odoo/models/lesson.py` and registers the technical model name `lesson.odoo`. It inherits from `odoo.models.Model` and contains:

- `name`: Required text (`Char`) for the lesson name.
- `desc`: Optional text (`Char`) for the description.
- `duration`: Required selection field with options for 1, 5, or 10 minutes (`one_minute`, `five_minutes`, `ten_minutes`); defaults to `ten_minutes`.

There are no relationships with other models. Tree/form views, actions, and corresponding menus reside in separate XML files.

## Configuration and Execution

Prerequisites: Docker and Docker Compose plugin. Compose reads a `.env` file at the root. Create it from the example and replace placeholder values with local secrets:

```bash
cp .env.example .env
```

Do not use example values as production credentials or share the `.env` file. It should not be version controlled.

Start services:

```bash
docker compose up -d
docker compose logs -f odoo
```

Odoo exposes port 8069 and mounts `./addons` to `/mnt/extra-addons`. The `config/odoo.conf` file includes this path in `addons_path`. Create or select the database directly via the Odoo web interface.

To install, open Odoo at `http://localhost:8069`, select/create a database, update the app list if needed, and install **Course Odoo**. To update the addon from the command line, use the image CLI (replacing the placeholder with your confirmed database name):

```bash
docker compose exec odoo odoo -d <DATABASE_NAME> -u curso_odoo --stop-after-init
```

Compose also defines a pgAdmin service on port 5050. HTTPS, reverse proxy, and public domain configurations are not present; the HTTP address above is intended for local development.

## Security and Current Permissions

`security/ir.model.access.csv` grants read, write, create, and unlink permissions on the `lesson.odoo` model to the standard internal group `base.group_user`. This rule was kept to allow CRUD usage via the addon interface.

**The API is public**: `/lessons/list`, `/lessons/create`, `/lessons/update`, and `/lessons/delete` use `auth="public"` and `sudo()`. Removing the ACL does not protect these routes; they require an authentication/authorization mechanism before being exposed outside a study environment.

## JSON-RPC API Endpoints

The endpoints reside in `addons/curso_odoo/controllers/lessons_api.py`. All endpoints accept `POST`, are `type="json"`, use `auth="public"`, and disable CSRF protection.

### Summary Table

| Method | Endpoint Path | Description |
| :--- | :--- | :--- |
| `POST` | `/lessons/list` | Retrieve all lessons |
| `POST` | `/lessons/create` | Create a new lesson |
| `POST` | `/lessons/update` | Update an existing lesson |
| `POST` | `/lessons/delete` | Delete an existing lesson |

### 1. List Lessons

```bash
curl 'http://localhost:8069/lessons/list' \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"call","params":{},"id":1}'
```

### 2. Create Lesson

```bash
curl 'http://localhost:8069/lessons/create' \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"call","params":{"name":"Introduction","desc":"First lesson overview","duration":"ten_minutes"},"id":2}'
```

### 3. Update Lesson

```bash
curl 'http://localhost:8069/lessons/update' \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"call","params":{"id":1,"duration":"five_minutes"},"id":3}'
```

### 4. Delete Lesson

```bash
curl 'http://localhost:8069/lessons/delete' \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"call","params":{"id":1},"id":4}'
```

## Limitations and Pending Items

- Active database and installed modules must be verified on the running environment.
- Public routes utilize `sudo()` and actions do not require user identity validation.
- No custom authentication, token system, CORS configuration, TLS, or record rules are currently defined in this repository.
