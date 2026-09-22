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

  Views
    ↓
  Serializers / Permissions
    ↓
  Services
    ↓
  Models
    ↓
  PostgreSQL


Principais endpoints

  Método	Endpoint	Descrição
  GET	/requests/	Lista solicitações permitidas ao usuário
  POST	/requests/	Cria uma nova solicitação
  GET	/requests/{id}/	Consulta uma solicitação
  PATCH	/requests/{id}/	Atualiza uma solicitação
  PATCH	/requests/{id}/change-status/	Altera o status
  GET	/requests/{id}/history/	Consulta o histórico

Filtros

  Filtrar por status:
  
  GET /requests/?status=RESOLVED
  
  Buscar por texto:
  
  GET /requests/?search=buraco

Controle de acesso
  Perfil	Permissões principais
  Citizen	Cria e acompanha suas próprias solicitações
  Staff	Gerencia solicitações do próprio departamento
  Admin	Acesso administrativo às solicitações
  
O sistema também restringe alterações de acordo com o status da solicitação e o departamento responsável.


Testes

  Execute a suíte de testes com:
  
  python manage.py test

Os testes cobrem autenticação, permissões, solicitações, alteração de status, histórico, filtros e transações.

Instalação

  git clone <URL_DO_REPOSITORIO>
  cd urbanize

  python -m venv venv
  venv\Scripts\activate
  
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py runserver

O projeto utiliza variáveis de ambiente para configuração do banco de dados e informações sensíveis.

Roadmap
 Reclassificação de solicitações
 Auditoria de eventos
 Reatribuição entre departamentos
 Documentação da API
 Processamento assíncrono
 Docker
 CI/CD
