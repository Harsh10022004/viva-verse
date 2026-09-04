import matplotlib.pyplot as plt
import os

output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "report_assets"))
os.makedirs(output_dir, exist_ok=True)

formulas = [
    ("eq_bm25.png", 
     r"$Score_{BM25}(D, Q) = \sum_{i=1}^{n} IDF(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{avgdl}\right)}$", 
     (8.5, 1.4), 14),
    
    ("eq_cosine.png", 
     r"$CosineSimilarity(\mathbf{A}, \mathbf{B}) = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|} = \frac{\sum_{i=1}^{n} A_i B_i}{\sqrt{\sum_{i=1}^{n} A_i^2} \sqrt{\sum_{i=1}^{n} B_i^2}}$", 
     (8.5, 1.4), 14),
    
    ("eq_rrf.png", 
     r"$RRF(d) = \sum_{r \in R} \frac{1}{k + rank_r(d)}$", 
     (6.0, 1.1), 15),
    
    ("eq_dp_chunking.png", 
     r"$dp[i][j] = \min_{0 \leq k < i} \left( \max(dp[k][j - 1], \mathrm{sum}[k+1 \dots i]) \right)$", 
     (7.5, 1.1), 14),
    
    ("eq_kmeans.png", 
     r"$J = \sum_{j=1}^{k} \sum_{i=1}^{n} \| x_i^{(j)} - c_j \|^2$", 
     (6.0, 1.1), 15),
    
    ("eq_knapsack.png", 
     r"$dp[i][w] = \max\left(dp[i - 1][w], \; dp[i - 1][w - w_i] + v_i\right)$", 
     (7.5, 1.1), 14)
]

for filename, latex_str, figsize, fontsize in formulas:
    fig, ax = plt.subplots(figsize=figsize, dpi=300)
    ax.axis('off')
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.text(0.5, 0.5, latex_str, fontsize=fontsize, ha='center', va='center', color='#0F172A')
    out_path = os.path.join(output_dir, filename)
    plt.savefig(out_path, bbox_inches='tight', pad_inches=0.1, facecolor='#FFFFFF')
    plt.close()
    print(f"Rendered formula: {out_path}")
