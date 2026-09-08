"""Print exact frozen instruction strings; task-dependent text remains in archives."""
import json
from pathlib import Path
from . import codex_subscription as c
from .heldout200.inot import INOT_DESCRIPTION

ROOT=Path(__file__).resolve().parents[1]


def escape(text):
    replacements={'\\':r'\textbackslash{}','{':r'\{','}':r'\}','_':r'\_',
                  '&':r'\&','%':r'\%','#':r'\#','$':r'\$','<':r'\textless{}','>':r'\textgreater{}'}
    return ''.join(replacements.get(char,char) for char in text)


def quote(text):
    return '\\begin{quote}\\small\n'+escape(text)+'\n\\end{quote}\n'


def render():
    data={'common_instruction':c.BASE,'operation_sentences':list(c.STEPS),
          'neutral_labels':['stage 1','stage 2','stage 3'],
          'role_labels':['planner','implementer','reviewer'],
          'direct_instruction':'Implement the requested program.',
          'final_output_contract':c.FINAL,'inot_independent_instruction':INOT_DESCRIPTION,
          'source_sha256_lf':c.source_hash(),
          'scope':'Exact experimental English strings; print wrapping is not an input transformation'}
    (ROOT/'reproducibility/revision/frozen_prompt_material.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for lang in ('en','ru'):
        en=lang=='en'
        out=('The following English strings are used in both language editions because they are the executed experimental instructions. Typographic wrapping is for the page only; exact UTF-8 prompts and forwarded responses are retained in the archive.\n' if en else
             'Ниже приведены английские строки, фактически использованные в эксперименте; они одинаковы в обеих языковых версиях. Переносы для вёрстки относятся только к странице; точные UTF-8-промпты и переданные ответы сохранены в архиве.\n')
        out='\\begingroup\\small\n'+out
        out+='\\paragraph*{'+('Common instruction.' if en else 'Общая инструкция.')+'}\n'+quote(c.BASE)
        out+='\\paragraph*{'+('Factorial operations.' if en else 'Операции факторных условий.')+'}\n'
        out+=('In order, the three exact operation sentences are:\n' if en else 'Три точных предложения с операциями следуют в таком порядке:\n')
        out+='\\begin{quote}\n'+'\\par\n'.join(escape(step) for step in c.STEPS)+'\n\\end{quote}\n'
        out+=('Each sentence is prefixed by its neutral label (stage 1/2/3) or role label (planner/implementer/reviewer), followed by a colon and a space. Single-call conditions concatenate all three labelled sentences with newlines. Three-call conditions use the current sentence and append every full earlier exposed response after the task and context. The direct condition uses the following sentence alone before the common final contract:\n' if en else
              'Каждому предложению предшествует нейтральное обозначение (stage 1/2/3) либо роль (planner/implementer/reviewer), затем двоеточие и пробел. Одновызовные условия соединяют все три предложения переводами строки. Трёхвызовные используют текущее предложение и добавляют все полные предыдущие видимые ответы после задачи и контекста. Прямое условие использует только следующее предложение перед общим требованием итогового формата:\n')
        out+=quote(data['direct_instruction'])
        out+='\\paragraph*{'+('Final-output contract.' if en else 'Требование итогового формата.')+'}\n'+quote(c.FINAL)
        out+=('The contract appears in each single-call condition and in stage 3 of each three-call condition. Task text is introduced by TASK; supplied context by FULL SUPPLIED CONTEXT. Each earlier response is introduced by PREVIOUS STAGE $i$ (COMPLETE OUTPUT), with one-based $i$. The runner enforces the byte guard before dispatch.\n' if en else
              'Требование добавляется во всех одновызовных условиях и на третьем этапе трёхвызовных. Текст задачи предваряется TASK, предоставленный контекст --- FULL SUPPLIED CONTEXT. Каждый предыдущий ответ предваряется PREVIOUS STAGE $i$ (COMPLETE OUTPUT), где $i$ нумеруется с единицы. Исполнитель проверяет байтовый предел до отправки.\n')
        out+='\\clearpage\\subsection{'+('Independent INoT instruction' if en else 'Независимая инструкция INoT')+'}\n'+quote(INOT_DESCRIPTION)
        out+=('For INoT*, this instruction precedes the full task and context; the same final-output contract follows them. The common execution instruction is also retained. This is model-read conceptual guidance, not executable host code.\n' if en else
              'Для INoT* эта инструкция предшествует полной задаче и контексту; после них добавляется то же требование итогового формата. Общая инструкция исполнения также сохраняется. Это концептуальное руководство для модели, а не код, исполняемый на хосте.\n')
        out+='\\endgroup\n'
        (ROOT/f'sections/exact_prompts_{lang}.tex').write_text(out,encoding='utf-8')


if __name__=='__main__':render()
