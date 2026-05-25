from pathlib import Path

path = Path(r"d:\BMS COLL\PROJECT\MS-AI\imag\final_report.tex")
text = path.read_text(encoding="utf-8")
marker = "Figure~\\ref{fig:system_architecture} shows the high-level system architecture of MandiSense AI."
idx = text.index(marker)
start = text.index("\\begin{figure}[H]", idx)
end = text.index("\\end{figure}", start) + len("\\end{figure}")
new_block = r"""\begin{figure}[H]
\centering
\resizebox{0.95\textwidth}{!}{%
\begin{tikzpicture}[
    >=Stealth,
    font=\small,
    box/.style={rectangle, draw=black!70, rounded corners=5pt, align=center, text width=3.2cm, minimum height=1.0cm, fill=blue!12, inner sep=5pt},
    agent/.style={rectangle, draw=black!70, rounded corners=5pt, align=center, text width=2.8cm, minimum height=1.0cm, fill=green!18, inner sep=5pt},
    support/.style={rectangle, draw=black!70, rounded corners=5pt, align=center, text width=2.8cm, minimum height=1.0cm, fill=orange!18, inner sep=5pt},
    core/.style={rectangle, draw=black!70, rounded corners=5pt, align=center, text width=3.4cm, minimum height=1.0cm, fill=teal!15, inner sep=5pt},
    storage/.style={rectangle, draw=black!70, rounded corners=5pt, align=center, text width=2.8cm, minimum height=1.0cm, fill=gray!15, inner sep=5pt},
    gateway/.style={rectangle, draw=black!70, rounded corners=5pt, align=center, text width=3.2cm, minimum height=1.0cm, fill=violet!15, inner sep=5pt},
    terminal/.style={rectangle, draw=black!70, rounded corners=5pt, align=center, text width=3.4cm, minimum height=1.0cm, fill=purple!20, inner sep=5pt, thick},
    arrow/.style={->, thick, shorten >=2pt, shorten <=2pt},
    dasharrow/.style={<->, thick, dashed, shorten >=2pt, shorten <=2pt}
]

\node[box] (data) at (0,0) {Data Sources\\Agmarknet, Arrivals, Weather, News};
\node[box] (preprocess) at (0,-1.6) {Data Preprocessing\\Cleaning, Normalization, Feature Extraction};

\node[agent] (seasonality) at (-7,-4) {Seasonality Agent\\Cycles \\& Trends};
\node[support] (cross) at (-2.5,-4) {Cross-Commodity\\Granger \\& VAR};
\node[agent] (arrival) at (0,-4) {Arrival Agent\\Elasticity \\& Shocks};
\node[support] (volatility) at (2.5,-4) {Volatility System\\GARCH \\& HMM};
\node[agent] (external) at (7,-4) {External Agent\\News \\& Policy};

\node[core] (ensemble) at (0,-7) {Context-Adaptive Meta-Ensemble\\Dynamic Weighting};
\node[core] (cognition) at (0,-9.2) {Institutional Cognition Engine\\Deliberation, Memory, Directives};

\node[storage] (memstore) at (-5.5,-9.2) {Market Memory Store\\Evolved State Snapshots};
\node[storage] (audit) at (5.5,-9.2) {Deployment Audit Trail\\Operational Lineage};

\node[gateway] (api) at (0,-11.7) {FastAPI Unified Gateway\\Circuit Breakers, Rate Limiter};
\node[terminal] (traderos) at (0,-14.0) {TraderOS High-Density Terminal\\Viewports (T1/T2/T3), Query Console};

\draw[arrow] (data) -- (preprocess);
\draw[arrow] (preprocess) -- (seasonality);
\draw[arrow] (preprocess) -- (cross);
\draw[arrow] (preprocess) -- (arrival);
\draw[arrow] (preprocess) -- (volatility);
\draw[arrow] (preprocess) -- (external);

\draw[arrow] (seasonality) -- ++(0,-0.8) -| (ensemble.west);
\draw[arrow] (cross) -- ++(0,-0.8) -| ([xshift=-8pt]ensemble.west);
\draw[arrow] (arrival) -- (ensemble);
\draw[arrow] (volatility) -- ++(0,-0.8) -| ([xshift=8pt]ensemble.east);
\draw[arrow] (external) -- ++(0,-0.8) -| (ensemble.east);

\draw[arrow] (ensemble) -- (cognition);
\draw[dasharrow] (cognition) -- (memstore);
\draw[dasharrow] (cognition) -- (audit);
\draw[arrow] (cognition) -- (api);
\draw[arrow] (api) to [bend left=20] node[right, font=\scriptsize] {WebSocket Cognition Stream} (traderos);
\draw[arrow] (traderos) to [bend left=20] node[left, font=\scriptsize] {HTTPS Directives / Approvals} (api);

\end{tikzpicture}%
}
\caption{MandiSense AI Extended System Architecture with TraderOS Integration}
\label{fig:system_architecture}
\end{figure}"""
path.write_text(text[:start] + new_block + text[end:], encoding="utf-8")
print("Updated architecture figure block in final_report.tex")
"""
