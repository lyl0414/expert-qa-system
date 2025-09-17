from zhipuai import ZhipuAI
client = ZhipuAI(api_key="") # 填写API Key

def gen_abstract(msg: str) -> str:
    response = client.chat.completions.create(
        model="glm-4-flash",  # 填写需要调用的模型编码
        messages=[
            {"role": "user", "content": """获取下面一个网页的摘要：{}""".format(msg)},
        ],
    )
    return response.choices[0].message.content
