import pandas as pd

df1 = pd.DataFrame({
    'Subsidiary': ['SECL', 'SECL', 'SECL'],
    'Mine': ['Gevra OCP', 'Kusmunda OCP', 'Dipka OCP'],
    'Coal Production': [52.5, 45.0, 38.2],
    'Overburden Removal': [85.0, 72.4, 60.1],
    'Reporting Period': ['FY 2023-24', 'FY 2023-24', 'FY 2023-24']
})

df2 = pd.DataFrame({
    'Subsidiary': ['SECL', 'SECL'],
    'Metric': ['Coal Dispatch', 'Washery Capacity'],
    'Value': [142.5, 12.0],
    'Reporting Period': ['FY 2023-24', 'FY 2023-24']
})

with pd.ExcelWriter('sample_docs/secl_quarterly_production.xlsx', engine='openpyxl') as writer:
    df1.to_excel(writer, sheet_name='Mine_Production', index=False)
    df2.to_excel(writer, sheet_name='Dispatch_Washery', index=False)

print('Excel generated successfully!')
