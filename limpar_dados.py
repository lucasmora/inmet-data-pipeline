import pandas as pd

df = pd.read_csv('dados_estacoes.csv', index_col=0)

print(df.head())