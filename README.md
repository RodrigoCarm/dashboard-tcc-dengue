# Dashboard Dengue - Ji-Parana

Projeto de analise dos casos de dengue em Ji-Parana, usando dados semanais do InfoDengue/Alerta Dengue.

A aplicacao foi estruturada em duas partes:

- **FastAPI**: responsavel por carregar, tratar, filtrar e disponibilizar os dados via endpoints.
- **Streamlit**: responsavel apenas por consumir a API e apresentar o dashboard.

## Tecnologias

- Python
- FastAPI
- Streamlit
- Pandas
- Plotly
- Cachetools
- Uvicorn

## Estrutura do projeto

```text
.
+-- api.py
+-- base.py
+-- data_service.py
+-- main.py
+-- requirements.txt
+-- teste.py
+-- cache_system/
|   +-- cache.py
+-- volume/
    +-- dengue_2025.csv
```

## Principais arquivos

- `api.py`: define os endpoints da API FastAPI.
- `data_service.py`: centraliza leitura, cache, tratamento, filtros e organizacao dos dados.
- `main.py`: aplicacao Streamlit que consome a API e monta o dashboard.
- `base.py`: carrega os arquivos `.csv` da pasta `volume`.
- `cache_system/cache.py`: cache em memoria usado pela API.
- `volume/dengue_2025.csv`: base de dados usada no projeto.

## Instalação

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Se o ambiente virtual ja existir, basta ativar e instalar/atualizar as dependencias:

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

## Como executar

Primeiro, suba a API:

```powershell
venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

A API ficara disponivel em:

```text
http://127.0.0.1:8000
```

A documentacao interativa da API fica em:

```text
http://127.0.0.1:8000/docs
```

Em outro terminal, suba o Streamlit:

```powershell
venv\Scripts\python.exe -m streamlit run main.py
```

O dashboard ficara disponivel em:

```text
http://localhost:8501
```

## Configuracao da URL da API

Por padrao, o Streamlit consome a API em:

```text
http://127.0.0.1:8000
```

Se precisar usar outra URL, defina a variavel de ambiente `DENGUE_API_URL` antes de iniciar o Streamlit:

```powershell
$env:DENGUE_API_URL="http://127.0.0.1:8000"
venv\Scripts\python.exe -m streamlit run main.py
```

## Fluxo dos dados

1. A API le os arquivos `.csv` da pasta `volume`.
2. Os dados brutos sao armazenados em cache em memoria.
3. A API trata as colunas, converte datas e numeros, cria campos auxiliares e guarda o resultado em cache.
4. O Streamlit envia os filtros selecionados para o endpoint `POST /filtros`.
5. Os demais endpoints retornam os dados ja filtrados.
6. O Streamlit monta os indicadores, graficos e tabela com os dados recebidos da API.

## Filtros

O endpoint `POST /filtros` registra os filtros ativos em memoria no servidor FastAPI.

Exemplo de payload:

```json
{
  "data_ini": "2024-12-29",
  "data_fim": "2025-12-28",
  "niveis_alerta": ["1 - Verde", "4 - Vermelho"],
  "somente_rt_maior_1": false
}
```

Depois que os filtros sao registrados, os endpoints de dados, graficos, indicadores, destaques e tabela passam a responder conforme esses parametros.

## Endpoints principais

| Metodo | Endpoint | Descricao |
|---|---|---|
| `GET` | `/` | Verifica se a API esta online. |
| `GET` | `/metadados` | Retorna periodo disponivel, niveis de alerta e municipio. |
| `POST` | `/filtros` | Registra os filtros ativos em memoria. |
| `GET` | `/dados/original` | Retorna a base tratada completa. |
| `GET` | `/dados/filtrados` | Retorna a base tratada conforme os filtros ativos. |
| `GET` | `/indicadores` | Retorna os indicadores principais. |
| `GET` | `/destaques` | Retorna os principais achados textuais. |
| `GET` | `/tabela` | Retorna os dados da tabela analitica. |

## Endpoints dos graficos

| Metodo | Endpoint | Descricao |
|---|---|---|
| `GET` | `/graficos/casos-incidencia` | Dados de casos semanais e incidencia por 100 mil. |
| `GET` | `/graficos/casos-mes` | Casos acumulados por mes. |
| `GET` | `/graficos/nivel-alerta` | Nivel de alerta por semana. |
| `GET` | `/graficos/rt` | Rt por semana. |
| `GET` | `/graficos/probabilidade-rt` | Probabilidade de Rt maior que 1. |
| `GET` | `/graficos/temperatura` | Temperatura minima, media e maxima por semana. |
| `GET` | `/graficos/umidade` | Umidade minima, media e maxima por semana. |
| `GET` | `/graficos/clima-rt` | Dados combinados de casos, temperatura media, umidade media e Rt. |

## Validacao rapida

Para verificar se os arquivos Python estao compilando:

```powershell
venv\Scripts\python.exe -m py_compile main.py api.py data_service.py base.py cache_system\cache.py teste.py
```

Para verificar conflitos de dependencias:

```powershell
venv\Scripts\python.exe -m pip check
```

## Observacoes

- Os filtros ficam registrados em memoria no processo da API. Se o servidor FastAPI for reiniciado, os filtros voltam para o padrao.
- O cache tambem fica em memoria. Ao reiniciar a API, os dados serao carregados novamente a partir da pasta `volume`.
- O Streamlit depende da API estar em execucao para carregar o dashboard.
