from pathlib import Path
import re,json
base=Path(__file__).resolve().parents[1]
s=(base/'source-snapshot/converted_article_springer.tex').read_text(encoding='utf-8')
body=s[s.index('\\section{Introduction}'):s.index('\\backmatter')]
original_identity='The research harness is published in the INoT\\_Research repository~\\cite{inotresearch2026}; every result below is tied to commit \\texttt{010211ee5775185e8330ab6cde06e912c2adcb9e}.'
anonymous_identity='The research harness and the immutable experimental snapshot are supplied in the anonymous replication package~\\cite{inotresearch2026}; every result below is tied to that frozen snapshot.'
assert original_identity in body
body=body.replace(original_identity,anonymous_identity).replace('\\botrule','\\bottomrule')
body=body.replace('\\footnotesize\n','').replace('\\renewcommand{\\arraystretch}{1.18}\n','')
# Wrap long hypotheses as ordinary text instead of an unbreakable description label.
body=re.sub(r'\\item\[(\\textbf\{H[123]\}[^\n]*?)\]',lambda m:r'\item[]'+m[1]+r'\quad',body)
# Standard URL/path breaking avoids overflow without changing font sizes or content.
body=re.sub(r'\\texttt\{([^{}]*[/\\_][^{}]*)\}',lambda m:r'\path{'+m[1].replace(r'\_','_')+'}',body)
# Upright code labels use an available shape of the ACM default monospaced font.
body=re.sub(r'\\texttt\{([^{}]*)\}',lambda m:r'\textnormal{\texttt{'+m[1]+'}}',body)
body=body.replace(r'$(w_{\mathrm{cc}},w_{\mathrm{dup}},w_{\mathrm{warn}},w_{\mathrm{doc}})\pm 20\%$',r'$(w_{\mathrm{cc}},\allowbreak w_{\mathrm{dup}},\allowbreak w_{\mathrm{warn}},\allowbreak w_{\mathrm{doc}})\pm 20\%$')

descriptions={
'e3_humaneval_replication_en.png':'Mean total tokens per task for B2 Classical-MAS and B3 Hybrid-INoT across context lengths, shown separately for the Pro pilot and Flash-Lite replication.',
'e6_model_cost_ratio_en.png':'Flash-Lite cost as a percentage of Pro cost across context lengths, shown separately for B2 Classical-MAS and B3 Hybrid-INoT.',
'e5_inference_cost_sensitivity_en.png':'Projected API-inference savings under common token-price multipliers, with a bootstrap interval.'}
for filename,description in descriptions.items():
    pattern=r'(\\includegraphics\[[^\]]+\]\{figures/generated/'+re.escape(filename)+r'\})'
    body,count=re.subn(pattern,lambda m:m[1]+'\n\\Description{'+description+'}',body)
    assert count==1
(base/'paper/body.tex').write_text(body,encoding='utf-8')
abstract=re.search(r'^\\abstract\{(.*)\}$',s,re.M).group(1)
keywords=re.search(r'^\\keywords\{(.*)\}$',s,re.M).group(1)
title=re.search(r'^\\title(?:\[[^\]]*\])?\{(.*)\}$',s,re.M).group(1)
main=r"""\documentclass[acmsmall,screen,review,anonymous]{acmart}
\usepackage{amsmath}
\usepackage{algorithm}
\usepackage{algorithmicx}
\usepackage{algpseudocode}
\usepackage{tabularx}
\newcommand{\E}{\mathbb{E}}
\newcommand{\I}{\mathbb{I}}
\newtheorem{proposition}{Proposition}
\newtheorem{definition}{Definition}
\newtheorem{assumption}{Assumption}
\makeatletter
\providecommand*{\toclevel@algorithm}{1}
\providecommand*{\theHalgorithm}{\thealgorithm}
\makeatother
\citestyle{acmnumeric}
% Retain the default ACM permission and reference-format blocks.
% Publication identifiers are unassigned at initial review.
\acmConference[FSE 2027]{ACM International Conference on the Foundations of Software Engineering}{12-16 July 2027}{Shenzhen, China}
\acmBooktitle{ACM International Conference on the Foundations of Software Engineering (FSE 2027), 12-16 July 2027, Shenzhen, China}
\acmYear{2027}
\copyrightyear{2027}
\acmDOI{}
\acmISBN{}
\begin{document}
\title[Hybrid-INoT]{TITLE}
\begin{abstract}
ABSTRACT
\end{abstract}
\ccsdesc[500]{Software and its engineering~Automatic programming}
\ccsdesc[300]{Computing methodologies~Multi-agent systems}
\keywords{KEYWORDS}
\maketitle
\input{body}
\section*{Data Availability}
An anonymous replication package, \texttt{hybrid-inot-july-2026-anonymous.zip}, accompanies this manuscript. It contains the frozen research harness, configurations, recorded metrics and usage, and scripts and source data for the reported tables and figures. The records do not include complete generated solution text; this limits answer-level auditing. The package supports inspection and offline analysis of retained results; rerunning hosted models may require an API account and may be affected by model drift. The replication materials will be made publicly available upon acceptance.
\nocite{austin2021mbpp,goncalves2011,ko2007,parnin2011}
\bibliographystyle{ACM-Reference-Format}
\bibliography{references}
\end{document}
"""
main=main.replace('TITLE',title).replace('ABSTRACT',abstract).replace('KEYWORDS',keywords)
(base/'paper/main.tex').write_text(main,encoding='utf-8')
(base/'validation/conversion_whitelist.json').write_text(json.dumps({'scientific_text_shortened':False,'allowed_changes':['Springer-to-ACM wrapper','botrule to bottomrule','removal of inherited table font/spacing overrides','anonymous repository and commit locator','figure accessibility descriptions','ACM bibliography formatting','CCS descriptors and Data Availability']},indent=2)+'\n',encoding='utf-8')
print('Full scientific body written without shortening')
