import pandas as pd
import json
from backend.app.services.visualization_engine import generate_visualization

print("Running Visualization Test...\n")

df = pd.read_csv("backend/sample.csv")

print("Columns in dataset:", df.columns.tolist())
print("\n")

print("---- BAR CHART ----")
bar_result = generate_visualization(df, "bar", "City", "Salary")
print(json.dumps(bar_result, indent=2))


print("\n---- SCATTER ----")
scatter_result = generate_visualization(df, "scatter", "Age", "Salary")
print(json.dumps(scatter_result, indent=2))


print("\n---- PIE ----")
pie_result = generate_visualization(df, "pie", "Gender")
print(json.dumps(pie_result, indent=2))

print("\n---- HISTOGRAM ----")
hist_result = generate_visualization(df, "histogram", "Salary")
print(json.dumps(hist_result, indent=2))

print("\n---- BOXPLOT ----")
box_result = generate_visualization(df, "boxplot", "Salary", "Gender")
print(json.dumps(box_result, indent=2))
