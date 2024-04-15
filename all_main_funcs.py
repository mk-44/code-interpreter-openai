import os
from openai import OpenAI
import ast
import json
import os
from dotenv import load_dotenv

GPT_MODEL = "gpt-3.5-turbo-0613"

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
client = OpenAI()

memory = list()

def get_dataframe_schema(df):
    dataframe_schema_string = '\n'.join(
        [
            str({'columns' : df.columns,
            'shape' : df.shape,
            'dataframe_info' : df.info(),
            'dataframe_description' : df.describe()})
        ]
    )
    return dataframe_schema_string

def get_tools(df):
    dataframe_schema_string = get_dataframe_schema(df)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "ask_dataframe",
                "description": "Use this function to answer user questions about the given dataframe/dataset. Input should be a fully formed python code that could produce results such that the code should return a string. If the input column name does not match the dataframe/dataset column name, pick the nearest possible column and use that to give answer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": f"""
                                    Python code extracting info from dataframe to answer the user's question.
                                    Python should be written using this dataframe schema:
                                    {dataframe_schema_string}
                                    The query should be returned in plain text, not in JSON.
                                    """,
                        }
                    },
                    "required": ["query"],
                },
            }
        }
    ]
    return tools


def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_MODEL):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature = 0.0
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e


def run(code: str, df):
    tree = ast.parse(code)
    last_node = tree.body[-1] if tree.body else None
    if isinstance(last_node, ast.Expr):
        tgts = [ast.Name(id="_result", ctx=ast.Store())]
        assign = ast.Assign(targets=tgts, value=last_node.value)
        tree.body[-1] = ast.fix_missing_locations(assign)
    ns = {'df' : df}
    exec(compile(tree, filename="<ast>", mode="exec"), ns)
    return ns.get("_result", None)


def ask_dataframe(query, df):
    try:
        results = str(run(query, df))
    except Exception as e:
        results = f"query failed with error: {e}"
    return results


def execute_function_call(message):
    if message.tool_calls[0].function.name == "ask_dataframe":
        query = json.loads(message.tool_calls[0].function.arguments)["query"]
        results = ask_dataframe(query)
    else:
        results = f"Error: function {message.tool_calls[0].function.name} does not exist"
    return results


def get_output(question, df):
    dataframe_schema_string = get_dataframe_schema(df)

    messages = []
 
    print(f'memory: {memory}')
    
    messages.append({"role": "system", "content": f"Answer user questions by generating python script against the dataframe/dataset where dataframe details are : {dataframe_schema_string}. These are the previous conversations that have already happened : {memory[-5:]}"})
    messages.append({"role": "user", "content": question})
    tools = get_tools(df)

    print('chat completion request : ')
    chat_response = chat_completion_request(messages, tools)
    print(chat_response)

    try:
        code = json.loads(chat_response.choices[0].message.tool_calls[0].function.arguments)['query']
        response_content = run(code, df)
        memory.append({'question' : question, 'response' : response_content})
        print('Response found from dataframe')
        return response_content
    except:
        response = client.chat.completions.create(model = GPT_MODEL, messages = messages)
        response_content = response.choices[0].message.content
        memory.append({'question' : question, 'response' : response_content})
        print('Response not found from dataframe')
        return response_content