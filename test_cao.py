import pandas as pd
df = pd.read_excel('danhsachisbn.xlsx').head(3)
df.to_excel('test_isbn.xlsx', index=False)
