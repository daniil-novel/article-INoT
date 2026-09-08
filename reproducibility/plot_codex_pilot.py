"""Plot every assigned development candidate, with means and no inferential bars."""
from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(archive, output):
    rows=[json.loads(s) for s in (archive/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    arms=['direct','single_neutral','single_roles','multi_neutral','multi_roles']
    labels=['Direct','1 / neutral','1 / roles','3 / neutral','3 / roles']
    colors=['#324e67','#549194','#ce895c','#549194','#ce895c']
    fig,axes=plt.subplots(1,2,figsize=(8.2,3.25),layout='constrained')
    for ax,field,multiplier,title in zip(axes,['total_tokens','api_equivalent_usd'],[.001,100],['Input + output (thousand tokens)','API-equivalent value (US cents)']):
        for index,arm in enumerate(arms):
            values=[r[field]*multiplier for r in sorted(rows,key=lambda r:r['task_id']) if r['arm']==arm]
            if len(values)!=8:raise ValueError('Plot requires eight assigned candidates per arm')
            jitter=[(i-3.5)*.036 for i in range(8)]
            ax.scatter([index+j for j in jitter],values,s=19,color=colors[index],alpha=.78,zorder=3)
            mean=sum(values)/len(values)
            ax.plot([index-.30,index+.30],[mean,mean],color='#152a3a',linewidth=1.7,zorder=4)
        ax.set_xticks(range(5),labels,rotation=24,ha='right',fontsize=8)
        ax.set_ylabel(title,fontsize=9);ax.set_ylim(bottom=0)
        ax.spines[['top','right']].set_visible(False)
        ax.yaxis.grid(True,color='#e3e7ec',linewidth=.7);ax.set_axisbelow(True)
        ax.tick_params(axis='y',labelsize=8)
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output.with_suffix('.pdf'));fig.savefig(output.with_suffix('.png'),dpi=200)
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();plot(a.archive,a.output)
