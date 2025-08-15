import langextract as lx
from typing import Iterator, Iterable, cast
import textwrap

# 1. Define the prompt and extraction rules
prompt = textwrap.dedent("""\
    请从文本中提取人物的姓名和事件的关键信息。
请确保提取的文本是原文中的准确片段""")

# 2. Provide a high-quality example to guide the model
examples = [
    lx.data.ExampleData(
        text="市政协党组副书记、副主席肖贵玉，党组成员、副主席金兴明作交流发言，党组成员、副主席吴信宝，副主席寿子琪、钱锋出席，党组成员、秘书长周亚传达有关精神。",
        extractions=[
            lx.data.Extraction(
                extraction_class="人物",
                extraction_text="肖贵玉",
                attributes={"职务": "市政协党组副书记、副主席"}
            ),
            lx.data.Extraction(
                extraction_class="事件",
                extraction_text="作交流发言",
                attributes={"相关人员": ["肖贵玉", "金兴明"]}
            ),
        ]
    ),
]


# The input text to be processed
input_text = """
3月27日，市政协党组举行理论学习中心组（扩大）学习会，围绕习近平总书记关于加强党的作风建设的重要论述、《中共中央政治局贯彻落实中央八项规定实施细则》精神开展专题学习交流。市政协党组书记、主席胡文容主持并讲话。
会上，市委党校党的建设教研部副主任赵大朋围绕“深入学习习近平总书记关于加强党的作风建设的重要论述”作专题辅导。他紧扣主题、结合实际，从加强党的作风建设的重要意义和价值、正确全面认识党的作风建设问题、新时代加强党的作风建设的主要内容、对于加强新时代党的作风建设的系统性思考等方面作了系统讲解。
胡文容指出，习近平总书记关于加强党的作风建设的重要论述，深化了党的作风建设的规律性认识，赋予了党的作风建设新的时代内涵，为我们开展学习教育提供了根本遵循。要着力在学深悟透上下功夫，全面对标对表中央和市委部署要求，强化学习引领，加固贯彻落实中央八项规定精神的堤坝，忠诚拥护“两个确立”，坚决做到“两个维护”。要着力在查摆问题上见真章，紧密联系政协工作实际，全面对照中央《通知》要求和《中共中央政治局贯彻落实中央八项规定实施细则》精神，深化同查同治，形成问题清单，深挖问题根源，为整改落实提供精准靶向。要着力在集中整治上求实效，把学查改有机贯通起来，将整改成果转化为制度成果，不断完善作风建设长效机制，同时锤炼坚强党性，树起担当作为导向，营造风清气正环境，更好激励党员、干部大胆干事，以优良作风推动政协工作高质量发展。
市政协党组副书记、副主席肖贵玉，党组成员、副主席金兴明作交流发言，党组成员、副主席吴信宝，副主席寿子琪、钱锋出席，党组成员、秘书长周亚传达有关精神。市政协机关党组成员，副秘书长，各专委会分党组书记、副书记，市纪委监委驻市政协机关纪检监察组成员，机关和事业单位干部参加学习。
"""

# Run the extraction

result = lx.extract(
    text_or_documents=input_text,
    prompt_description=prompt,
    examples=examples,
    language_model_type=lx.inference.OpenAILanguageModel,
    model_id="Qwen3",
    language_model_params={
        "base_url": "http://10.31.31.42:8000/v1"
    },
    format_type=lx.data.FormatType.JSON,
    temperature=0.0,
    max_char_buffer=10000,
    fence_output=False,
    use_schema_constraints=False,
    api_key="123"
)


# Save the results to a JSONL file
if isinstance(result, lx.data.AnnotatedDocument):
    annotated_documents: Iterator[lx.data.AnnotatedDocument] = iter([result])
else:
    annotated_documents = iter(cast(Iterable[lx.data.AnnotatedDocument], result))

lx.io.save_annotated_documents(annotated_documents, output_name="extraction_results.jsonl", output_dir=".")

# Generate the visualization from the file
html_content = lx.visualize("extraction_results.jsonl")
with open("visualization.html", "w") as f:
    f.write(html_content)