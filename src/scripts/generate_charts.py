import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style for academic publication
plt.style.use('seaborn-v0_8-paper')
sns.set_context("paper", font_scale=1.5)
sns.set_style("whitegrid")

OUTPUT_DIR = "experiments/plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def plot_comparison():
    """
    Chart 1: Baseline vs Agentic (Latency & Citations)
    Uses Dual-Axis bar chart.
    """
    try:
        df = pd.read_csv("experiments/comparison_results.csv")
        
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Bar 1: Latency
        color = 'tab:blue'
        ax1.set_xlabel('Model Architecture')
        ax1.set_ylabel('Latency (seconds)', color=color, fontweight='bold')
        bars1 = ax1.bar(df['Model'], df['Latency (s)'], color=color, alpha=0.6, width=0.4, label='Latency')
        ax1.tick_params(axis='y', labelcolor=color)

        # Axis 2: Citations
        ax2 = ax1.twinx() 
        color = 'tab:green'
        ax2.set_ylabel('Verified Citations (Count)', color=color, fontweight='bold')
        bars2 = ax2.plot(df['Model'], df['Citations (Grounding)'], color=color, marker='o', linewidth=3, markersize=12, label='Citations')
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.set_ylim(0, 20)

        plt.title('Trade-off: Latency vs. Information Grounding', fontweight='bold', pad=20)
        fig.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/comparison_chart.png", dpi=300)
        print("✅ Generated comparison_chart.png")
    except Exception as e:
        print(f"❌ Error plotting comparison: {e}")

def plot_ablation():
    """
    Chart 2: Critics Impact on Analytical Depth (Output Length)
    """
    try:
        df = pd.read_csv("experiments/ablation_results.csv")
        
        plt.figure(figsize=(8, 6))
        # Rename for clarity
        df['Config'] = df['Run Label'].apply(lambda x: 'RAG Only' if 'Run A' in x else 'Agentic + Critic')
        
        ax = sns.barplot(x='Config', y='Output Length', data=df, palette="magma")
        
        # Add percentage annotation
        rag_len = df[df['Run Label'].str.contains("Run A")]['Output Length'].values[0]
        agent_len = df[df['Run Label'].str.contains("Run B")]['Output Length'].values[0]
        increase = ((agent_len - rag_len) / rag_len) * 100
        
        # Add annotation arrow
        plt.annotate(f'+{increase:.1f}% Depth', 
                     xy=(0.5, (rag_len + agent_len)/2), 
                     xytext=(0.5, agent_len + 500),
                     arrowprops=dict(facecolor='black', shrink=0.05),
                     ha='center', fontsize=12, fontweight='bold')

        plt.ylabel("Analytical Output (Characters)", fontweight='bold')
        plt.xlabel("System Configuration", fontweight='bold')
        plt.title('Ablation Study: Impact of Adversarial Critic', fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/ablation_chart.png", dpi=300)
        print("✅ Generated ablation_chart.png")
    except Exception as e:
        print(f"❌ Error plotting ablation: {e}")

def plot_pilot_summary():
    """
    Chart 3: Pilot Study Success Rates (N=10)
    """
    try:
        df = pd.read_csv("experiments/results.csv")
        
        # Calculate stats
        total = len(df)
        success = len(df[df['status'] == 'Success'])
        failed = total - success
        
        labels = ['Successful Diagnosis', 'Edge Case Failures']
        sizes = [success, failed]
        colors = ['#4CAF50', '#FF5722'] # Green, Orange
        
        plt.figure(figsize=(7, 7))
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140, pctdistance=0.85, textprops={'fontsize': 12, 'weight': 'bold'})
        
        # Draw circle
        centre_circle = plt.Circle((0,0),0.70,fc='white')
        fig = plt.gcf()
        fig.gca().add_artist(centre_circle)
        
        plt.title(f'Pilot Study Robustness (N={total})', fontweight='bold')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/pilot_study_chart.png", dpi=300)
        print("✅ Generated pilot_study_chart.png")
    except Exception as e:
        print(f"❌ Error plotting pilot: {e}")

if __name__ == "__main__":
    print("📊 Generating Research Plots...")
    plot_comparison()
    plot_ablation()
    plot_pilot_summary()
