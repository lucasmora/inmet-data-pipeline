import pandas as pd

df = pd.read_csv('dados_estacoes.csv', index_col=0)

# - Juntar Data e Hora
df['data'] = pd.to_datetime(df['Data'] + ' ' + df['Hora UTC'].str.replace(' UTC', ''), format='%Y/%m/%d %H%M')
df = df.drop(['Data', 'Hora UTC'], axis=1)
df = df[['data'] + df.columns.drop('data').tolist()]

# - Padronizar nomes de colunas (sem espaços, acentos e caracteres especiais);  
columns = ['data', 'regiao', 'estado', 'estacao', 'cidade',
       'precipitacao',
       'pressao',
       'pressao_max_ant',
       'pressao_min_ant',
       'radiacao',
       'temp_ar',
       'temp_orvalho',
       'temp_max_ant',
       'temp_min_ant',
       'temp_orvalho_max_ant',
       'temp_orvalho_min_ant',
       'umidade_max_ant',
       'umidade_min_ant',
       'umidade_ar',
       'vento_dir', 'vento_rajada',
       'vento_vel']
df.columns = columns

# - Converter formatos numéricos e substituir pontuação (de “12,3” para 12.3)
# Converte a partir da sexta coluna
for coluna in df.columns[5:]:
    if df[coluna].dtype == 'object':
        df[coluna] = df[coluna].str.replace(',', '.').astype(float)
    else:
        continue

# - Gerar uma saída final: `dados_estacoes_limpos.csv`.
df.to_csv('dados_estacoes_limpo.csv')