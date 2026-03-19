import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Create research dir if it doesn't exist
os.makedirs('research', exist_ok=True)

# Load data
with open('backend/comparison_results.json') as f:
    data = json.load(f)

summary = data['summary']
breakdown = data['breakdown']
raw_results = data['raw_results']

sns.set_theme(style="whitegrid")

# 1. Overall Accuracy Plot
metrics = ['Overall Accuracy', 'Scam Catch Rate']
g_vals = [summary['guardian_overall_accuracy'], summary['guardian_catch_rate']]
i_vals = [summary['industry_overall_accuracy'], summary['industry_catch_rate']]

x = np.arange(len(metrics))
width = 0.35
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - width/2, g_vals, width, label='AI Guardian v3.0.0', color='#3b82f6')
ax.bar(x + width/2, i_vals, width, label='Industry Baseline', color='#ef4444')
ax.set_ylabel('Score (0-1)')
ax.set_title('Overall Performance Delta')
ax.set_xticks(x)
ax.set_xticklabels(metrics)
ax.legend()
plt.tight_layout()
plt.savefig('research/overall_performance.png')
plt.close()

# 2. Category Accuracy Plot
categories = [cat for cat in breakdown.keys() if cat != 'safe']
g_cat = [breakdown[cat]['guardian'] for cat in categories]
i_cat = [breakdown[cat]['industry'] for cat in categories]

df_cat = pd.DataFrame({
    'Category': categories * 2,
    'Accuracy': g_cat + i_cat,
    'Provider': ['AI Guardian'] * len(categories) + ['Industry Baseline'] * len(categories)
})

plt.figure(figsize=(12, 6))
sns.barplot(data=df_cat, x='Category', y='Accuracy', hue='Provider', palette=['#3b82f6', '#ef4444'])
plt.title('Detection Accuracy by Scam Category')
plt.ylim(0, 1.0)
plt.tight_layout()
plt.savefig('research/category_accuracy.png')
plt.close()

# 3. Latency Distribution
latencies = [r['guardian']['latency_ms'] for r in raw_results if 'guardian' in r]
plt.figure(figsize=(10, 6))
plt.hist(latencies, bins=15, color='#10b981', alpha=0.7)
plt.axvline(np.mean(latencies), color='#ef4444', linestyle='dashed', linewidth=2, label=f"Avg: {np.mean(latencies):.0f}ms")
plt.title('Pipeline Latency Distribution (Deep Reasoning Path)')
plt.xlabel('Latency (ms)')
plt.ylabel('Scenario Count')
plt.legend()
plt.tight_layout()
plt.savefig('research/latency_distribution.png')
plt.close()

print("Graphs generated successfully in research/ directory.")
