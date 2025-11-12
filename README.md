# 🌦️ Análise de Dados Meteorológicos com Python e Power BI
### Projeto de consolidação e limpeza de dados do INMET

Este projeto tem como objetivo automatizar a **leitura, integração e preparação de dados meteorológicos** fornecidos pelo **INMET (Instituto Nacional de Meteorologia)**.  
Ele reúne centenas de arquivos CSV em um único dataset padronizado, facilitando análises em ferramentas como **Power BI**, **Excel** ou **Python**.

---

## Objetivo

Consolidar e preparar dados climáticos de diferentes estações do Brasil, permitindo análises sobre **temperatura, umidade, precipitação, pressão e radiação solar** de forma centralizada e limpa.

---

## Estrutura do Projeto

```
📁 meteorologia/
├── concatena_dados.py        # Extrai e une os arquivos CSV brutos
├── limpeza_dados.py          # (Em desenvolvimento) Limpa e padroniza os dados
├── dados_estacoes.csv        # Saída gerada após a concatenação
└── dados_estacoes_limpos.csv # Saída final após limpeza (em breve)
```

---

## Etapas do Processo

### 1. Coleta e Concatenação (`concatena_dados.py`)
- Lê automaticamente todos os arquivos `.CSV` em um diretório.  
- Usa **expressões regulares (regex)** para extrair metadados (região, estado, estação e cidade) do nome de cada arquivo.  
- Remove colunas vazias e insere colunas descritivas.  
- Concatena os DataFrames em um único arquivo (`dados_estacoes.csv`).

---

### 2. Limpeza e Padronização (`limpeza_dados.py`)

Esta etapa (em desenvolvimento) fará a **limpeza e transformação** do dataset gerado, preparando-o para análise em ferramentas de Business Intelligence.

Objetivos:
- Padronizar nomes de colunas (sem espaços, acentos e caracteres especiais);  
- Converter formatos numéricos (ex.: “12,3” → 12.3);  
- Corrigir tipos de dados e tratar valores ausentes;  
- Gerar uma saída final: `dados_estacoes_limpos.csv`.

---

## Sobre o Dataset do INMET

Os dados foram obtidos do **Instituto Nacional de Meteorologia (INMET)** e representam medições realizadas em diversas estações meteorológicas do Brasil.

Cada arquivo contém registros horários com variáveis como:

| Variável | Descrição |
|-----------|------------|
| `Data` | Data da observação |
| `Hora (UTC)` | Horário da coleta |
| `PRECIPITAÇÃO TOTAL (mm)` | Quantidade de chuva registrada |
| `PRESSÃO ATMOSFERICA (hPa)` | Pressão atmosférica ao nível da estação |
| `RADIACAO GLOBAL (KJ/m²)` | Energia solar recebida |
| `TEMPERATURA DO AR (°C)` | Temperatura instantânea do ar |
| `TEMPERATURA MÁXIMA (°C)` | Temperatura máxima diária |
| `TEMPERATURA MÍNIMA (°C)` | Temperatura mínima diária |
| `UMIDADE RELATIVA (%)` | Umidade relativa do ar |
| `VENTO (m/s)` | Velocidade do vento |

Essas variáveis permitem análises sobre:
- Variação de temperatura e umidade ao longo do tempo;  
- Comparações regionais entre estados e estações;  
- Identificação de padrões de chuva e períodos de seca;  
- Estudos de comportamento climático local.

---

## Tecnologias e Bibliotecas utilizadas

- **Python 3**
- **Pandas** → manipulação e concatenação de dados 
- **Regex (re)** → extração de informações dos nomes dos arquivos  
- **OS** → automação da leitura de diretórios

---

## Habilidades Demonstradas

- Manipulação e limpeza de dados com **Pandas**  
- Uso de **expressões regulares** para automação  
- Construção de pipeline de dados (extração → transformação → exportação)  
- Preparação de datasets para **análise em Power BI**

---

## Próximos Passos

- Implementar as etapas de limpeza e transformação em `limpeza_dados.py`  
- Criar gráficos e relatórios analíticos no Power BI  
- Explorar padrões climáticos regionais com análises estatísticas

---

## Fluxo ETL Simplificado

```
[Arquivos CSV brutos]
        ↓
 concatena_dados.py  →  dados_estacoes.csv
        ↓
 limpeza_dados.py    →  dados_estacoes_limpos.csv
        ↓
   Power BI / Análises
```

---

## Contato

**Lucas Môra**  
[LinkedIn](https://www.linkedin.com/in/lucas-mora-) • [GitHub](https://github.com/lucasmora)
