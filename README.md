# Urbanize

API REST para gerenciamento de solicitações e ocorrências urbanas, desenvolvida com Django REST Framework e PostgreSQL.

> Projeto em desenvolvimento.

## Sobre

O Urbanize busca organizar o registro e atendimento de solicitações urbanas, conectando cidadãos aos departamentos responsáveis.

A aplicação possui controle de acesso por diferentes níveis de usuário, fluxo de status, categorias, departamentos e histórico de alterações.

## Tecnologias

  - Python
  - Django
  - Django REST Framework
  - PostgreSQL
  - Git

## Funcionalidades

  - Autenticação e autorização baseada em papéis
  - Criação e gerenciamento de solicitações
  - Categorias e departamentos
  - Controle de acesso por departamento
  - Fluxo de status
  - Histórico de alterações
  - Busca e filtros
  - Validações e regras de negócio
  - Transações para garantir consistência
  - Testes automatizados


## Arquitetura

```text
Views
  ↓
Serializers / Permissions
  ↓
Services
  ↓
Models
  ↓
PostgreSQL
```


Principais endpoints

  | Método  | Endpoint                        | Descrição                                |
  | ------- | ------------------------------- | ---------------------------------------- |
  | `GET`   | `/requests/`                    | Lista solicitações permitidas ao usuário |
  | `POST`  | `/requests/`                    | Cria uma nova solicitação                |
  | `GET`   | `/requests/{id}/`               | Consulta uma solicitação                 |
  | `PATCH` | `/requests/{id}/`               | Atualiza uma solicitação                 |
  | `PATCH` | `/requests/{id}/change-status/` | Altera o status                          |
  | `GET`   | `/requests/{id}/history/`       | Consulta o histórico                     |


## Filtros e busca

A API permite filtrar e pesquisar solicitações diretamente pelo endpoint de listagem.

### Filtrar por status

```http
GET /requests/?status=RESOLVED
```
### Buscar por texto
```http
GET /requests/?search=buraco
```

### Ordenação

Os resultados também podem ser ordenados através do parâmetro `ordering`:

```http
GET /requests/?ordering=created_at
```

Para ordem decrescente, utilize `-` antes do campo:

```http
GET /requests/?ordering=-created_at
```

## Controle de acesso

O acesso às solicitações é definido de acordo com o perfil do usuário:

| Perfil | Permissões principais |
|---|---|
| `Citizen` | Cria e acompanha suas próprias solicitações |
| `Staff` | Gerencia solicitações do próprio departamento |
| `Admin` | Possui acesso administrativo às solicitações |

Além do perfil, algumas operações também são condicionadas ao **status da solicitação** e ao **departamento responsável**.

## Testes

O projeto possui testes automatizados para validar a API e suas regras de negócio.

Os testes abrangem:

- Autenticação e permissões;
- Solicitações;
- Alteração de status;
- Histórico;
- Filtros;
- Transações e rollback.

Para executar a suíte de testes:

```bash
python manage.py test
```


## Pré-requisitos

Antes de executar o projeto, certifique-se de ter instalado:

- Python 3.11.x
- PostgreSQL
- Git


## Instalação

Clone o repositório:

```bash
git clone <URL_DO_REPOSITORIO>
cd urbanize
```

Crie e ative o ambiente virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute as migrations:

```bash
python manage.py migrate
```

Inicie o servidor:

```bash
python manage.py runserver
```

A aplicação estará disponível em:

```text
http://127.0.0.1:8000/
```

> O projeto utiliza variáveis de ambiente para configuração do banco de dados e outras informações sensíveis.

## Roadmap

- [ ] Reclassificação de solicitações
- [ ] Auditoria de eventos
- [ ] Reatribuição entre departamentos
- [ ] Documentação da API
- [ ] Processamento assíncrono
- [ ] Docker
- [ ] CI/CD
