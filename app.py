import chainlit as cl
import pandas as pd
from all_main_funcs import get_output


@cl.on_chat_start
async def on_chat_start():
    files = None
    while files is None:
        files = await cl.AskFileMessage(
            content="Please upload a csv file to begin!", 
            accept=["text/csv"],
            max_size_mb= 100,
            timeout = 180,
        ).send()

    file = files[0]
    df = pd.read_csv(file.path)


    cl.user_session.set('data', df)
    msg = cl.Message(content=f"Dataframe {file.name} uploaded with shape : {df.shape}")
    await msg.send()


@cl.on_message
async def main(message: cl.Message):
    # out = get_output(message.content, cl.user_session.get('data'))
    # print(out)
    try:
        out = get_output(message.content, cl.user_session.get('data'))
        await cl.Message(
            content=f"{out}",
        ).send()  
    except:
        await cl.Message(
            content=f"Please be more descriptive in the question asked regarding the dataframe",
        ).send()

