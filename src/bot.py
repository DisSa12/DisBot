import os
import openai
import asyncio
import discord
from random import randrange
from src.aclient import client
from discord import app_commands
from src import log, art, personas, responses

logger = log.setup_logger(__name__)

def run_discord_bot():
    @client.event
    async def on_ready():
        await client.send_start_prompt()
        await client.tree.sync()
        loop = asyncio.get_event_loop()
        loop.create_task(client.process_messages())
        logger.info(f'{client.user} is now running!')


    @client.tree.command(name="chat", description="Have a chat with ChatGPT")
    async def chat(interaction: discord.Interaction, *, message: str):
        if client.is_replying_all == "True":
            await interaction.response.defer(ephemeral=False)
            await interaction.followup.send(
                "> **WARN: Sei già in modalità RispondiTutto. Se vuoi usare il comando Slash, passa alla modalità normale usando di nuovo `/replyall`**")
            logger.warning("\x1b[31mSei già in modalità replyAll, non puoi usare il comando slash!\x1b[0m")
            return
        if interaction.user == client.user:
            return
        username = str(interaction.user)
        client.current_channel = interaction.channel
        logger.info(
            f"\x1b[31m{username}\x1b[0m : /chat [{message}] in ({client.current_channel})")

        await client.enqueue_message(interaction, message)


    @client.tree.command(name="private", description="Attiva/disattiva l'accesso privato")
    async def private(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        if not client.isPrivate:
            client.isPrivate = not client.isPrivate
            logger.warning("\x1b[31mPassa alla modalità privata\x1b[0m")
            await interaction.followup.send(
                "> **INFO: Successivamente, la risposta verrà inviata tramite risposta privata. Se vuoi tornare alla modalità pubblica, usa `/public`**")
        else:
            logger.info("Sei già in modalità privata!")
            await interaction.followup.send(
                "> **WARN: Sei già in modalità privata. Se vuoi passare alla modalità pubblica, usa `/public`**")


    @client.tree.command(name="public", description="Attiva/disattiva l'accesso pubblico")
    async def public(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        if client.isPrivate:
            client.isPrivate = not client.isPrivate
            await interaction.followup.send(
                "> **INFO:Successivamente, la risposta verrà inviata direttamente al canale. Se vuoi tornare alla modalità privata, usa `/private`**")
            logger.warning("\x1b[31mPassa alla modalità pubblica\x1b[0m")
        else:
            await interaction.followup.send(
                "> **WARN: Sei già in modalità pubblica. Se vuoi passare alla modalità privata, usa `/private`**")
            logger.info("Sei già in modalità pubblica!")


    @client.tree.command(name="replyall", description="Tutti gli accessi")
    async def replyall(interaction: discord.Interaction):
        client.replying_all_discord_channel_id = str(interaction.channel_id)
        await interaction.response.defer(ephemeral=False)
        if client.is_replying_all == "True":
            client.is_replying_all = "False"
            await interaction.followup.send(
                "> **INFO: Next, the bot will response to the Slash Command. If you want to switch back to replyAll mode, use `/replyAll` again**")
            logger.warning("\x1b[31mSwitch to normal mode\x1b[0m")
        elif client.is_replying_all == "False":
            client.is_replying_all = "True"
            await interaction.followup.send(
                "> **INFO: Next, the bot will disable Slash Command and responding to all message in this channel only. If you want to switch back to normal mode, use `/replyAll` again**")
            logger.warning("\x1b[31mSwitch to replyAll mode\x1b[0m")


    @client.tree.command(name="chat-model", description="Switch different chat model")
    @app_commands.choices(choices=[
        app_commands.Choice(name="Official GPT-3.5", value="OFFICIAL"),
        app_commands.Choice(name="Ofiicial GPT-4.0", value="OFFICIAL-GPT4"),
        app_commands.Choice(name="Website ChatGPT-3.5", value="UNOFFICIAL"),
        app_commands.Choice(name="Website ChatGPT-4.0", value="UNOFFICIAL-GPT4"),
        app_commands.Choice(name="Bard", value="Bard"),
        app_commands.Choice(name="Bing", value="Bing"),
    ])

    async def chat_model(interaction: discord.Interaction, choices: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=False)
        original_chat_model = client.chat_model
        original_openAI_gpt_engine = client.openAI_gpt_engine

        try:
            if choices.value == "OFFICIAL":
                client.openAI_gpt_engine = "gpt-3.5-turbo"
                client.chat_model = "OFFICIAL"
            elif choices.value == "OFFICIAL-GPT4":
                client.openAI_gpt_engine = "gpt-4"
                client.chat_model = "OFFICIAL"
            elif choices.value == "UNOFFICIAL":
                client.openAI_gpt_engine = "gpt-3.5-turbo"
                client.chat_model = "UNOFFICIAL"
            elif choices.value == "UNOFFICIAL-GPT4":
                client.openAI_gpt_engine = "gpt-4"
                client.chat_model = "UNOFFICIAL"
            elif choices.value == "Bard":
                client.chat_model = "Bard"
            elif choices.value == "Bing":
                client.chat_model = "Bing"
            else:
                raise ValueError("Invalid choice")

            client.chatbot = client.get_chatbot_model()
            await interaction.followup.send(f"> **INFO: You are now in {client.chat_model} model.**\n")
            logger.warning(f"\x1b[31mSwitch to {client.chat_model} model\x1b[0m")

        except Exception as e:
            client.chat_model = original_chat_model
            client.openAI_gpt_engine = original_openAI_gpt_engine
            client.chatbot = client.get_chatbot_model()
            await interaction.followup.send(f"> **ERROR: Error while switching to the {choices.value} model, check that you've filled in the related fields in `.env`.**\n")
            logger.exception(f"Error while switching to the {choices.value} model: {e}")


    @client.tree.command(name="reset", description="Complete reset conversation history")
    async def reset(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        if client.chat_model == "OFFICIAL":
            client.chatbot = client.get_chatbot_model()
        elif client.chat_model == "UNOFFICIAL":
            client.chatbot.reset_chat()
            await client.send_start_prompt()
        elif client.chat_model == "Bard":
            client.chatbot = client.get_chatbot_model()
            await client.send_start_prompt()
        elif client.chat_model == "Bing":
            await client.chatbot.reset()
        await interaction.followup.send("> **INFO: I have forgotten everything.**")
        personas.current_persona = "standard"
        logger.warning(
            f"\x1b[31m{client.chat_model} bot has been successfully reset\x1b[0m")


    @client.tree.command(name="help", description="Show help for the bot")
    async def help(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await interaction.followup.send(""":star: **BASIC COMMANDS** \n
        - `/chat [message]` Chatta con ChatGPT!
        - `/draw [prompt]` Generare un'immagine con il modello Dalle2
        - `/switchpersona [persona]` Passa tra i jailbreak ChatGPT opzionali
                `random`: Scegli una persona a caso
                `chatgpt`: Standard ChatGPT mode
                `dan`: Dan Mode 11.0, famigerata modalità Do Anything Now
                `sda`: Superior DAN ha ancora più libertà in modalità DAN
                `confidant`: Confidente malvagio, confidente fidato malvagio
                `based`: BasedGPT v2, sexy GPT
                `oppo`: OPPO dice esattamente l'opposto di quello che direbbe ChatGPT
                `dev`: Modalità sviluppatore, modalità sviluppatore v2 abilitata

        - `/private` ChatGPT passa alla modalità privata
         - `/public` ChatGPT passa alla modalità pubblica
         - `/replyall` ChatGPT passa dalla modalità replyAll alla modalità predefinita
         - `/reset` Cancella la cronologia delle conversazioni di ChatGPT
         - `/chat-model` Cambia modello di chat diverso
                 `UFFICIALE`: modello GPT-3.5
                 `NON UFFICIALE`: sito Web ChatGPT
                 `Bard`: modello di Google Bard
                 `Bing`: modello Microsoft Bing""")

        logger.info(
            "\x1b[31mSomeone needs help!\x1b[0m")


    @client.tree.command(name="info", description="Bot information")
    async def info(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        chat_engine_status = client.openAI_gpt_engine
        chat_model_status = client.chat_model
        if client.chat_model == "UNOFFICIAL":
            chat_model_status = "ChatGPT(UNOFFICIAL)"
        elif client.chat_model == "OFFICIAL":
            chat_model_status = "OpenAI API(OFFICIAL)"
        if client.chat_model != "UNOFFICIAL" and client.chat_model != "OFFICIAL":
            chat_engine_status = "x"
        elif client.openAI_gpt_engine == "text-davinci-002-render-sha":
            chat_engine_status = "gpt-3.5"

        await interaction.followup.send(f"""
```fix
chat-model: {chat_model_status}
gpt-engine: {chat_engine_status}
```
""")


    @client.tree.command(name="draw", description="Generate an image with the Dalle2 model")
    @app_commands.choices(amount=[
        app_commands.Choice(name="1", value=1),
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="3", value=3),
        app_commands.Choice(name="4", value=4),
        app_commands.Choice(name="5", value=5),
        app_commands.Choice(name="6", value=6),
        app_commands.Choice(name="7", value=7),
        app_commands.Choice(name="8", value=8),
        app_commands.Choice(name="9", value=9),
        app_commands.Choice(name="10", value=10),
    ])
    async def draw(interaction: discord.Interaction, *, prompt: str, amount: int = 1):
        if interaction.user == client.user:
            return

        username = str(interaction.user)
        channel = str(interaction.channel)
        logger.info(
            f"\x1b[31m{username}\x1b[0m : /draw [{prompt}] in ({channel})")

        await interaction.response.defer(thinking=True, ephemeral=client.isPrivate)
        try:
            path = await art.draw(prompt, amount)
            files = []
            for idx, img in enumerate(path):
                files.append(discord.File(img, filename=f"image{idx}.png"))
            title = f'> **{prompt}** - {str(interaction.user.mention)} \n\n'

            await interaction.followup.send(files=files, content=title)

        except openai.InvalidRequestError:
            await interaction.followup.send(
                "> **ERROR: Inappropriate request 😿**")
            logger.info(
            f"\x1b[31m{username}\x1b[0m made an inappropriate request.!")

        except Exception as e:
            await interaction.followup.send(
                "> **ERROR: Something went wrong 😿**")
            logger.exception(f"Error while generating image: {e}")


    @client.tree.command(name="switchpersona", description="Switch between optional chatGPT jailbreaks")
    @app_commands.choices(persona=[
        app_commands.Choice(name="Random", value="random"),
        app_commands.Choice(name="Standard", value="standard"),
        app_commands.Choice(name="Do Anything Now 11.0", value="dan"),
        app_commands.Choice(name="Superior Do Anything", value="sda"),
        app_commands.Choice(name="Evil Confidant", value="confidant"),
        app_commands.Choice(name="BasedGPT v2", value="based"),
        app_commands.Choice(name="OPPO", value="oppo"),
        app_commands.Choice(name="Developer Mode v2", value="dev"),
        app_commands.Choice(name="DUDE V3", value="dude_v3"),
        app_commands.Choice(name="AIM", value="aim"),
        app_commands.Choice(name="UCAR", value="ucar"),
        app_commands.Choice(name="Jailbreak", value="jailbreak")
    ])
    async def switchpersona(interaction: discord.Interaction, persona: app_commands.Choice[str]):
        if interaction.user == client.user:
            return

        await interaction.response.defer(thinking=True)
        username = str(interaction.user)
        channel = str(interaction.channel)
        logger.info(
            f"\x1b[31m{username}\x1b[0m : '/switchpersona [{persona.value}]' ({channel})")

        persona = persona.value

        if persona == personas.current_persona:
            await interaction.followup.send(f"> **WARN: Already set to `{persona}` persona**")

        elif persona == "standard":
            if client.chat_model == "OFFICIAL":
                client.chatbot.reset()
            elif client.chat_model == "UNOFFICIAL":
                client.chatbot.reset_chat()
            elif client.chat_model == "Bard":
                client.chatbot = client.get_chatbot_model()
            elif client.chat_model == "Bing":
                client.chatbot = client.get_chatbot_model()

            personas.current_persona = "standard"
            await interaction.followup.send(
                f"> **INFO: Switched to `{persona}` persona**")

        elif persona == "random":
            choices = list(personas.PERSONAS.keys())
            choice = randrange(0, 6)
            chosen_persona = choices[choice]
            personas.current_persona = chosen_persona
            await responses.switch_persona(chosen_persona, client)
            await interaction.followup.send(
                f"> **INFO: Switched to `{chosen_persona}` persona**")


        elif persona in personas.PERSONAS:
            try:
                await responses.switch_persona(persona, client)
                personas.current_persona = persona
                await interaction.followup.send(
                f"> **INFO: Switched to `{persona}` persona**")
            except Exception as e:
                await interaction.followup.send(
                    "> **ERROR: Something went wrong, please try again later! 😿**")
                logger.exception(f"Error while switching persona: {e}")

        else:
            await interaction.followup.send(
                f"> **ERROR: No available persona: `{persona}` 😿**")
            logger.info(
                f'{username} requested an unavailable persona: `{persona}`')


    @client.event
    async def on_message(message):
        if client.is_replying_all == "True":
            if message.author == client.user:
                return
            if client.replying_all_discord_channel_id:
                if message.channel.id == int(client.replying_all_discord_channel_id):
                    username = str(message.author)
                    user_message = str(message.content)
                    client.current_channel = message.channel
                    logger.info(f"\x1b[31m{username}\x1b[0m : '{user_message}' ({client.current_channel})")

                    await client.enqueue_message(message, user_message)
            else:
                logger.exception("replying_all_discord_channel_id not found, please use the command `/replyall` again.")

    TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    client.run(TOKEN)
