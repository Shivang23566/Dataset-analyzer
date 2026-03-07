import pandas as pd
import json
from backend.app.services.eda_engine import analyze_dataset


print("Running EDA test...")
# Load a sample CSV file
df = pd.read_csv("backend/sample.csv")

# Run EDA
result = analyze_dataset(df)

# Print nicely formatted output
print(json.dumps(result, indent=2))
