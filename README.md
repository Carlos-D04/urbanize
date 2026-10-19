# Urbanize

API REST para registro e acompanhamento de solicitações urbanas,
desenvolvida com Django REST Framework e PostgreSQL.

> **Status:** projeto em desenvolvimento. A API possui regras de
> negócio, autenticação, histórico de alterações e configuração inicial
> de Docker para desenvolvimento.

## 1. O problema

Problemas urbanos — como buracos nas vias, iluminação pública defeituosa
e falhas na coleta de resíduos — precisam ser registrados, encaminhados
ao departamento responsável e acompanhados até sua resolução.

O Urbanize busca organizar esse fluxo em uma API: o cidadão registra uma
solicitação, a solicitação é associada a uma categoria e a um
departamento, e os usuários autorizados acompanham sua evolução. O
objetivo é manter as informações e as alterações organizadas em um único
sistema.

## 2. Quem usa

O sistema diferencia os usuários por papel (`role`):

| Perfil    | Responsabilidade                                                                                   |
|:----------|:---------------------------------------------------------------------------------------------------|
| `CITIZEN` | Registra solicitações e acompanha as próprias solicitações.                                        |
| `STAFF`   | Atua sobre solicitações dentro do escopo de seu departamento, conforme as permissões configuradas. |
| `ADMIN`   | Possui acesso administrativo, de acordo com as permissões implementadas.                           |

O usuário é baseado no `AbstractUser` do Django. Cada usuário possui
e-mail obrigatório e único. Um usuário também pode estar associado a um
departamento; essa associação é especialmente relevante para os usuários
de atendimento.

## 3. As principais regras de negócio

### Solicitações e classificação

Cada solicitação possui título, descrição, localização, autor,
categoria, departamento responsável, status e datas de criação e
atualização. Cada categoria pertence a um departamento.

### Fluxo de status

Os status disponíveis são:

`PENDING` → `IN_REVIEW` → `IN_PROGRESS` → `RESOLVED`

A mudança de status segue as transições permitidas pelo serviço de
negócio. Uma transição inválida deve ser rejeitada, em vez de permitir
que a solicitação pule etapas arbitrariamente.

### Acesso e responsabilidades

A autenticação utiliza JWT. As permissões consideram o papel do usuário
e, nas operações pertinentes, o departamento responsável e o estado da
solicitação. O cidadão deve ter acesso às próprias solicitações; a
atuação do staff é limitada pelas regras de acesso do sistema.

### Histórico e consistência

As mudanças relevantes são registradas em `RequestHistory`, incluindo o
status anterior e o novo status, o usuário responsável e o tipo de
evento. As operações relacionadas à mudança de status e ao registro do
histórico são realizadas em uma transação para manter a consistência dos
dados.

### Notificações

O projeto possui um modelo de notificação associado a um destinatário e
a uma solicitação, com tipos como mudança de status, reclassificação e
nova mensagem. A entrega de notificações por e-mail e seu processamento
confiável ainda precisam ser concluídos e validados como fluxo completo.

## 4. Uma decisão difícil durante o desenvolvimento

Uma decisão importante foi separar as regras de negócio da camada HTTP,
usando serviços para operações como a mudança de status. A view recebe a
requisição e valida a entrada; o serviço concentra a regra de transição,
salva a solicitação e registra o histórico.

Essa separação evita que a regra de negócio fique dependente de um
endpoint específico e facilita testar o comportamento sem misturar toda
a lógica com a resposta HTTP.

Outra decisão foi tratar a notificação como uma operação secundária: a
criação de uma solicitação não deve falhar apenas porque um mecanismo de
notificação está indisponível. A implementação completa desse isolamento
— especialmente com processamento assíncrono e retentativas — continua
sendo uma evolução planejada.


## 5. O que ainda falta

O projeto continua em desenvolvimento. Entre os próximos itens estão:

- Concluir e validar o fluxo de notificações por e-mail.
- Implementar ou finalizar a reclassificação de solicitações e o
  registro completo dos eventos relacionados.
- Avaliar e concluir regras de reatribuição entre departamentos.
- Ampliar os testes automatizados para as regras de negócio e os fluxos
  de integração.
- Completar a documentação dos endpoints e dos fluxos de autenticação.
- Evoluir a configuração Docker e documentar a inicialização em uma
  máquina nova.
- Configurar CI/CD e verificações automatizadas antes de integrar
  alterações.

O estado de cada item deve ser atualizado conforme a implementação real,
sem considerar planejamentos como funcionalidades concluídas.


Esses itens são propostas para evolução, não declarações de que já
estejam implementados.

## 6. Tecnologias e execução

### Tecnologias

- Python 3.13
- Django
- Django REST Framework
- PostgreSQL
- Psycopg
- Simple JWT
- django-filter
- drf-spectacular
- Docker e Docker Compose
- Git

### Pré-requisitos

Para executar localmente, instale Python compatível com o projeto, Git e
PostgreSQL. Para executar a API em container, instale Docker Desktop com
Docker Compose.

### Configuração local

Clone o repositório e entre na pasta:

``` bash
git clone <URL_DO_REPOSITORIO>
cd urbanize
```

Crie e ative um ambiente virtual no Windows:

``` powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Instale as dependências:

``` powershell
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz do projeto, com as variáveis exigidas por
`config/settings.py`:

``` dotenv
SECRET_KEY=<sua-chave-secreta>
DB_NAME=urbanize
DB_USER=<usuario-do-postgresql>
DB_PASSWORD=<senha-do-postgresql>
DB_HOST=localhost
DB_PORT=5432
```

Use valores próprios do seu ambiente. Não compartilhe o `.env` e não o
versione no Git.

Aplique as migrations e inicie o servidor:

``` powershell
python manage.py migrate
python manage.py runserver
```

A API ficará disponível em `http://127.0.0.1:8000/`, considerando a
configuração local padrão.

### Executar com Docker Compose

Na configuração atual de desenvolvimento, o Django roda em um container
e o PostgreSQL continua instalado no Windows. Por isso, o `DB_HOST` do
`.env` deve ser:

``` dotenv
DB_HOST=host.docker.internal
```

Com o Docker Desktop em execução, inicie o serviço na raiz do projeto:

``` powershell
docker compose up --build
```

Para parar o serviço, use `Ctrl+C`. Para executá-lo em segundo plano:

``` powershell
docker compose up --build -d
```

Para acompanhar os logs:

``` powershell
docker compose logs -f web
```

Para parar os serviços:

``` powershell
docker compose down
```

O arquivo `.env` é fornecido ao container em tempo de execução pelo
Compose e não deve ser copiado para a imagem nem enviado ao repositório.
A configuração atual usa o servidor de desenvolvimento do Django; ela
não é uma configuração de produção.

### Testes

Execute os testes automatizados com:

``` powershell
python manage.py test
```

Os testes devem ser executados em um ambiente configurado para testes.
Antes de executar comandos que alterem o banco, confirme qual banco está
selecionado.

### Endpoints principais

| Método  | Endpoint                        | Descrição                                                   |
|:--------|:--------------------------------|:------------------------------------------------------------|
| `GET`   | `/requests/`                    | Lista solicitações permitidas ao usuário autenticado.       |
| `POST`  | `/requests/`                    | Cria uma solicitação.                                       |
| `GET`   | `/requests/{id}/`               | Consulta uma solicitação.                                   |
| `PATCH` | `/requests/{id}/`               | Atualiza uma solicitação, conforme permissões e validações. |
| `PATCH` | `/requests/{id}/change-status/` | Solicita uma mudança de status.                             |
| `GET`   | `/requests/{id}/history/`       | Consulta o histórico da solicitação.                        |

As rotas de autenticação e documentação dependem da configuração em
`config/urls.py`.

### Filtros, busca e ordenação

A listagem de solicitações oferece parâmetros de filtro, busca e
ordenação conforme a configuração da API. Exemplos:

``` http
GET /requests/?status=RESOLVED
GET /requests/?search=buraco
GET /requests/?ordering=created_at
GET /requests/?ordering=-created_at
```

A disponibilidade exata de cada campo depende dos filtros e das views
configurados no projeto.

------------------------------------------------------------------------

O Urbanize é um projeto em evolução. O objetivo é desenvolver uma API
com regras de negócio explícitas, controle de acesso, histórico
confiável e uma base que possa evoluir sem perder clareza arquitetural.
